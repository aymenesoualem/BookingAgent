import os
import json
import base64
import asyncio
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from gtts import gTTS
from io import BytesIO
from dotenv import load_dotenv
from datetime import date
import ssl

from main import initialize_session

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 5050))

app = FastAPI()

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set")


# Function to convert text to base64-encoded audio
def text_to_audio_base64(text: str) -> str:
    """Converts text to audio and returns the base64 encoded audio."""
    tts = gTTS(text)
    audio_file = BytesIO()
    tts.save(audio_file)
    audio_file.seek(0)
    audio_base64 = base64.b64encode(audio_file.read()).decode('utf-8')
    return audio_base64


# WebSocket handler for OpenAI interaction
import asyncio
import websockets
import json

async def handle_openai_websocket(websocket: WebSocket):
    """Handles the connection to OpenAI WebSocket."""
    print("Connecting to OpenAI WebSocket...")
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    # Connecting to OpenAI WebSocket
    async with websockets.connect(
            'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01',
            ssl=ssl_context,
            extra_headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
    ) as openai_ws:
        await initialize_session(openai_ws)


        while True:
            message = await websocket.receive_text()
            audio_base64 = text_to_audio_base64(message)

            # Sending the audio to OpenAI via WebSocket
            audio_append = {
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            }
            await openai_ws.send(json.dumps(audio_append))
            response = await openai_ws.recv()
            print(f"OpenAI response: {response}")
            await websocket.send_text(json.dumps({"response": response}))


@app.post("/send-message")
async def send_message(request: Request):
    """Receives string message from POST request, converts to audio and sends to WebSocket."""
    data = await request.json()
    message = data.get("message", "")

    # Convert the text message to audio and base64 encode it
    audio_base64 = text_to_audio_base64(message)

    # Send to WebSocket
    # In this case, we're just using a WebSocket connection for interaction
    # You'll need to pass the WebSocket object here or implement logic to manage connections

    return JSONResponse(content={"audio_base64": audio_base64})


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """Accepts WebSocket connections and forwards messages to OpenAI WebSocket."""
    await websocket.accept()
    await handle_openai_websocket(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
