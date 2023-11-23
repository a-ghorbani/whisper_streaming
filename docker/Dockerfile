# Use Python 3.10.13 as the base image
FROM python:3.10.13

# Set the working directory in the container
WORKDIR /usr/src/app

RUN apt-get update && \
    apt-get install -y cmake libboost-program-options-dev libboost-thread-dev libre2-dev \
    pybind11-dev ffmpeg 



# Install opus-fast-mosestokenizer
RUN pip install faster-whisper opus-fast-mosestokenizer librosa soundfile audioread
ENV LD_LIBRARY_PATH /usr/local/lib/python3.10/site-packages/mosestokenizer/lib:$LD_LIBRARY_PATH

RUN git clone https://github.com/a-ghorbani/whisper_streaming.git

WORKDIR /usr/src/app/whisper_streaming

EXPOSE 43001

CMD ["python", "whisper_online_server.py"]

