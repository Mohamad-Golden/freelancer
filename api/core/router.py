from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter
from fastapi.responses import JSONResponse
from sqlmodel import select, Session, func
from fastapi import Depends, Body
from pydantic import Field, EmailStr
from typing import List
from hashlib import md5
from datetime import datetime, timedelta

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
    Technology,
    TechnologyCreate,
    OfferCreate,
    Offer,
    PlanChange,
    ProjectList,
    UserUpdate,
    Experience,
    Education,
    SampleProject,
    UserTechnology,
    Comment,
    CommentIn,
)
from .utils import (
    get_session,
    validate_user,
    create_access_token,
    authenticate_user,
    authenticate_admin,
    Auth,
    sendmail,
)
from .types import PlanEnum
from sqlalchemy.exc import IntegrityError
from .responses import (
    conflict_exception,
    invalid_data_exception,
    not_found_exception,
    credentials_exception,
    permission_exception,
)

router = InferringRouter()
authenticated_router = InferringRouter()
admin_router = InferringRouter()


@cbv(router)
class Router:
    session: Session = Depends(get_session)

    @router.post(
        "/user",
        response_model=UserOut,
        status_code=201,
        response_model_exclude_none=True,
    )
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
            sendmail(user_in.email, verification_code.code)
            self.session.add(verification_code)
            self.session.commit()
            self.session.refresh(user)
            return user
        except IntegrityError:
            raise conflict_exception

    @router.get("/user", response_model=UserOut)
    def get_user_info(self, user_id: int):
        user = self.session.get(User, user_id)
        if user is None:
            raise not_found_exception
        avg_star = self.session.exec(
            select(Comment, func.avg(Comment.star).label("average")).where(
                Comment.to_user_id == self.user_id
            )
        )
        user.star = avg_star
        return user

    @router.post("/login")
    def login(self, user_in: UserLogin):
        user = validate_user(self.session, user_in.email, user_in.password)
        if user.is_verified:
            access_token = create_access_token({"sub": str(user.id)})
            response = JSONResponse(status_code=200, content={})
            response.set_cookie("access_token", access_token)
            return response
        else:
            raise credentials_exception

    @router.post("/user/verify")
    def verify_user(self, user_id: int = Body(), code: str = Body()):
        database_code = self.session.exec(
            select(UserVerificationCode).where(
                UserVerificationCode.code == code,
                UserVerificationCode.user_id == user_id,
                UserVerificationCode.expire_at > datetime.utcnow(),
            )
        ).first()
        if database_code:
            user = self.session.get(User, user_id)
            user.is_verified = True
            self.session.delete(database_code)
            self.session.add(user)
            self.session.commit()
            return JSONResponse(status_code=200, content={})
        else:
            raise invalid_data_exception

    @router.post("/password/forgot")
    def send_reset_password_token(self, email: EmailStr = Body(embed=True)):
        user = self.session.exec(select(User).where(User.email == email)).first()
        if user:
            past_token = self.session.exec(
                select(ResetPasswordToken, User).where(
                    User.email == email, ResetPasswordToken.user_id == User.id
                )
            )
            for token, _ in past_token:
                self.session.delete(token)

            reset_token = ResetPasswordToken(user=user)
            sendmail(email, reset_token.token)
            self.session.add(reset_token)
            self.session.commit()
            return JSONResponse(status_code=200, content={})
        else:
            raise not_found_exception

    @router.post("/password/reset/validate")
    def validate_reset_token(self, token: str = Body(), email: EmailStr = Body()):
        database_token = self.session.exec(
            select(ResetPasswordToken).where(
                User.email == email,
                ResetPasswordToken.token == token,
                ResetPasswordToken.user_id == User.id,
                ResetPasswordToken.expire_at > datetime.utcnow(),
            )
        ).first()
        if database_token:
            return JSONResponse(status_code=200, content={"detail": "valid"})
        else:
            raise invalid_data_exception

    @router.post("/password/reset")
    def reset_password(
        self, token: str = Body(), email: EmailStr = Body(), password: str = Body()
    ):
        result = self.session.exec(
            select(ResetPasswordToken, User).where(
                User.email == email,
                ResetPasswordToken.token == token,
                ResetPasswordToken.user_id == User.id,
                ResetPasswordToken.expire_at > datetime.utcnow(),
            )
        )
        for reset_token, user in result:
            user.hashed_password = md5(password.encode()).hexdigest()
            self.session.delete(reset_token)
            self.session.add(user)
            self.session.commit()
            return JSONResponse(status_code=200, content={})
        else:
            raise invalid_data_exception

    @router.get("/role", response_model=List[Role])
    def list_roles(self):
        return self.session.exec(select(Role)).all()

    @router.get("/plan", response_model=List[Plan])
    def list_plans(self):
        return self.session.exec(select(Plan)).all()

    @router.get(
        "/project", response_model=List[ProjectList], response_model_exclude_none=True
    )
    def list_projects(self):
        return self.session.exec(select(Project).order_by(Project.expire_at)).all()


