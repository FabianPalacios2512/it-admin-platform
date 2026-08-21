import asyncio
import json
from app.services.gpo_chat_agent import chat

async def main():
    print("Iniciando test de GPO Chat...")
    history = [
        {"role": "user", "content": "Hola, necesito crear una GPO para mapear una unidad de red"}
    ]
    
    print("\n--- TURNO 1 ---")
    print("User:", history[-1]["content"])
    res1 = await chat(history, [])
    print("Assistant:", res1["reply"])
    print("Proposal:", json.dumps(res1["proposal"]))
    
    history.append({"role": "assistant", "content": res1["reply"]})
    history.append({"role": "user", "content": "La ruta es \\\\servidor\\compartido"})
    
    print("\n--- TURNO 2 ---")
    print("User:", history[-1]["content"])
    res2 = await chat(history, [])
    print("Assistant:", res2["reply"])
    print("Proposal:", json.dumps(res2["proposal"]))
    
    history.append({"role": "assistant", "content": res2["reply"]})
    history.append({"role": "user", "content": "Quiero que use la letra Z: y sí, dale crea eso para todos"})
    
    print("\n--- TURNO 3 ---")
    print("User:", history[-1]["content"])
    res3 = await chat(history, [])
    print("Assistant:", res3["reply"])
    print("Proposal:", json.dumps(res3["proposal"]))

if __name__ == "__main__":
    asyncio.run(main())
