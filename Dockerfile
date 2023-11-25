FROM python:3.10.13

# Set the working directory in the container
WORKDIR /usr/src/app

# Install dependencies 
RUN apt-get update && \
    apt-get install -y cmake libboost-program-options-dev libboost-thread-dev libre2-dev pybind11-dev ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install faster-whisper opus-fast-mosestokenizer librosa soundfile audioread websockets
ENV LD_LIBRARY_PATH /usr/local/lib/python3.10/site-packages/mosestokenizer/lib:$LD_LIBRARY_PATH

# RUN git clone https://github.com/a-ghorbani/whisper_streaming.git
COPY . /usr/src/app/whisper_streaming

WORKDIR /usr/src/app/whisper_streaming

EXPOSE 43007

RUN useradd -m appuser
USER appuser

CMD ["python", "whisper_online_server_ws.py"]

