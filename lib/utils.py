from platform import system

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
