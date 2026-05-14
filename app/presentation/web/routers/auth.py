from fastapi import APIRouter, Request, Form, Response, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from datetime import datetime, timedelta
import hashlib
import uuid
from jose import jwt
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from config import get_settings
from ....infrastructure.database.connection import get_session
from ....infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from ....domain.entities.user import User as DomainUser

router = APIRouter()
settings = get_settings()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(request: Request, session: AsyncSession = Depends(get_session)) -> DomainUser | None:
    token = request.cookies.get("access_token")
    if not token or not token.startswith("Bearer "):
        return None
    token = token.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("id")
        if not user_id:
            return None
            
        user_repo = SQLAlchemyUserRepository(session)
        user = await user_repo.get_by_id(uuid.UUID(user_id))
        return user
    except Exception:
        return None

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_session)
):
    user_repo = SQLAlchemyUserRepository(session)
    user = await user_repo.get_by_email(email)
    
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "Email ou senha incorretos."
        }, status_code=status.HTTP_400_BAD_REQUEST)
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "id": str(user.id)}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token", 
        value=f"Bearer {access_token}", 
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    return response

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
async def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_session)
):
    user_repo = SQLAlchemyUserRepository(session)
    existing_user = await user_repo.get_by_email(email)
    if existing_user:
        return templates.TemplateResponse("register.html", {
            "request": request, 
            "error": "Este email já está cadastrado."
        }, status_code=status.HTTP_400_BAD_REQUEST)
        
    new_user = DomainUser(
        id=uuid.uuid4(),
        email=email,
        name=name,
        hashed_password=hash_password(password)
    )
    await user_repo.create(new_user)
    
    # Auto-login after registration
    return await login(request, email, password, session)

@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    return response
