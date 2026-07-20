"""
Utilidad de encriptación para contraseñas de servidores.
Usa Fernet (AES-128-CBC) para encriptar/desencriptar.
"""
import os
import base64
import hashlib
from cryptography.fernet import Fernet

# Generamos una clave derivada del nombre de la máquina + salt fijo
# Esto garantiza que las contraseñas solo se puedan descifrar en esta máquina
_SALT = b"it-admin-platform-2026"
_MACHINE = os.environ.get("COMPUTERNAME", "default-machine").encode()
_KEY = base64.urlsafe_b64encode(hashlib.sha256(_SALT + _MACHINE).digest())


def encrypt_password(plain: str) -> str:
    """Encripta una contraseña en texto plano."""
    f = Fernet(_KEY)
    return f.encrypt(plain.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    """Desencripta una contraseña."""
    f = Fernet(_KEY)
    return f.decrypt(encrypted.encode()).decode()
