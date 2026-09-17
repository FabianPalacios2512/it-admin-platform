import os
import json
import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Cargar todas las llaves de Groq
GROQ_KEYS = []
for i in range(1, 20):
    key = os.getenv(f"GROQ_API_KEY_{i}")
    if key:
        GROQ_KEYS.append(key)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class AIFallbackManager:
    def __init__(self):
        self.current_groq_index = 0
        self.groq_model = "llama-3.3-70b-versatile" # "llama-3.1-70b-versatile" or mixtral depending on availability
        
    async def analyze_logs(self, ip: str, logs: str) -> Dict[str, Any]:
        """
        Analiza logs usando Groq con rotación. Si todas fallan, usa Gemini.
        """
        prompt = f"""
        Actúa como un Analista Senior de Ciberseguridad.
        Analiza los siguientes logs de intentos de conexión para la IP {ip}.
        Determina si el comportamiento es malicioso (ataque de fuerza bruta, escaneo de puertos, intentos repetidos fallidos, etc.) o si parece un falso positivo (ej. un usuario legítimo que olvidó su contraseña una vez).
        
        LOGS:
        {logs}
        
        Devuelve estrictamente un objeto JSON con dos propiedades:
        - "is_malicious": booleano (true si es un ataque real, false si es falso positivo o tráfico benigno)
        - "summary": un breve y claro resumen en español de lo que hizo la IP y por qué tomaste la decisión (máximo 3 oraciones). No uses markdown en el JSON.
        """
        
        # Intentar con Groq
        for _ in range(len(GROQ_KEYS)):
            if not GROQ_KEYS:
                break
                
            key = GROQ_KEYS[self.current_groq_index]
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.groq_model,
                            "messages": [
                                {"role": "system", "content": "You are a cybersecurity expert. Output ONLY valid JSON, no markdown formatting like ```json."},
                                {"role": "user", "content": prompt}
                            ],
                            "response_format": {"type": "json_object"}
                        }
                    )
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data["choices"][0]["message"]["content"]
                        return json.loads(content)
                    elif resp.status_code == 429:
                        logger.warning(f"Groq Key {self.current_groq_index + 1} rate limited. Rotating...")
                        self._rotate_key()
                    else:
                        logger.error(f"Groq API error {resp.status_code}: {resp.text}")
                        self._rotate_key()
            except Exception as e:
                logger.error(f"Groq request failed: {str(e)}")
                self._rotate_key()
                
        # Si todas fallaron o no hay Groq keys, usar Gemini
        logger.warning("Todas las llaves de Groq fallaron. Usando Gemini como fallback.")
        return await self._analyze_with_gemini(prompt)
        
    def _rotate_key(self):
        if GROQ_KEYS:
            self.current_groq_index = (self.current_groq_index + 1) % len(GROQ_KEYS)
            
    async def _analyze_with_gemini(self, prompt: str) -> Dict[str, Any]:
        if not GEMINI_API_KEY:
            logger.error("No hay Gemini API key disponible.")
            return {"is_malicious": True, "summary": "Alerta generada. Análisis IA fallido (Sin Keys)."}
            
        try:
            # Using HTTP for Gemini to avoid dependency issues with google-genai versioning
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": "You are a cybersecurity expert. Output ONLY valid JSON.\n\n" + prompt}]}],
                        "generationConfig": {
                            "responseMimeType": "application/json"
                        }
                    }
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(content)
                else:
                    logger.error(f"Gemini API error {resp.status_code}: {resp.text}")
                    return {"is_malicious": True, "summary": f"Alerta generada. Análisis IA fallido (Gemini error {resp.status_code})."}
        except Exception as e:
            logger.error(f"Gemini request failed: {str(e)}")
            return {"is_malicious": True, "summary": "Alerta generada. Análisis IA fallido."}

llm_rotator = AIFallbackManager()
