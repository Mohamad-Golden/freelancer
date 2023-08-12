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
    SampleProjectOut,
    ExperienceOut,
    EducationOut,
    TechnologyOut,
    PickDoer
)
from .utils import (
    get_session,
    validate_user,
    create_access_token,
    authenticate_user,
    authenticate_admin,
    Auth,
    sendmail,
    update_model,
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

    @router.get("/user", response_model=UserOut, response_model_exclude_none=True)
    def get_user_info(self, user_id: int):
        user = self.session.get(User, user_id)
        if user is None:
            raise not_found_exception
        avg_star = self.session.exec(
            select(func.avg(Comment.star).label("average")).where(
                Comment.to_user_id == user_id
            )
        ).first()
        user_out = UserOut.from_orm(user)
        user_out.star = avg_star if avg_star else 0
        return user_out

    @router.post("/login")
    def login(self, user_in: UserLogin):
        user = validate_user(self.session, user_in.email, user_in.password)
        if user.is_verified:
            access_token = create_access_token({"sub": str(user.id)})
            response = JSONResponse(status_code=200, content={})
            response.set_cookie(
                key="access_token",
                value=access_token,
                expires=15 * 24 * 60 * 60,
                httponly=True,
                secure=True,
            )
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
        project_technologies = []
        try:
            project = Project.from_orm(project_in)
            project.owner = self.auth.user
            if project_in.technologies_id:
                for tech_id in project_in.technologies_id:
                    project_tech = ProjectTechnology(
                        technology_id=tech_id, project=project
                    )
                    self.auth.session.add(project_tech)
                    self.auth.session.commit()
                    self.auth.session.refresh(project_tech)
                    if project_tech.technology:
                        project_technologies.append(
                            TechnologyOut.from_orm(project_tech.technology)
                        )

            self.auth.session.commit()
            project_out = ProjectOut.from_orm(project)
            project_out.technologies = project_technologies
            # print(project_out.technologies[0].title)
            return project_out
        except IntegrityError:
            raise invalid_data_exception

    @authenticated_router.get(
        "/project/detail", response_model=ProjectOut, response_model_exclude_none=True
    )
    def get_project_detail(self, project_id: int):
        project = self.auth.session.get(Project, project_id)
        if project:
            technologies = []
            for tech_project in project.project_technologies:
                technologies.append(TechnologyOut.from_orm(tech_project.technology))
            project_out = ProjectOut.from_orm(project)
            project_out.technologies = technologies
            return project_out
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

        technologies_in_list = (
            user_in.technologies_id if user_in.technologies_id else []
        )
        educations_in_list = user_in.educations if user_in.educations else []
        experiences_in_list = user_in.experiences if user_in.experiences else []
        sample_projects_in_list = (
            user_in.sample_projects if user_in.sample_projects else []
        )

        technologies_list = []
        educations_list = []
        experiences_list = []
        sample_projects_list = []
        try:
            experiences_in = experiences_in_list.copy()
            for db_exp in db_experiences:
                is_in_input = False
                for exp_in in experiences_in_list:
                    if db_exp.id == exp_in.id:
                        update_model(db_exp, exp_in)
                        self.auth.session.add(db_exp)
                        experiences_list.append(ExperienceOut.from_orm(db_exp))
                        experiences_in.remove(exp_in)
                        is_in_input = True
                if is_in_input is False:
                    self.auth.session.delete(db_exp)

            for exp_in in experiences_in:
                exp_in.id = None
                new_exp = Experience.from_orm(exp_in)
                new_exp.user = self.auth.user
                self.auth.session.add(new_exp)
                experiences_list.append(ExperienceOut.from_orm(new_exp))

            educations_in = educations_in_list.copy()
            for db_edu in db_educations:
                is_in_input = False
                for edu_in in educations_in_list:
                    if db_edu.id == edu_in.id:
                        update_model(db_edu, edu_in)
                        self.auth.session.add(db_edu)
                        educations_list.append(EducationOut.from_orm(db_edu))
                        educations_in.remove(edu_in)
                        is_in_input = True
                if is_in_input is False:
                    self.auth.session.delete(db_edu)

            for edu_in in educations_in:
                edu_in.id = None
                new_edu = Education.from_orm(edu_in)
                new_edu.user = self.auth.user
                self.auth.session.add(new_edu)
                educations_list.append(EducationOut.from_orm(new_edu))

            sample_projects_in = sample_projects_in_list.copy()
            for sample_db in db_sample_project:
                is_in_input = False
                for sample_in in sample_projects_in_list:
                    if sample_db.id == sample_in.id:
                        update_model(sample_db, sample_in)
                        self.auth.session.add(sample_db)
                        sample_projects_list.append(
                            SampleProjectOut.from_orm(sample_db)
                        )
                        sample_projects_in.remove(sample_in)
                        is_in_input = True
                if is_in_input is False:
                    self.auth.session.delete(sample_db)

            for sample_in in sample_projects_in:
                sample_in.id = None
                new_sample = SampleProject.from_orm(sample_in)
                new_sample.user = self.auth.user
                self.auth.session.add(new_sample)
                sample_projects_list.append(SampleProjectOut.from_orm(new_sample))

            technologies_id = technologies_in_list.copy()
            for tech_db in db_technologies:
                if tech_db.technology_id in technologies_in_list:
                    technologies_list.append(TechnologyOut.from_orm(tech_db.technology))
                    technologies_id.remove(tech_db.technology_id)
                else:
                    self.auth.session.delete(tech_db)

            for tech_id in technologies_id:
                tech = self.auth.session.get(Technology, tech_id)
                new_user_tech = UserTechnology(technology=tech, user=self.auth.user)
                self.auth.session.add(new_user_tech)
                technologies_list.append(TechnologyOut.from_orm(tech))
            self.auth.session.commit()
        except IntegrityError:
            raise invalid_data_exception

        user_out = UserOut.from_orm(self.auth.user)
        user_out.experiences = experiences_list
        user_out.educations = educations_list
        user_out.sample_projects = sample_projects_list
        user_out.technologies = technologies_list
        avg_star = self.auth.session.exec(
            select(func.avg(Comment.star).label("average")).where(
                Comment.to_user_id == self.auth.user.id
            )
        ).first()
        user_out.star = avg_star if avg_star else 0
        return user_out

    @authenticated_router.post("/offer", status_code=201)
    def create_offer(self, offer_in: OfferCreate):
        if self.auth.user.offer_left > 0:
            try:
                offer = Offer.from_orm(offer_in)
                offer.offerer = self.auth.user
                self.auth.session.add(offer)
                self.auth.user.offer_left = self.auth.user.offer_left - 1
                self.auth.session.add(self.auth.user)
                self.auth.session.commit()
                return JSONResponse(status_code=201, content={})
            except IntegrityError:
                raise permission_exception
        else:
            raise permission_exception

    @authenticated_router.post("/doer", response_model=PickDoer)
    def add_doer(self, project_id: int, doer_id: int):
        project = self.auth.session.get(Project, project_id)
        if project and project.owner == self.auth.user and project.doer is None:
            try:
                project.doer_id = doer_id
                self.auth.session.add(project)
                self.auth.session.commit()
                self.auth.session.refresh(project)
                return PickDoer(doer=project.doer)
            except IntegrityError:
                raise permission_exception
        else:
            raise permission_exception

    @authenticated_router.post("/comment", status_code=201)
    def create_comment(self, comment_in: CommentIn):
        project = self.auth.session.get(Project, comment_in.project_id)
        if project is None:
            raise not_found_exception
        to_user = self.auth.session.get(User, comment_in.to_user_id)
        if to_user is None:
            raise not_found_exception
        if (
            self.auth.user == project.doer
            or self.auth.user == project.owner
            or self.auth.user == to_user
        ):
            try:
                new_comment = Comment.from_orm(comment_in)
                new_comment.from_user = self.auth.user
                self.auth.session.add(new_comment)
                self.auth.session.commit()
                return JSONResponse(status_code=201, content={})
            except IntegrityError:
                raise permission_exception
        else:
            raise permission_exception

    @authenticated_router.patch("/plan", response_model=PlanChange)
    def upgrade_user_plan(self, plan_id: int):
        plan = self.auth.session.get(Plan, plan_id)
        if plan.title == PlanEnum.free:
            raise permission_exception

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
            self.auth.user.offer_left = self.auth.user.offer_left + plan.offer_number
            self.auth.session.add(self.auth.user)
            self.auth.session.commit()
            return plan
        else:
            raise not_found_exception


@cbv(admin_router)
class AuthenticatedRouter:
    auth: Auth = Depends(authenticate_admin)

    @admin_router.post("/technology", response_model=TechnologyOut, status_code=201)
    def create_technology(self, technology_in: TechnologyCreate):
        try:
            technology = Technology.from_orm(technology_in)
            self.auth.session.add(technology)
            self.auth.session.commit()
            return technology
        except IntegrityError:
            raise conflict_exception
