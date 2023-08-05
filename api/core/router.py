from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter
from fastapi.responses import JSONResponse
from sqlmodel import select, Session
from fastapi import Depends, Body
from pydantic import Field, EmailStr
from typing import List
from hashlib import md5
from datetime import datetime

from .models import (
    UserCreate,
    UserOut,
    User,
    Plan,
    Role,
    UserVerificationCode,
    ResetPasswordToken,
    Project,
    ProjectIn,
    ProjectOut,
    ProjectTechnology,
    UserLogin,
)
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
from sqlalchemy.exc import IntegrityError
from .responses import conflict_exception, invalid_data_exception, not_found_exception

router = InferringRouter()
authenticated_router = InferringRouter()
admin_router = InferringRouter()


@cbv(router)
class Router:
    session: Session = Depends(get_session)

    @router.post("/user", response_model=UserOut, status_code=201)
    def create_user(self, user_in: UserCreate):
        plan = self.session.exec(
            select(Plan).where(Plan.title == PlanEnum.free)
        ).first()
        role = self.session.exec(select(Role).where(Role.title == user_in.role)).first()
        user = User.from_orm(
            user_in,
            update={
                "hashed_password": md5(user_in.password.encode()).hexdigest(),
            },
        )
        try:
            user.plan = plan
            user.role = role
            self.session.add(user)
            verification_code = UserVerificationCode(user=user)
            self.session.add(verification_code)
            self.session.commit()
            self.session.refresh(user)
            return user
        except IntegrityError:
            raise conflict_exception

    @router.post("/login")
    def login(self, user: UserLogin):
        user = validate_user(self.session, user.email, user.password)
        access_token = create_access_token({"sub": str(user.id)})
        response = JSONResponse(status_code=200, content={})
        response.set_cookie("access_token", access_token)
        return response

    @router.post("/user/verify")
    def verify_user(self, user_id: int = Body(), code: str = Body()):
        database_code = self.session(
            select(UserVerificationCode).where(
                UserVerificationCode.code == code,
                UserVerificationCode.user_id == user_id,
                UserVerificationCode.expire_at > datetime.utcnow(),
            )
        )
        if database_code:
            user = self.session.get(User, user_id)
            user.is_verified = True
            self.session.add(user)
            self.session.commit()
        else:
            raise invalid_data_exception

    @router.post("/password/reset/validate")
    def validate_reset_token(self, token: str = Body()):
        database_token = self.session.get(ResetPasswordToken, token)
        if database_token and database_token.expire_at > datetime.utcnow():
            JSONResponse(status_code=200, content={"detail": "valid"})
        else:
            raise invalid_data_exception

    @router.post("/password/reset")
    def reset_password(self, token: str = Body(), password: str = Body()):
        database_token = self.session.get(ResetPasswordToken, token)
        if database_token and database_token.expire_at > datetime.utcnow():
            user = database_token.user
            user.hashed_password = md5(password.encode()).hexdigest()
            self.session.add(user)
            self.session.commit()
        else:
            raise invalid_data_exception

    @router.get("/role", response_model=List[Role])
    def list_roles(self):
        return self.session.exec(select(Role)).all()

    @router.get("/plan", response_model=List[Plan])
    def list_roles(self):
        return self.session.exec(select(Plan)).all()


@cbv(authenticated_router)
class AuthenticatedRouter:
    auth: Auth = Depends(authenticate_user)

    @authenticated_router.post("/project", response_model=ProjectOut, status_code=201)
    def create_project(self, project_in: ProjectIn):
        try:
            project = Project.from_orm(project_in, update={"owner": self.auth.user})
            if project_in.technologies_id:
                for tech_id in project_in.technologies_id:
                    self.auth.session.add(
                        ProjectTechnology(technology_id=tech_id, project=project)
                    )
            self.auth.session.commit()
            return project
        except IntegrityError:
            raise invalid_data_exception

    @authenticated_router.get("/project", response_model=ProjectOut)
    def get_project_detail(self, project_id: int):
        project = self.auth.session.get(Project, project_id)
        if project:
            return project
        else:
            raise not_found_exception


@cbv(admin_router)
class AuthenticatedRouter:
    auth: Auth = Depends(authenticate_admin)

    @admin_router.post("/b", response_model=UserOut, status_code=201)
    def b(self, user: UserCreate):
        return
