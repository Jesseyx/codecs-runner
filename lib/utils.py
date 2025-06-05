from platform import system
import subprocess
import os
import json

IS_WIN = system() in ['Windows', 'cli']

# see https://github.com/slhck/ffmpeg-quality-metrics/blob/master/ffmpeg_quality_metrics/utils.py
def win_path_check(path: str) -> str:
    """
    Format a file path correctly for Windows

    Args:
        path (str): The path to format

    Returns:
        str: The formatted path
    """
    if IS_WIN:
        return path.replace("\\", "/").replace(":", "\\:")
    return path


def win_vmaf_model_path_check(path: str) -> str:
    """
    Format vmaf model file path correctly for Windows

    Args:
        path (str): The path to format

    Returns:
        str: The formatted path
    """
    if IS_WIN:
        return win_path_check(path).replace("\\", "\\\\\\")
    return path


def video_to_yuv(ffmpeg: str, input: str, output: str):
    encode_yuv_args = [
        ffmpeg, '-y', '-loglevel', 'warning', '-i', input, output
    ]
    print(f'Begin encoding yuv file with cmd: {" ".join(encode_yuv_args)}...')
    # generate yuv
    subprocess.run(encode_yuv_args)


def get_video_properties(ffprobe: str, video_path: str) -> dict:
    if not os.path.isfile(video_path) or not os.access(video_path, os.R_OK):
        raise RuntimeError(f'File not found or inaccessible: {video_path}')

    output = subprocess.check_output(
        [ffprobe, '-loglevel', 'panic', '-select_streams', 'v:0', '-show_streams', '-print_format', 'json', video_path]
    )
    props = json.loads(output)

    if 'streams' not in props or not props['streams']:
        raise RuntimeError(f'No usable video stream found: {video_path}')

    return props['streams'][0]
