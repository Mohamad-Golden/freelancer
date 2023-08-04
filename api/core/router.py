from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter
from fastapi.responses import JSONResponse
from sqlmodel import select, Session
from fastapi import Depends
from typing import List
from hashlib import md5

from .models import UserCreate, UserOut, User, Plan, Role
from .utils import (
    get_session,
    validate_user,
    get_user,
    create_access_token,
    authenticate_user,
    authenticate_admin,
    Auth,
)
from .types import PlanEnum

router = InferringRouter()
authenticated_router = InferringRouter()
admin_router = InferringRouter()


@cbv(router)
class Router:
    session: Session = Depends(get_session)

    @router.post("/user", response_model=UserOut, status_code=201)
    def create_user(self, user: UserCreate):
        plan = self.session.exec(select(Plan).where(Plan.title == PlanEnum.free))
        role = self.session.exec(select(Role).where(Role.title == user.role))
        user = User.from_orm(
            user,
            update={
                "plan": plan,
                "role": role,
                "hashed_password": md5(user.password.encode()).hexdigest(),
            },
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    @router.post("/login", status_code=200)
    def login(self, user: UserCreate):
        user = get_user(self.session, email=user.email)
        user = validate_user(self.session, user.id, user.password)
        access_token = create_access_token({"sub": user.id})
        response = JSONResponse(status_code=200)
        response.set_cookie("access_token", access_token)
        return response

    @router.get("/role", response_model=List[Role])
    def list_roles(self):
        return self.session.exec(select(Role).all())


@cbv(authenticated_router)
class AuthenticatedRouter:
    auth: Auth = Depends(authenticate_user)

    @router.post("/a", response_model=UserOut, status_code=201)
    def a(self, user: UserCreate):
        return


@cbv(admin_router)
class AuthenticatedRouter:
    auth: Auth = Depends(authenticate_admin)

    @router.post("/b", response_model=UserOut, status_code=201)
    def b(self, user: UserCreate):
        return
