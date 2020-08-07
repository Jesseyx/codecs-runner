import re
import time
import subprocess
import os
import json
import glob
import numpy as np

from lib import summary


def generate_cmd(template, config, video_file, two_pass_config=None):
    if not two_pass_config:
        two_pass_config = {}
    if two_pass_config.get('pass_num') == 1:
        two_pass_config.update({'output_format': 'null', 'output_filename': '-'})
    extend_data = {}
    for data in [config, vars(video_file), two_pass_config]:
        extend_data.update(data)
    match = re.findall('{(.+?)}', template)
    command = template
    for pattern in match:
        val = extend_data.get(pattern)
        if not val:
            continue
        command = command.replace('{' + pattern + '}', str(val))
    return command


def unlink_2_pass_log():
    for log in glob.glob(os.path.join(os.getcwd(), '*2pass-*')):
        os.unlink(log)


def calculate_scores(config, video_file):
    output_path = config['output_path']
    output_filename = config['output_filename']
    output_basename = os.path.splitext(os.path.basename(output_filename))[0]

    temp_yuv_file = os.path.join(output_path,
                                 '%s_temp_yuv.yuv' % output_basename)
    if os.path.isfile(temp_yuv_file):
        print('Removing temp file before decode:', temp_yuv_file)
        os.unlink(temp_yuv_file)
    encode_yuv_args = [
        config['ffmpeg'], '-loglevel', 'warning', '-i', output_filename, temp_yuv_file
    ]
    print(f'Begin encoding temp yuv file with cmd: {" ".join(encode_yuv_args)}...')
    # generate temp yuv
    subprocess.run(encode_yuv_args)

    raw_vmaf_options = config['vmaf_options']
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
        '-s', f'{video_file.width}x{video_file.height}', '-r', f'{video_file.framerate}', '-i', temp_yuv_file,
        '-s', f'{video_file.width}x{video_file.height}', '-r', f'{video_file.framerate}', '-i', video_file.filename,
        '-lavfi', '[0:v]setpts=PTS-STARTPTS[main];[1:v]setpts=PTS-STARTPTS[ref];[main][ref]'f'libvmaf={vmaf_options}',
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


def generate_and_run(config, video_file):
    print(config)
    template = config['template']

    cmd_list = []
    two_pass_mode = config.get('two_pass')
    if two_pass_mode:
        for pass_num in range(1, 3):
            cmd_list.append(generate_cmd(template, config, video_file,
                                         {'pass_num': pass_num}))
    else:
        cmd_list.append(generate_cmd(template, config, video_file))

    print(f'Begin encoding with cmd: {cmd_list}...')

    start_time = time.time()
    for cmd in cmd_list:
        subprocess.run(cmd, shell=True)
    end_time = time.time()
    if two_pass_mode:
        unlink_2_pass_log()
    time_to_convert = end_time - start_time
    output_filename = config['output_filename']
    bitrate = video_file.measured_bitrate(os.path.getsize(output_filename))
    encode_fps = round(time_to_convert / video_file.frame_count(), 5)
    print(bitrate, encode_fps)

    scores = None
    if config.get('ffmpeg') and config.get('vmaf_options'):
        scores = calculate_scores(config, video_file)
    return bitrate, encode_fps, scores


class Task(object):
    def __init__(self, config):
        self.config = config

    def run(self, seqs_video_file):
        config = self.config
        repeat_target = config.get('repeat_target')
        output_format = config.get("output_format", "mp4")

        task_results = {
            'task_name': config['task_name'],
            'repeat_target': '',
            'results': []
        }

        for video_file in seqs_video_file:
            encode_results = {
                'name': video_file.name,
                'frame_count': video_file.frame_count(),
                'results': []
            }
            if repeat_target:
                if config[repeat_target] and len(config[repeat_target]):
                    task_results['repeat_target'] = repeat_target
                    for repeat_value in config[repeat_target]:
                        config_copy = config.copy()
                        config_copy[repeat_target] = repeat_value
                        output_filename = os.path.join(config['output_path'],
                                                       '%s_%s_%s.%s' % (video_file.basename, repeat_target,
                                                                        repeat_value, output_format))
                        config_copy['output_filename'] = output_filename
                        bitrate, encode_fps, scores = generate_and_run(config_copy, video_file)

                        encode_results['results'].append({
                            'repeat_value': repeat_value,
                            'bitrate': bitrate,
                            'encode_fps': encode_fps,
                            'scores': scores
                        })
                else:
                    print('Invalid repeat target config')
                    return 0
            else:
                config_copy = config.copy()
                output_filename = os.path.join(config['output_path'],
                                               '%s.%s' % (video_file.basename, output_format))
                config_copy['output_filename'] = output_filename
                bitrate, encode_fps, scores = generate_and_run(config_copy, video_file)

                encode_results['results'].append({
                    'repeat_value': '',
                    'bitrate': bitrate,
                    'encode_fps': encode_fps,
                    'scores': scores
                })

            task_results['results'].append(encode_results)

        summary.record_task_results(task_results)


def generate_tasks(config):
    tasks_list = config['tasks']
    tasks = set()
    for (index, item) in enumerate(tasks_list):
        task_config = item.copy()
        for key in config:
            if key != 'tasks' and key not in task_config:
                task_config[key] = config[key]
        if not task_config.get('task_name'):
            task_config['task_name'] = f'task_{index}'
        tasks.add(Task(task_config))
    return tasks
