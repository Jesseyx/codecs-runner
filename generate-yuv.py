import sys
import argparse
import os
import glob
import subprocess


def generate(ffmpeg_path, filename, output_name):
    print(filename, output_name)
    encode_yuv_args = [
        ffmpeg_path, '-loglevel', 'warning', '-i', filename, output_name, '-y'
    ]
    print(f'Begin encoding yuv file with cmd: {" ".join(encode_yuv_args)}...')
    # generate temp yuv
    subprocess.run(encode_yuv_args)


def main():
    parser = argparse.ArgumentParser(description='Util for generate yuv files',
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-ffmpeg', type=str, default='ffmpeg', help='Enter ffmpeg path for encode. ')
    parser.add_argument('-i', '--input-path', type=str, required=True,
                        help='Enter the path of the video. '
                             'A relative or absolute path can be specified.'
                             'If the path contains a space, it must be surrounded in double quotes.\n'
                             'Example: -i "./work"')
    parser.add_argument('-ext', nargs='+', default=['mp4', 'flv', 'webm'],
                        help='List the video ext you want to be encode (separated by a space). \n'
                             'Default is mp4, flv, webm')
    args = parser.parse_args()
    print(args)

    input_path = args.input_path
    if not os.path.exists(input_path):
        print('Invalid input path')
        return 0
    ffmpeg_path = args.ffmpeg

    input_files = []
    for ext in args.ext:
        input_files.extend(glob.glob(os.path.join(input_path, f'*.{ext}')))

    for filename in input_files:
        generate(ffmpeg_path, filename, f'{os.path.join(os.path.splitext(filename)[0])}.yuv')


if __name__ == '__main__':
    sys.exit(main())
