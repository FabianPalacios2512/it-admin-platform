import subprocess
import threading
import re
import time
import logging
import atexit

logger = logging.getLogger(__name__)

class CloudflareTunnelManager:
    def __init__(self):
        self.process = None
        self.url = None
        self._lock = threading.Lock()
        
        # Ensure we don't leave zombie tunnels on exit
        atexit.register(self.stop)

    def start(self, port: int = 8000) -> str:
        """Inicia el túnel de Cloudflare y retorna la URL segura."""
        with self._lock:
            if self.process and self.process.poll() is None:
                if self.url:
                    return self.url
                # Is running but URL not found yet, let's stop and restart just in case
                self.stop()
            
            logger.info("Iniciando Cloudflare Tunnel...")
            
            import os
            # Intentar usar la ruta absoluta si está instalado vía winget
            cloudflared_path = "cloudflared"
            if os.path.exists(r"C:\Program Files (x86)\cloudflared\cloudflared.exe"):
                cloudflared_path = r"C:\Program Files (x86)\cloudflared\cloudflared.exe"
            elif os.path.exists(r"C:\Program Files\cloudflared\cloudflared.exe"):
                cloudflared_path = r"C:\Program Files\cloudflared\cloudflared.exe"
            
            # cloudflared logs its output to stderr
            self.process = subprocess.Popen(
                [cloudflared_path, "tunnel", "--url", f"http://localhost:{port}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            self.url = None
            start_time = time.time()
            
            # Read stderr line by line without blocking indefinitely
            def log_reader():
                while self.process and self.process.poll() is None:
                    line = self.process.stderr.readline()
                    if not line:
                        break
                    
                    # Look for the URL pattern
                    # e.g.: INF |  https://some-random-words.trycloudflare.com
                    match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
                    if match and not self.url:
                        self.url = match.group(0)
                        logger.info(f"Túnel establecido en: {self.url}")
            
            reader_thread = threading.Thread(target=log_reader, daemon=True)
            reader_thread.start()
            
            # Wait up to 10 seconds for the URL to be parsed
            while not self.url and (time.time() - start_time) < 10:
                time.sleep(0.5)
                
            if not self.url:
                self.stop()
                raise Exception("Timeout esperando a que Cloudflare generara la URL.")
                
            return self.url

    def stop(self):
        """Detiene el túnel si está activo."""
        with self._lock:
            if self.process:
                logger.info("Cerrando Cloudflare Tunnel...")
                try:
                    self.process.terminate()
                    self.process.wait(timeout=3)
                except Exception:
                    self.process.kill()
                self.process = None
            self.url = None

    def get_url(self) -> str | None:
        return self.url

tunnel_manager = CloudflareTunnelManager()
