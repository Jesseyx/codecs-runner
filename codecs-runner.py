import sys
import argparse
import json
import os

from lib import seq_picker, task_parser, summary


def main():
    parser = argparse.ArgumentParser(description='Compare codecs')
    parser.add_argument('-c', '--config', type=str, required=True, help='Enter the path of the task config json. ')
    args = parser.parse_args()
    config_file = open(args.config)
    config = json.load(config_file)
    seq_path = config.get('seq_path')
    if not seq_path or not os.path.exists(seq_path):
        print('Invalid sequence path')
        return 0
    if not config.get('tasks') or not len(config.get('tasks')):
        print('Invalid tasks config')
        return 0
    output_path = config.get('output_path', './result')
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    seqs_video_file = seq_picker.pick_seqs(seq_path)
    tasks = task_parser.generate_tasks(config)
    for task in tasks:
        task.run(seqs_video_file)

    # save
    summary.save(os.path.join(output_path, 'encoder_result.xlsx'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
