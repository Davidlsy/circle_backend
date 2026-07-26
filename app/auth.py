import hashlib
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import bcrypt

from app.config import get_settings
from app.database import get_db
from app.models import User
from app.schemas import TokenData

settings = get_settings()

# OAuth2 scheme（前端按 Authorization: Bearer <token> 方式传 token）
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _prehash_password(password: str) -> bytes:
    """
    bcrypt 算法限制原始输入最长 72 字节。
    先用 SHA256 对密码做预哈希，得到固定 32 字节的 digest，
    再交给 bcrypt 处理，从而支持任意长度的密码。
    """
    return hashlib.sha256(password.encode("utf-8")).digest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与 bcrypt 哈希值是否匹配。"""
    prehash = _prehash_password(plain_password)
    return bcrypt.checkpw(prehash, hashed_password.encode("utf-8"))


def hash_password(password: str) -> str:
    """对密码进行 bcrypt 哈希（支持超过 72 字节的密码）。"""
    prehash = _prehash_password(password)
    return bcrypt.hashpw(prehash, bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    # python-jose 要求 sub 必须是字符串
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            return None
        return TokenData(user_id=user_id)
    except JWTError:
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """根据 JWT token 获取当前登录用户。未登录会抛出 401。"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token 无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = decode_token(token)
    if token_data is None:
        raise credentials_exception
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户已被禁用")
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户已被禁用")
    return current_user


async def get_current_active_user_optional(
    token: Optional[str] = Depends(OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    可选认证：已登录返回用户对象，未登录返回 None。
    用于评论列表等需要区分登录/未登录用户状态的场景。
    """
    if not token:
        return None
    token_data = decode_token(token)
    if token_data is None:
        return None
    user = db.query(User).filter(User.id == token_data.user_id, User.is_active == True).first()
    return user
