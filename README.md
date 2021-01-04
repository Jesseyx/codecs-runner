# codecs-runner

A good tool to help you encode video and test video quality.

# Dependencies

* python3, pip3
* ffmpeg installed

install requirements:

```
cd <project-dir>
pip3 install -r requirements.txt
```

# Tools

* generate-yuv.py - Util for generate yuv files
* codecs-runner.py - Run encoding tasks, then compare video quality

You can use `python3 <tool> -h` to see usage information.

# Config

Usually, the configuration is as follows, see `config.example.json` for more information.

```
{
  ...common_config,
  "tasks": [
    {
      ...other_task_config,
      "template": task_run_template
    }
  ]
}
```
codecs-runner config is very flexible, but you need to follow some principles:

* `ffmpeg, ffprobe, vmaf_options` should in common_config if you want to calculate video quality.
* Use `seq_path` to configure yuv sequence path
* Use `output_path` to configure where the encoded video output
* `template` value will be compiled into a "Formatted String Literal" with a lambda function inside. 
    This means you can use any configuration in "common_config" or "other_task_config" with `{config_key}` grammar.
    You can even use some simple mathematical operations like `{bitrate_and_resolution['bitrate_m'] * 1000 * 2}`!
* `task_name` should in every task config
* `repeat_target` in task config is special. That means its value is a array, and task will run with every item config.
* You can use parsed yuv file info in `template` value:
    - `filename` - yuv video file path
    - `name` - yuv video file base name
    - `width` - yuv video width
    - `height` - yuv video height
    - `framerate` - yuv video framerate
    - `output_filename` computed output path with `output_path` config
* `"use_task_bitrate": "{task_name}",` and `"repeat_target": "bitrate"` is for two-pass encoding. Because multi-pass encoding needs to use the encoded special bit rate.

**Notice**: The configuration items mentioned above are special for codecs runner, please do not overwrite them!

# Tip for video sequence

Sequence naming must follow this rule: `{don't care string}_{width}(x|_){height}_{framerate}.yuv`.

The name of a test sequence should look like this: `gipsrecstat_1280_720_50.yuv` or `gipsrecstat_1280x720_50.yuv`.

You can use `generate-yuv` tool to convert the mp4, flv, webm video to yuv video.

# Use docker

```
# build
docker build -t codecs-runner ./

# mount directory on the container
# notice: set seq_path to ./work, output_path to ./result, base path is /data/codecs-runner
docker run -it -v /home/codecs_videos:/data/codecs-runner/work -v /home/codecs_result:/data/codecs-runner/result codecs-runner /bin/bash
```