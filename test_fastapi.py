from fastapi import FastAPI, WebSocket
import uvicorn

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Accepted")
    try:
        data = await websocket.receive_text()
        print("Received:", len(data))
        await websocket.send_text('{"type": "execute_command"}')
        
        data2 = await websocket.receive_text()
        print("Received 2:", len(data2))
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8765, log_level='error')
