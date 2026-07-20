from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt

from app.services.ldap_auth import authenticate_ldap

router = APIRouter()

SECRET_KEY = "key_corporativa_super_secreta"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    display_name: str

@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest):
    auth_result = authenticate_ldap(credentials.username, credentials.password)
    
    if not auth_result.get("authenticated"):
        error_detail = auth_result.get("error", "Credenciales de dominio inválidas o acceso denegado.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": credentials.username,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return {
        "access_token": encoded_jwt,
        "token_type": "bearer",
        "display_name": auth_result.get("display_name", credentials.username)
    }
