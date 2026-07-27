import os
import sys
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print('No API KEY found in .env')
    sys.exit(1)

client = genai.Client(api_key=api_key)

models_to_test = [
    'gemini-1.5-flash',
    'gemini-2.0-flash',
    'gemini-2.5-flash',
    'gemini-2.5-flash-lite',
    'gemini-3.0-flash',
    'gemini-3.5-flash',
    'gemini-3.5-flash-lite',
    'gemini-3.1-flash',
    'gemini-3.1-flash-lite',
    'gemini-3.6-flash'
]

print("Iniciando prueba de modelos...")
working_models = []

for model in models_to_test:
    print(f"\nProbando modelo: {model} ...", end=" ")
    try:
        response = client.models.generate_content(
            model=model,
            contents='Responde con la palabra "OK" si puedes leer esto.'
        )
        print(f"SUCCESS! Respuesta: {response.text.strip()}")
        working_models.append(model)
    except Exception as e:
        print(f"FAILED! Error: {e}")

print("\n==================================")
if not working_models:
    print("NINGÚN MODELO FUNCIONÓ.")
else:
    print(f"MODELOS QUE FUNCIONAN PERFECTAMENTE: {working_models}")
print("==================================\n")
