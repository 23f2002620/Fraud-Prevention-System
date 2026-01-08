from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt
from jose.exceptions import JWTError
from passlib.context import CryptContext

from app.core.config import settings
from app.core.security import create_access_token, ALGORITHM

router = APIRouter(tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# For college MVP: single admin user from config
_admin_hash = pwd_context.hash(settings.admin_password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


@router.post("/token")
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    if form_data.username != settings.admin_username:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if not verify_password(form_data.password, _admin_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    token = create_access_token(subject=form_data.username, secret_key=settings.jwt_secret_key)
    return {"access_token": token, "token_type": "bearer"}


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        exp = payload.get("exp")
        if sub is None or exp is None:
            raise credentials_exc
        # optional: basic expiry sanity check (jwt lib checks exp too, but keep simple)
        return str(sub)
    except JWTError:
        raise credentials_exc


CurrentUser = Annotated[str, Depends(get_current_user)]
