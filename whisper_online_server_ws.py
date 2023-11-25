
#!/usr/bin/env python3
import asyncio
import websockets
from whisper_online import *
import sys
import argparse
import os
import logging

level = logging.INFO
logging.basicConfig(level=level, format='whisper-server-%(levelname)s: %(message)s')

parser = argparse.ArgumentParser()

# server options
parser.add_argument("--host", type=str, default='localhost')
parser.add_argument("--port", type=int, default=43007)

# options from whisper_online
# TODO: code repetition

parser.add_argument('--min-chunk-size', type=float, default=1.0, help='Minimum audio chunk size in seconds. It waits up to this time to do processing. If the processing takes shorter time, it waits, otherwise it processes the whole segment that was received by this time.')
parser.add_argument('--model', type=str, default='large-v2', choices="tiny.en,tiny,base.en,base,small.en,small,medium.en,medium,large-v1,large-v2,large".split(","),help="Name size of the Whisper model to use (default: large-v2). The model is automatically downloaded from the model hub if not present in model cache dir.")
parser.add_argument('--model_cache_dir', type=str, default=None, help="Overriding the default model cache dir where models downloaded from the hub are saved")
parser.add_argument('--model_dir', type=str, default=None, help="Dir where Whisper model.bin and other files are saved. This option overrides --model and --model_cache_dir parameter.")
parser.add_argument('--lan', '--language', type=str, default='en', help="Language code for transcription, e.g. en,de,cs.")
parser.add_argument('--task', type=str, default='transcribe', choices=["transcribe","translate"],help="Transcribe or translate.")
parser.add_argument('--backend', type=str, default="faster-whisper", choices=["faster-whisper", "whisper_timestamped"],help='Load only this backend for Whisper processing.')
parser.add_argument('--vad', action="store_true", default=False, help='Use VAD = voice activity detection, with the default parameters.')

args = parser.parse_args()

# setting whisper object by args 
SAMPLING_RATE = 16000

size = args.model
language = args.lan

t = time.time()
print(f"Loading Whisper {size} model for {language}...",file=sys.stderr,end=" ",flush=True)

if args.backend == "faster-whisper":
    from faster_whisper import WhisperModel
    asr_cls = FasterWhisperASR
else:
    import whisper
    import whisper_timestamped
#    from whisper_timestamped_model import WhisperTimestampedASR
    asr_cls = WhisperTimestampedASR

asr = asr_cls(modelsize=size, lan=language, cache_dir=args.model_cache_dir, model_dir=args.model_dir)

if args.task == "translate":
    asr.set_translate_task()
    tgt_language = "en"
else:
    tgt_language = language

e = time.time()
print(f"done. It took {round(e-t,2)} seconds.",file=sys.stderr)

if args.vad:
    print("setting VAD filter",file=sys.stderr)
    asr.use_vad()


min_chunk = args.min_chunk_size
online = OnlineASRProcessor(asr,create_tokenizer(tgt_language))



demo_audio_path = "./test/test.wav"
if os.path.exists(demo_audio_path):
    # load the audio into the LRU cache before we start the timer
    a = load_audio_chunk(demo_audio_path,0,1)

    # TODO: it should be tested whether it's meaningful
    # warm up the ASR, because the very first transcribe takes much more time than the other
    asr.transcribe(a)
else:
    print("Whisper is not warmed up",file=sys.stderr)



######### Server objects

class WebSocketConnection:
    def __init__(self, websocket):
        self.websocket = websocket
        logging.info("init WebSocketConnection")

    async def receive_audio_chunk(self):
        logging.info("WebSocketConnection - receive_audio_chunk")
        try:
            data = await self.websocket.recv()
            return data
        except websockets.exceptions.ConnectionClosed:
            logging.info("websockets.exceptions.ConnectionClosed")
            return None

    async def send_result(self, result):
        logging.info("sending results: %s", result)
        if result:
            await self.websocket.send(result)
import io
import soundfile
class WebSocketServerProcessor(): #ServerProcessor):
    def __init__(self, connection, online_asr_proc, min_chunk_size):
        self.connection = connection 
        self.online_asr_proc = online_asr_proc
        self.min_chunk = min_chunk_size

        self.last_end = None
        #super().__init__(connection, online_asr_proc, min_chunk_size)
    
    def format_output_transcript(self,o):
        # output format in stdout is like:
        # 0 1720 Takhle to je
        # - the first two words are:
        #    - beg and end timestamp of the text segment, as estimated by Whisper model. The timestamps are not accurate, but they're useful anyway
        # - the next words: segment transcript

        # This function differs from whisper_online.output_transcript in the following:
        # succeeding [beg,end] intervals are not overlapping because ELITR protocol (implemented in online-text-flow events) requires it.
        # Therefore, beg, is max of previous end and current beg outputed by Whisper.
        # Usually it differs negligibly, by appx 20 ms.

        if o[0] is not None:
            beg, end = o[0]*1000,o[1]*1000
            if self.last_end is not None:
                beg = max(beg, self.last_end)

            self.last_end = end
            print("%1.0f %1.0f %s" % (beg,end,o[2]),flush=True,file=sys.stderr)
            return "%1.0f %1.0f %s" % (beg,end,o[2])
        else:
            print(o,file=sys.stderr,flush=True)
            return None

    async def send_result(self, o):
        print("sending result")
        msg = self.format_output_transcript(o)
        print("and the result: ", msg)
        if msg is not None:
            try:
                await self.connection.send_result(msg)
            except Exception as e:
                logging.error(e)

    async def process(self):
        self.online_asr_proc.init()
        while True:
            logging.info("receiving")
            raw_bytes = await self.connection.receive_audio_chunk()

            if raw_bytes is None:
                break

            sf = soundfile.SoundFile(io.BytesIO(raw_bytes), channels=1,endian="LITTLE",samplerate=SAMPLING_RATE, subtype="PCM_16",format="RAW")
            audio_chunk, _ = librosa.load(sf,sr=SAMPLING_RATE)

            self.online_asr_proc.insert_audio_chunk(audio_chunk)
            logging.info("process_iter")
            result = self.online_asr_proc.process_iter()
            logging.info("sending result: %s", result)
            await self.send_result(result)
        final_result = self.online_asr_proc.finish()
        logging.info("finished result: %s", final_result)
        await self.send_result(final_result)

async def handle_client(websocket, path):
    client_address = websocket.remote_address
    logging.info(f'Client connected: {client_address}')

    connection = WebSocketConnection(websocket)
    processor = WebSocketServerProcessor(connection, online, args.min_chunk_size)
    await processor.process()

# Start server
start_server = websockets.serve(handle_client, args.host, args.port)
logging.info(f'WebSocket server started on ws://{args.host}:{args.port}')

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
