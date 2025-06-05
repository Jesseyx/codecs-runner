import glob
import os
import re

from .utils import get_video_properties


class Error(Exception):
    """Generic errors in all Encoder-related problems."""
    pass


class VideoFile(object):
    def __init__(self, filename: str, config: dict):
        """ Parse the file name to find width, height and framerate. """
        self.filename = filename
        self.name = os.path.basename(filename)
        self.basename = os.path.splitext(self.name)[0]
        self.ext = os.path.splitext(filename)[1]

        if self.ext == '.yuv':
            match = re.search(r'_(\d+)x(\d+)_(\d+)', filename)
            if match:
                self.width = int(match.group(1))
                self.height = int(match.group(2))
                self.framerate = int(match.group(3))
            else:
                match = re.search(r'_(\d+)_(\d+)_(\d+).yuv$', filename)
                if match:
                    self.width = int(match.group(1))
                    self.height = int(match.group(2))
                    self.framerate = int(match.group(3))
        else:
            video_properties = get_video_properties(config['ffprobe'], filename)
            self.width = video_properties['width']
            self.height = video_properties['height']
            self.framerate = round(eval(video_properties['r_frame_rate']))
            self.framecount = float(video_properties['nb_frames'])
        
        if not self.width and not self.height:
            raise Error("Unable to parse filename " + filename)

    def measured_bitrate(self, encoded_size: int):
        """Returns bitrate of an encoded file in kilobits per second.

        Argument: Encoded file size in bytes.
        """
        frame_count = self.frame_count()
        encoded_frame_size = encoded_size / frame_count
        return round(encoded_frame_size * self.framerate * 8 / 1000, 2)

    def frame_count(self):
        if hasattr(self, 'framecount'):
            return self.framecount
        # YUV is 8 bits per pixel for Y, 1/4 that for each of U and V.
        frame_size = self.width * self.height * 3 / 2
        return os.path.getsize(self.filename) / frame_size

    def clip_time(self):
        return float(self.frame_count()) / self.framerate

def generate_seqs(name: str, config: dict):
    set_ext = os.path.splitext(name)[1]
    if not set_ext:
        print('Not set sequence ext, will use yuv')
    seq_files = glob.glob(name if set_ext else os.path.join(name, '*.yuv'))
    my_list = []
    for seq_file in seq_files:
        video_file = VideoFile(seq_file, config)
        my_list.append(video_file)
    return my_list


def pick_seqs(name: str, config: dict):
    return generate_seqs(name, config)
