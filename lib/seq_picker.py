import glob
import os
import re


class Error(Exception):
    """Generic errors in all Encoder-related problems."""
    pass


class VideoFile(object):
    def __init__(self, filename):
        """ Parse the file name to find width, height and framerate. """
        self.filename = filename
        self.name = os.path.basename(filename)
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
                raise Error("Unable to parse filename " + filename)
        self.basename = os.path.splitext(self.name)[0]

    def measured_bitrate(self, encoded_size):
        """Returns bitrate of an encoded file in kilobits per second.

        Argument: Encoded file size in bytes.
        """
        frame_count = self.frame_count()
        encoded_frame_size = encoded_size / frame_count
        return round(encoded_frame_size * self.framerate * 8 / 1000, 2)

    def frame_count(self):
        # YUV is 8 bits per pixel for Y, 1/4 that for each of U and V.
        frame_size = self.width * self.height * 3 / 2
        return os.path.getsize(self.filename) / frame_size

    def clip_time(self):
        return float(self.frame_count()) / self.framerate


def generate_seqs(name):
    yuv_files = glob.glob(os.path.join(name, '*.yuv'))
    my_set = set()
    for yuv_file in yuv_files:
        video_file = VideoFile(yuv_file)
        my_set.add(video_file)
    return my_set


def pick_seqs(name):
    return generate_seqs(name)
