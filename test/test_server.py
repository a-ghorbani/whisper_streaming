import socket
from pydub import AudioSegment

# Server's IP address and port
server_ip = '127.0.0.1'
server_port =  43007
packet_size = 65536  # This should match the PACKET_SIZE in your server

def convert_audio_to_raw_pcm16(file_path, target_format="wav", channels=1, sample_rate=16000):
    audio = AudioSegment.from_file(file_path)
    audio = audio.set_channels(channels).set_frame_rate(sample_rate)
    return audio.raw_data


# Path to your MP3 file
file_path = './Conference.wav'

# Create a socket object
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to the server
client_socket.connect((server_ip, server_port))

converted_audio = convert_audio_to_raw_pcm16(file_path, channels=1, sample_rate=16000)

audio_chunk_size = packet_size
for i in range(0, len(converted_audio), audio_chunk_size):
    audio_chunk = converted_audio[i:i + audio_chunk_size]
    if not audio_chunk:
        break
    print('chunking and sending')
    client_socket.sendall(audio_chunk)

# Optionally wait for a response from the server
# Increase the buffer size if you expect a long transcription
# Receive the full response from the server
full_response = b""
while True:
    print("---1---")
    part = client_socket.recv(4096)
    print("---2---")
    print("part: ", part.decode())
    if not part:
        break  # No more data to receive
    full_response += part

print("Transcription:", full_response.decode())

# Close the connection
client_socket.close()
