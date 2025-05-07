from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security, APIRouter, Depends, status, Form
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
SUPERUSER_USERNAME = os.getenv("SUPERUSER_USERNAME", "morgan")
SUPERUSER_PASSWORD = os.getenv("SUPERUSER_PASSWORD", "Mushroom1!")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: list[str] = []

class AuthService:
    def __init__(self):
        self.secret_key = SECRET_KEY
        self.algorithm = ALGORITHM
        self.access_token_expire_minutes = ACCESS_TOKEN_EXPIRE_MINUTES

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str = Security(oauth2_scheme)) -> Dict[str, Any]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Could not validate credentials")

    def get_api_key(self, api_name: str) -> str:
        """Get API key from environment variables"""
        api_key = os.getenv(f"{api_name.upper()}_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail=f"{api_name} API key not configured")
        return api_key

    def validate_api_key(self, api_name: str, provided_key: str) -> bool:
        """Validate provided API key against stored key"""
        stored_key = self.get_api_key(api_name)
        return stored_key == provided_key

    def create_api_token(self, api_name: str, scopes: list[str] = None) -> str:
        """Create a token for API access with specific scopes"""
        if scopes is None:
            scopes = []
        data = {
            "sub": api_name,
            "scopes": scopes
        }
        return self.create_access_token(data)

    def verify_api_token(self, token: str, required_scopes: list[str] = None) -> bool:
        """Verify API token and required scopes"""
        if required_scopes is None:
            required_scopes = []
        try:
            payload = self.verify_token(token)
            token_scopes = payload.get("scopes", [])
            for scope in required_scopes:
                if scope not in token_scopes:
                    raise HTTPException(status_code=403, detail="Not enough permissions")
            return True
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid API token")

    def authenticate_superuser(self, username: str, password: str) -> bool:
        return username == SUPERUSER_USERNAME and password == SUPERUSER_PASSWORD

    def create_superuser_token(self) -> str:
        data = {"sub": SUPERUSER_USERNAME, "role": "superuser"}
        return self.create_access_token(data)

# FastAPI login endpoint
router = APIRouter()

auth_service = AuthService()

@router.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    if not auth_service.authenticate_superuser(username, password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = auth_service.create_superuser_token()
    return {"access_token": token, "token_type": "bearer"} 