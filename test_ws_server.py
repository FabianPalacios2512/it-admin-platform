import asyncio
import websockets

async def handler(websocket, path):
    try:
        msg1 = await websocket.recv()
        print('Received machine info:', len(msg1), 'bytes')
        
        # Send command
        await websocket.send('{"type": "execute_command", "command": "echo test"}')
        
        msg2 = await websocket.recv()
        print('Received result:', len(msg2), 'bytes')
    except Exception as e:
        print('Error:', e)

start_server = websockets.serve(handler, 'localhost', 8765)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
