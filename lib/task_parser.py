import re
import time
import subprocess
import os
import json
import numpy as np

from lib import bitrate_keeper

keeper = bitrate_keeper.BitrateKeeper()


def calculate_scores(seq_config, video_file):
    output_path = seq_config['output_path']
    output_filename = seq_config['output_filename']
    output_basename = os.path.splitext(os.path.basename(output_filename))[0]

    temp_yuv_file = os.path.join(output_path,
                                 '%s_temp_yuv.yuv' % output_basename)
    if os.path.isfile(temp_yuv_file):
        print('Removing temp file before decode:', temp_yuv_file)
        os.unlink(temp_yuv_file)
    encode_yuv_args = [
        seq_config['ffmpeg'], '-y', '-loglevel', 'warning', '-i', output_filename, temp_yuv_file
    ]
    print(f'Begin encoding temp yuv file with cmd: {" ".join(encode_yuv_args)}...')
    # generate temp yuv
    subprocess.run(encode_yuv_args)

    # Detect video width and height
    # todo use ffprobe?
    input_width = video_file.width
    input_height = video_file.height
    output_width = input_height
    output_height = input_height
    repeat_value = seq_config.get(seq_config['repeat_target']) if seq_config.get('repeat_target') else None
    if repeat_value and type(repeat_value) == dict and repeat_value.get('w') and repeat_value.get('h'):
        output_width = repeat_value['w']
        output_height = repeat_value['h']
    if input_width != output_width or input_height != output_height:
        scale_arg = f',scale={input_width}x{input_height}'
    else:
        scale_arg = ''

    raw_vmaf_options = seq_config['vmaf_options']
    calc_psnr = raw_vmaf_options.get('psnr', 1)
    calc_ssim = raw_vmaf_options.get('ssim', 1)
    vmaf_log_path = f'{output_path}/{output_basename}_vmaf.json'
    vmaf_options = {
        'model_path': raw_vmaf_options.get('model_path', './modal/vmaf_v0.6.1.pkl'),
        'phone_model': raw_vmaf_options.get('phone_model', 1),
        'psnr': calc_psnr,
        'ssim': calc_ssim,
        'log_path': vmaf_log_path,
        'log_fmt': 'json'
    }
    vmaf_options = ':'.join(f'{key}={value}' for key, value in vmaf_options.items())
    vmaf_run_args = [
        'ffmpeg', '-loglevel', 'error', '-stats',
        '-s', f'{output_width}x{output_height}', '-r', f'{video_file.framerate}', '-i', temp_yuv_file,
        '-s', f'{input_width}x{input_height}', '-r', f'{video_file.framerate}', '-i', video_file.filename,
        '-lavfi', f'[0:v]setpts=PTS-STARTPTS{scale_arg}[main];[1:v]setpts=PTS-STARTPTS[ref];[main][ref]'f'libvmaf={vmaf_options}',
        '-f', 'null', '-'
    ]
    print(f'Begin calculating the quality achieved with cmd: {" ".join(vmaf_run_args)}')
    # generate score
    subprocess.run(vmaf_run_args)
    os.unlink(temp_yuv_file)  # unlink temp yuv file

    scores = []

    with open(vmaf_log_path, 'r') as f:
        score_contents = json.load(f)
    vmaf_scores = [frame['metrics']['vmaf'] for frame in score_contents['frames']]
    vmaf = np.mean(vmaf_scores).round(5)
    vmaf_min = round(min(vmaf_scores), 5)
    vmaf_std = np.std(vmaf_scores).round(5)
    scores.append([vmaf, vmaf_min, vmaf_std])

    if calc_psnr:
        psnr_scores = [frame['metrics']['psnr'] for frame in score_contents['frames']]
        psnr = np.mean(psnr_scores).round(5)
        psnr_min = round(min(psnr_scores), 5)
        psnr_std = np.std(psnr_scores).round(5)
        scores.append([psnr, psnr_min, psnr_std])

    if calc_ssim:
        ssim_scores = [frame['metrics']['ssim'] for frame in score_contents['frames']]
        ssim = np.mean(ssim_scores).round(5)
        ssim_min = round(min(ssim_scores), 3)
        ssim_std = np.std(ssim_scores).round(5)
        scores.append([ssim, ssim_min, ssim_std])

    return scores


