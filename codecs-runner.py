import sys
import argparse
import json
import traceback

from lib import task_parser, summary


def main():
    parser = argparse.ArgumentParser(description='Compare codecs')
    parser.add_argument('-c', '--config', type=str, required=True, help='Enter the path of the task config json. ')
    args = parser.parse_args()
    config_file = open(args.config)
    config = json.load(config_file) # type: dict
    
    if not config.get('tasks') or not len(config.get('tasks')):
        print('Invalid tasks config')
        return 0
    
    tasks = task_parser.generate_tasks(config) # type: list[task_parser.Task]
    if not len(tasks):
        print('No tasks to run!')
        return 0

    try:
        for task in tasks:
            task_results = task.run()
            summary.record_task_results(task_results)
    except KeyboardInterrupt:
        print('Interrupted by user')
    except Exception as e:
        print('Run task error: \n%s' % traceback.format_exc())

    # save
    summary_path = config.get('summary_path', './result/encoder_result.xlsx')
    summary.save(summary_path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
