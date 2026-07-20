import os
import glob

base_path = os.path.dirname(os.path.abspath(__file__))
vue_files = glob.glob(os.path.join(base_path, 'frontend', 'src', '**', '*.vue'), recursive=True)

replacements = {
    "Ã¡": "á",
    "Ã©": "é",
    "Ã­": "í",
    "Ã³": "ó",
    "Ãº": "ú",
    "Ã±": "ñ",
    "Ã\x81": "Á",
    "Ã‰": "É",
    "Ã\x8d": "Í",
    "Ã“": "Ó",
    "Ã”": "Ú",
    "Ã‘": "Ñ",
    "Ã¼": "ü",
    "Ã\x9c": "Ü",
    "Â¿": "¿",
    "Â¡": "¡",
    "â€”": "—"
}

for file_path in vue_files:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        fixed_content = content
        for bad, good in replacements.items():
            fixed_content = fixed_content.replace(bad, good)
            
        fixed_content = fixed_content.replace('http://localhost:8000/api/v1', '/api/v1')
            
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
            
        print(f"Arreglado: {os.path.basename(file_path)}")
    except Exception as e:
        print(f"No se pudo arreglar {file_path}: {e}")

print("Terminado.")