@cbv(authenticated_router)
class AuthenticatedRouter:
    auth: Auth = Depends(authenticate_user)

    @authenticated_router.post(
        "/project",
        response_model=ProjectOut,
        status_code=201,
        response_model_exclude_none=True,
    )
    def create_project(self, project_in: ProjectIn):
        try:
            project = Project.from_orm(project_in)
            project.owner = self.auth.user
            if project_in.technologies_id:
                for tech_id in project_in.technologies_id:
                    self.auth.session.add(
                        ProjectTechnology(technology_id=tech_id, project=project)
                    )
            self.auth.session.commit()
            return project
        except IntegrityError:
            raise invalid_data_exception

    @authenticated_router.get(
        "/project/detail", response_model=ProjectOut, response_model_exclude_none=True
    )
    def get_project_detail(self, project_id: int):
        project = self.auth.session.get(Project, project_id)
        if project:
            return project
        else:
            raise not_found_exception

    @authenticated_router.put(
        "/user", response_model=UserOut, response_model_exclude_none=True
    )
    def update_user(self, user_in: UserUpdate):
        db_experiences = self.auth.session.exec(
            select(Experience).where(Experience.user_id == self.auth.user.id)
        ).all()
        db_educations = self.auth.session.exec(
            select(Education).where(Education.user_id == self.auth.user.id)
        ).all()
        db_sample_project = self.auth.session.exec(
            select(SampleProject).where(SampleProject.user_id == self.auth.user.id)
        ).all()
        db_technologies = self.auth.session.exec(
            select(UserTechnology).where(UserTechnology.user_id == self.auth.user.id)
        ).all()

        experiences_in = user_in.experiences.copy()
        for db_exp in db_experiences:
            is_in_input = False
            for exp_in in user_in.experiences:
                if db_exp.id == exp_in.id:
                    db_exp.from_orm(exp_in)
                    experiences_in.remove(exp_in)
                    is_in_input = True
            if is_in_input is False:
                self.auth.session.delete(db_exp)

        for exp_in in experiences_in:
            new_exp = Experience.from_orm(exp_in)
            self.auth.session.add(new_exp)

        educations_in = user_in.educations.copy()
        for db_edu in db_educations:
            is_in_input = False
            for edu_in in user_in.educations:
                if db_edu.id == edu_in.id:
                    db_edu.from_orm(edu_in)
                    educations_in.remove(edu_in)
                    is_in_input = True
            if is_in_input is False:
                self.auth.session.delete(db_edu)

        for edu_in in educations_in:
            new_edu = Education.from_orm(edu_in)
            self.auth.session.add(new_edu)

        sample_projects_in = user_in.sample_projects.copy()
        for sample_db in db_sample_project:
            is_in_input = False
            for sample_in in user_in.sample_projects:
                if sample_db.id == sample_in.id:
                    sample_db.from_orm(sample_in)
                    sample_projects_in.remove(sample_in)
                    is_in_input = True
            if is_in_input is False:
                self.auth.session.delete(sample_db)

        for sample_in in sample_projects_in:
            new_sample = SampleProject.from_orm(sample_in)
            self.auth.session.add(new_sample)

        technologies_id = user_in.technologies_id.copy()
        for tech_db in db_technologies:
            if tech_db.id in user_in.technologies_id:
                technologies_id.remove(tech_db.id)
            else:
                self.auth.session.delete(tech_db)

        for tech_id in technologies_id:
            new_user_tech = UserTechnology(technology_id=tech_id, user=self.auth.user)
            self.auth.session.add(new_user_tech)

        self.auth.session.commit()

    @authenticated_router.post("/offer", status_code=201)
    def create_offer(self, offer_in: OfferCreate):
        project = self.auth.session.get(Project, offer_in.project_id)
        if project:
            offer = Offer.from_orm(offer_in)
            offer.offerer = self.auth.user
            self.auth.session.add(offer)
            self.auth.session.commit()
            return JSONResponse(status_code=201, content={})
        else:
            raise not_found_exception

    @authenticated_router.post("/comment", status_code=201)
    def create_comment(self, comment_in: CommentIn):
        project = self.auth.session.get(Project, comment_in.project_id)
        if project is None:
            raise not_found_exception
        to_user = self.auth.session.get(User, comment_in.to_user_id)
        if to_user is None:
            raise not_found_exception

        try:
            new_comment = Comment.from_orm(comment_in)
            new_comment.from_user = self.auth.user
            self.auth.session.add(new_comment)
            self.auth.session.commit()
        except IntegrityError:
            raise permission_exception

    @authenticated_router.patch("/plan", response_model=PlanChange)
    def upgrade_user_plan(self, plan_id: int):
        if self.auth.user.plan.title != PlanEnum.free:
            raise permission_exception
        plan = self.auth.session.get(Plan, plan_id)
        if plan:
            self.auth.user.plan = plan
            match plan.title:
                case PlanEnum.bronze:
                    self.auth.user.plan_expire_at = datetime.utcnow() + timedelta(
                        days=30
                    )
                case PlanEnum.gold:
                    self.auth.user.plan_expire_at = datetime.utcnow() + timedelta(
                        days=60
                    )
                case PlanEnum.diamond:
                    self.auth.user.plan_expire_at = datetime.utcnow() + timedelta(
                        days=90
                    )
                case _:
                    self.auth.user.plan_expire_at = None

            self.auth.session.add(self.auth.user)
            self.auth.session.commit()
            return plan
        else:
            raise not_found_exception


@cbv(admin_router)
class AuthenticatedRouter:
    auth: Auth = Depends(authenticate_admin)

    @admin_router.post("/technology", response_model=Technology, status_code=201)
    def create_technology(self, technology_in: TechnologyCreate):
        try:
            technology = Technology.from_orm(technology_in)
            self.auth.session.add(technology)
            self.auth.session.commit()
            return technology
        except IntegrityError:
            raise conflict_exception