def run_cmd(seq_config, video_file):
    cmd = seq_config['template']
    print(f'Begin encoding with cmd: {cmd}...')

    start_time = time.time()
    subprocess.run(cmd, shell=True)
    end_time = time.time()

    time_to_convert = end_time - start_time
    output_filename = seq_config['output_filename']
    bitrate = video_file.measured_bitrate(os.path.getsize(output_filename))
    encode_fps = round(time_to_convert / video_file.frame_count(), 5)
    print(bitrate, encode_fps)

    scores = None
    if seq_config.get('ffmpeg') and seq_config.get('vmaf_options'):
        scores = calculate_scores(seq_config, video_file)
    return bitrate, encode_fps, scores


def create_config(*dict_list):
    extend_data = {}
    for data in dict_list:
        extend_data.update(data)
    return extend_data


def compile_template(template):
    template = re.sub(r'{([^[}]+)(\[?[^}]+)?}', r"{self['\1']\2}", template)
    return eval(f'lambda self: f"{template}"')


class Task(object):
    def __init__(self, config):
        self.config = config
        self.tmpl_func = compile_template(config['template'])

        repeat_target = config.get('repeat_target')
        is_repeat = bool(repeat_target)
        if repeat_target:
            repeat_list = config.get(repeat_target)
            is_repeat = repeat_list and len(repeat_list) or config.get('use_task_bitrate')
        if repeat_target and not is_repeat:
            print('Invalid repeat target config, repeat config will be ignored!')
        self.is_repeat = is_repeat

    def run(self, videos_file):
        task_config = self.config
        is_repeat = self.is_repeat

        task_name = task_config['task_name']
        repeat_target = task_config['repeat_target'] if is_repeat else ''
        task_results = []

        for video_file in videos_file:
            file_results = []
            if is_repeat:
                if repeat_target == 'bitrate' \
                   and not task_config.get(repeat_target) and task_config.get('use_task_bitrate'):
                    repeat_values = keeper.get_bitrate_list(task_config.get('use_task_bitrate'), video_file.name)
                else:
                    repeat_values = task_config[repeat_target]
                if not repeat_values or not len(repeat_values):
                    print('Invalid repeat target config, error, do nothing!')
                    continue

                for index, repeat_value in enumerate(repeat_values):
                    # encode
                    bitrate, encode_fps, scores = self._run_seq(video_file, repeat_value)
                    # add file repeat results
                    file_results.append({
                        'repeat_value': json.dumps(repeat_value),
                        'bitrate': bitrate,
                        'encode_fps': encode_fps,
                        'scores': scores
                    })
                    keeper.set_bitrate(task_name, video_file.name, bitrate)
            else:
                # encode
                bitrate, encode_fps, scores = self._run_seq(video_file)
                # add file repeat results
                file_results.append({
                    'repeat_value': '',
                    'bitrate': bitrate,
                    'encode_fps': encode_fps,
                    'scores': scores
                })
                keeper.set_bitrate(task_name, video_file.name, bitrate)

            # add file results
            task_results.append({
                'name': video_file.name,
                'frame_count': video_file.frame_count(),
                'results': file_results
            })

        return {
            'task_name': task_name,
            'repeat_target': repeat_target,
            'results': task_results
        }

    def _run_seq(self, video_file, repeat_value=None):
        task_config = self.config
        is_repeat = self.is_repeat
        output_format = task_config.get('output_format', 'mp4')

        if is_repeat and repeat_value:
            repeat_target = task_config['repeat_target']

            # fix repeat_value is dict
            repeat_value_text = repeat_value
            if type(repeat_value) == dict:
                repeat_value_text = '_'.join([str(v) for v in filter(lambda v: type(v) != dict, repeat_value.values())])

            output_filename = os.path.join(
                task_config['output_path'],
                '%s_%s_%s.%s' % (video_file.basename, repeat_target, repeat_value_text, output_format)
            )
            extra_config = {repeat_target: repeat_value, 'output_filename': output_filename}
        else:
            output_filename = os.path.join(
                task_config['output_path'],
                '%s.%s' % (video_file.basename, output_format)
            )
            extra_config = {'output_filename': output_filename}

        seq_config = create_config(task_config, extra_config, vars(video_file))
        seq_config['template'] = self.tmpl_func(seq_config)

        # encode
        return run_cmd(seq_config, video_file)


def generate_tasks(config):
    tasks_list = config['tasks']
    tasks = []
    for (index, item) in enumerate(tasks_list):
        task_config = item.copy()
        for key in config:
            if key != 'tasks' and key not in task_config:
                task_config[key] = config[key]
        if not task_config.get('task_name'):
            task_config['task_name'] = f'task_{index}'
        tasks.append(Task(task_config))
    return tasks
