
import asyncio
import websockets
from pydub import AudioSegment

# Server's WebSocket URL
websocket_url = 'ws://127.0.0.1:43007'

def convert_audio_to_raw_pcm16(file_path, target_format="wav", channels=1, sample_rate=16000):
    audio = AudioSegment.from_file(file_path)
    audio = audio.set_channels(channels).set_frame_rate(sample_rate)
    return audio.raw_data

# Path to your audio file
file_path = './Conference.wav'

async def send_audio(websocket, audio_data, chunk_size=65536):
    for i in range(0, len(audio_data), chunk_size):
        audio_chunk = audio_data[i:i + chunk_size]
        if not audio_chunk:
            break
        print('Sending audio chunk')
        await websocket.send(audio_chunk)
    await websocket.send("END_OF_STREAM")

async def receive_transcription(websocket):
    while True:
        try:
            response = await websocket.recv()
            print("Received transcription:", response)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed by server")
            break

async def main():
    converted_audio = convert_audio_to_raw_pcm16(file_path, channels=1, sample_rate=16000)

    async with websockets.connect(websocket_url) as websocket:
        # Create tasks for sending and receiving
        sender_task = asyncio.create_task(send_audio(websocket, converted_audio))
        receiver_task = asyncio.create_task(receive_transcription(websocket))

        # Wait for both tasks to complete
        await asyncio.gather(sender_task, receiver_task)

# Run the async main function
asyncio.run(main())