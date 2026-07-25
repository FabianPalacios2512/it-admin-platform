import asyncio
import threading
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

try:
    from winpty import PtyProcess
except ImportError:
    PtyProcess = None

router = APIRouter()

@router.websocket("/ws")
async def terminal_websocket(websocket: WebSocket):
    await websocket.accept()

    if PtyProcess is None:
        await websocket.send_text("\r\n\x1b[31m[!] Error: 'pywinpty' no está instalado en el servidor.\r\nPor favor, ejecuta 'pip install pywinpty' y reinicia el servidor.\x1b[0m\r\n")
        await websocket.close()
        return

    loop = asyncio.get_running_loop()

    try:
        # Spawn a native Windows PTY running powershell (rows, cols)
        process = PtyProcess.spawn("powershell.exe", dimensions=(30, 120))
    except Exception as e:
        await websocket.send_text(f"\r\n\x1b[31mError starting PTY: {e}\x1b[0m\r\n")
        await websocket.close()
        return

    def read_stdout():
        try:
            while True:
                # read() blocks until data is available
                data = process.read(1024)
                if not data:
                    break
                
                # data is already decoded as string by pywinpty
                future = asyncio.run_coroutine_threadsafe(websocket.send_text(data), loop)
                try:
                    future.result(timeout=5)
                except Exception:
                    break
        except Exception as e:
            if "EOF" not in str(e):
                print(f"Terminal PTY Read Error: {e}")
        finally:
            try:
                asyncio.run_coroutine_threadsafe(websocket.close(), loop)
            except Exception:
                pass

    thread = threading.Thread(target=read_stdout, daemon=True)
    thread.start()

    try:
        while True:
            data = await websocket.receive_text()
            
            # Detectar comando de redimensionamiento
            if data.startswith('{"type":"resize"'):
                try:
                    import json
                    msg = json.loads(data)
                    if process.isalive():
                        # pywinpty expects (rows, cols)
                        process.set_size(msg["rows"], msg["cols"])
                except Exception as e:
                    print(f"Error resizing: {e}")
                continue

            if process.isalive():
                process.write(data)
            else:
                break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Terminal WS Error: {e}")
    finally:
        try:
            if process.isalive():
                process.terminate()
        except:
            pass
