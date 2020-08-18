FROM openvisualcloud/xeon-ubuntu1804-media-ffmpeg

WORKDIR /data/codecs-runner

COPY requirements.txt ./

RUN apt-get update -y \
    && apt-get install -y -q --no-install-recommends python3 python3-pip python3-setuptools python3-wheel wget xz-utils tar \
    && apt-get clean \
    && pip3 install -r requirements.txt

RUN wget -q https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    && xz -d ffmpeg-release-amd64-static.tar.xz \
    && tar -xvf ffmpeg-release-amd64-static.tar \
    && rm -rf ffmpeg-release-amd64-static.tar

COPY . .
