import re
import time
import subprocess
import os
import json
import numpy as np


def generate_cmd(template, config, video_file):
    match = re.findall('{(.+?)}', template)
    command = template
    for pattern in match:
        val = config.get(pattern)
        if not val:
            val = getattr(video_file, pattern)
        if not val:
            continue
        command = command.replace('{' + pattern + '}', str(val))
    return command


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
    vmaf_log_path = f'{output_path}/{output_basename}_vmaf.json'
    vmaf_options = {
        'model_path': raw_vmaf_options.get('model_path', './modal/vmaf_v0.6.1.pkl'),
        'phone_model': raw_vmaf_options.get('phone_model', 1),
        'psnr': raw_vmaf_options.get('psnr', 1),
        'ssim': raw_vmaf_options.get('ssim', 1),
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

    with open(vmaf_log_path, 'r') as f:
        score_contents = json.load(f)
    vmaf_scores = [frame['metrics']['vmaf'] for frame in score_contents['frames']]
    vmaf = np.mean(vmaf_scores).round(5)
    vmaf_min = round(min(vmaf_scores), 5)
    vmaf_std = np.std(vmaf_scores).round(5)
    vmaf_data = f'{vmaf_min} | {vmaf_std} | {vmaf}'
    print(vmaf_data)


def generate_and_run(config, video_file):
    print(config)
    template = config['template']
    cmd = generate_cmd(template, config, video_file)
    print(f'Begin encoding with cmd: {cmd}...')

    start_time = time.time()
    subprocess.run(cmd)
    end_time = time.time()
    time_to_convert = end_time - start_time
    time_rounded = round(time_to_convert, 3)
    output_filename = config['output_filename']
    bitrate = video_file.measured_bitrate(os.path.getsize(output_filename))
    print(time_rounded, bitrate)
    if config.get('ffmpeg') and config.get('vmaf_options'):
        calculate_scores(config, video_file)
    print('Done!')


class Task(object):
    def __init__(self, config):
        self.config = config

    def run(self, video_file):
        config = self.config
        repeat_target = config.get('repeat_target')
        output_format = config.get("output_format", "mp4")
        if repeat_target:
            if config[repeat_target] and len(config[repeat_target]):
                for repeat in config[repeat_target]:
                    config_copy = config.copy()
                    config_copy[repeat_target] = repeat
                    output_filename = os.path.join(config['output_path'],
                                                   '%s_%s_%s.%s' % (video_file.basename, repeat_target,
                                                                    repeat, output_format))
                    config_copy['output_filename'] = output_filename
                    generate_and_run(config_copy, video_file)
            else:
                print('Invalid repeat target config')
                return 0
        else:
            config_copy = config.copy()
            output_filename = os.path.join(config['output_path'],
                                           '%s.%s' % (video_file.basename, output_format))
            config_copy['output_filename'] = output_filename
            generate_and_run(config.copy(), video_file)


def generate_tasks(config):
    tasks_list = config['tasks']
    tasks = set()
    for item in tasks_list:
        task_config = item.copy()
        for key in config:
            if key != 'tasks' and key not in task_config:
                task_config[key] = config[key]
        tasks.add(Task(task_config))
    return tasks
