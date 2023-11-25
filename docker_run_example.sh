docker run \
     -p 43007:43007 \
     -v $(pwd)/tmp:/app/tmp \
     aghorbani/whisper_streaming:cpu python whisper_online_server_ws.py \
     --model medium.en
     --host 0.0.0.0 
     --port 43007
     --model_cache_dir /app/tmp/cache/
     --model_dir /app/tmp/model/
     --vad True