import asyncio
import websockets
import base64
import json

ASSEMBLY_API_KEY = 'YOUR_API_KEY'

if ASSEMBLY_API_KEY == 'YOUR_API_KEY':
    raise Exception("Please set your AssemblyAI API key in the ASSEMBLY_API_KEY variable.")

async def transcribe_file(file_path):
    url = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=8000"
    headers = {
        "Authorization": ASSEMBLY_API_KEY
    }
    transcript_text = ""
    async with websockets.connect(url, extra_headers=headers) as socket:
        audio_data_queue = asyncio.Queue()
        # Start a task to send the audio data chunks as they become available
        asyncio.create_task(send_audio_data(socket, audio_data_queue))
        async for message in socket:
            res = json.loads(message)
            if res["message_type"] == "PartialTranscript":
                print("Partial Text:", res["text"])
            if res["message_type"] == "FinalTranscript":
                print("Final Text:", res["text"])
                transcript_text += res["text"] + " "
            if res["message_type"] == "SessionBegins":
                print("Session Begins")
                with open(file_path, "rb") as f:
                    data = f.read()
                    # Queue up the audio data chunks
                    for i in range(0, len(data), 1800):
                        chunk = data[i:i+1800]
                        if len(chunk) < 1800:
                            continue
                        audio_data = base64.b64encode(chunk).decode("utf-8")
                        await audio_data_queue.put(audio_data)
                # Signal the end of the audio data
                await audio_data_queue.put(None)
        print(f"WebSocket connection closed with code {socket.close_code} and reason '{socket.close_reason}'")
        with open(f"{file_path}_transcript.txt", "w") as f:
            f.write(transcript_text)

# Async function to send the audio data chunks as they become available
async def send_audio_data(socket, audio_data_queue):
    while True:
        audio_data = await audio_data_queue.get()
        if audio_data is None:
            # Terminate the session when all audio data has been sent
            await socket.send(json.dumps({"terminate_session": True}))
            break
        await socket.send(json.dumps({"audio_data": audio_data}))
        await asyncio.sleep(0.05)

asyncio.run(transcribe_file("./example.wav"))

