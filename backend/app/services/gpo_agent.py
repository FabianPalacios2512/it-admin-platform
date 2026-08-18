import logging
from typing import Optional

from google import genai
from google.genai import types

from app.core.config import env_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Eres un Administrador de Sistemas Senior experto en Active Directory y PowerShell.
Tu única responsabilidad es generar scripts de PowerShell para crear o modificar Políticas de Grupo (GPOs) en Windows Server, basándote en la solicitud del usuario.

REGLAS ESTRICTAS E INQUEBRANTABLES:
1. SOLO debes responder con el código de PowerShell.
2. NO incluyas explicaciones, saludos, ni comentarios fuera del bloque de código.
3. El código debe estar dentro de un bloque de código markdown (```powershell ... ```).
4. El script debe usar módulos estándar como GroupPolicy (New-GPO, Set-GPRegistryValue, Set-GPPrefRegistryValue, etc.).
5. Asume que el módulo GroupPolicy ya está disponible o el script se ejecutará en un Controlador de Dominio.
6. Si la política requiere una ruta (ej. para un fondo de pantalla o mapear unidad), incluye comentarios inline claros para que el usuario sepa que debe reemplazarlos si no fueron especificados en el prompt.
7. Crea el objeto de GPO con un nombre descriptivo basado en la solicitud si no se provee uno.
8. NO vincules (link) el GPO a ningún OU o al dominio por defecto, solo crea el GPO y sus configuraciones. El usuario la vinculará después manualmente.
"""

class GpoAgent:
    def __init__(self):
        api_key = env_settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY no está configurada en el archivo .env."
            )
        self.client = genai.Client(api_key=api_key)

    async def generate_gpo_script(self, user_prompt: str) -> str:
        """
        Envía un prompt al LLM y devuelve el script de PowerShell generado.
        """
        logger.info(f"Generating GPO for prompt: {user_prompt}")
        
        try:
            response = self.client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.1, # Baja temperatura para código determinista
                ),
            )
            
            text = response.text
            # Extraer el código del bloque de markdown
            if "```powershell" in text.lower():
                # Extraer todo lo que está entre ```powershell y ```
                start_idx = text.lower().find("```powershell") + len("```powershell")
                end_idx = text.lower().find("```", start_idx)
                if end_idx != -1:
                    text = text[start_idx:end_idx].strip()
            elif "```" in text:
                start_idx = text.find("```") + 3
                end_idx = text.find("```", start_idx)
                if end_idx != -1:
                    text = text[start_idx:end_idx].strip()
                    
            return text
        except Exception as e:
            logger.error(f"Error generando GPO: {e}")
            raise e
