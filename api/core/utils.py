from jose import JWTError, jwt
from typing import Annotated, Union, List
from datetime import datetime, timedelta
from fastapi import Depends, Cookie, WebSocket
from ..settings import settings

from typing import Tuple

from .responses import credentials_exception, not_found_exception
from .models import User, Plan, Message
from sqlmodel import Session, select, or_
from hashlib import md5
from secrets import compare_digest
from ..db import get_engine
from .types import GeneralRole, PlanEnum

from sqlalchemy.exc import IntegrityError, DataError
from pydantic import BaseModel


class Auth:
    def __init__(self, user: User, session: Session) -> None:
        self.session = session
        self.user = user


def get_session() -> Session:
    engine = get_engine()
    with Session(engine) as session:
        yield session


def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SESSION_KEY, algorithm="HS256")
    return encoded_jwt


def get_user(
    session: Session,
    user_id: int = None,
    email: str = None,
    fail_silently: bool = False,
) -> User:
    if user_id:
        user = session.get(User, user_id)
    elif email:
        user = session.exec(select(User).where(User.email == email)).first()
    if user is None:
        if not fail_silently:
            raise not_found_exception
    return user


def authenticate_user(
    session: Session = Depends(get_session),
    access_token: str = Cookie(default=None, include_in_schema=False),
) -> Auth:
    if access_token is None:
        raise credentials_exception
    try:
        payload = jwt.decode(access_token, settings.SESSION_KEY, algorithms="HS256")
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(session, int(user_id))
    if user.plan_expire_at and user.plan_expire_at < datetime.utcnow():
        free_plan = session.exec(
            select(Plan).where(Plan.title == PlanEnum.free)
        ).first()
        user.plan = free_plan
        session.add(user)
        session.commit()
    return Auth(user, session)


def authenticate_admin(auth: Auth = Depends(authenticate_user)):
    if auth.user.role.title == GeneralRole.admin:
        return auth
    raise credentials_exception


def validate_user(session: Session, email: str, password: str) -> User:
    user = get_user(session, email=email, fail_silently=True)
    if user:
        hashed_password = md5(password.encode()).hexdigest()
        if compare_digest(user.hashed_password, hashed_password):
            return user
    raise credentials_exception


def sendmail(email: str, text: str):
    with open("mails", "a") as f:
        f.write(f"{email}: {text}\n")


def update_model(origin_obj, update_obj):
    update_data = update_obj.dict()
    for key, value in update_data.items():
        setattr(origin_obj, key, value)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append({user_id: websocket})

    def disconnect(self, user_id: int):
        del self.active_connections[user_id]

    async def send_personal_message(self, auth: Auth, message_block: dict):
        text = message_block.get("text")
        to_user_id = message_block.get("to_user_id")
        if to_user_id and text:
            receiver_socket = self.active_connections.get(to_user_id)
            if receiver_socket:
                await receiver_socket.send_json(
                    {
                        "text": text,
                        "to_user_id": to_user_id,
                        "from_user_id": auth.user.id,
                    }
                )
            try:
                message_db = Message(
                    text=text, to_user_id=to_user_id, from_user=auth.user
                )
                auth.session.add(message_db)
                auth.session.commit()
            except (IntegrityError, DataError):
                raise not_found_exception
