import asyncio
import json
from app.services.gpo_chat_agent import chat

async def main():
    print("Iniciando test de GPO Chat con consulta de OU...")
    history = [
        {"role": "user", "content": "Quiero crear una gpo de bloqueo de pantalla. ¿qué OUs tenemos actualmente y en cuál me recomiendas ponerla? la quiero solo para el departamento de ti"}
    ]
    
    print("\n--- TURNO 1 ---")
    print("User:", history[-1]["content"])
    res1 = await chat(history, [])
    print("\nAssistant:", res1["reply"])
    print("\nProposal:", json.dumps(res1["proposal"]))

if __name__ == "__main__":
    asyncio.run(main())
