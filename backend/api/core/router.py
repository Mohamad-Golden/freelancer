import os
from datetime import datetime, timedelta
from hashlib import md5
from typing import List, Optional

from fastapi import BackgroundTasks, Body, Depends, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter
from pydantic import EmailStr
from slugify import slugify
from sqlalchemy.exc import DataError, IntegrityError
from sqlmodel import Session, and_, func, or_, select, update

from ..settings import settings
from .models import (
    Comment,
    CommentIn,
    Education,
    EducationOut,
    Experience,
    ExperienceOut,
    Follower,
    Message,
    Offer,
    OfferCreate,
    PickDoer,
    Plan,
    PlanChange,
    PlanCreate,
    PlanUpdate,
    Project,
    ProjectIn,
    ProjectList,
    ProjectOut,
    ProjectTechnology,
    ResetPasswordToken,
    Role,
    SampleProject,
    SampleProjectOut,
    Status,
    Technology,
    TechnologyCreate,
    TechnologyOut,
    User,
    UserCreate,
    UserLogin,
    UserOut,
    UserShortOut,
    UserTechnology,
    UserUpdate,
    UserVerificationCode,
)
from .responses import (
    conflict_exception,
    credentials_exception,
    invalid_data_exception,
    not_found_exception,
    permission_exception,
)
from .types import PlanEnum, ProjectStatusEnum, SortDirEnum, SortEnum
from .utils import (
    Auth,
    ConnectionManager,
    authenticate_admin,
    authenticate_user,
    create_access_token,
    get_session,
    sendmail,
    update_model,
    validate_user,
)

router = InferringRouter()
authenticated_router = InferringRouter()
admin_router = InferringRouter()

connection_manager = ConnectionManager()
html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <input type="text" id="toUser"/> 
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:8000/api/chat/ws");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var user = document.getElementById('toUser')
                var input = document.getElementById("messageText")
                ws.send(JSON.stringify({text: input.value, to_user_id: user.value}))
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


@cbv(router)
class Router:
    session: Session = Depends(get_session)

    @router.get("/chat/test")
    async def get(self):
        return HTMLResponse(html)

    @router.post(
        "/user",
        response_model=UserOut,
        status_code=201,
        response_model_exclude_none=True,
    )
    def create_user(self, user_in: UserCreate, background_task: BackgroundTasks):
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
            user.offer_left = plan.offer_number
            self.session.add(user)
            verification_code = UserVerificationCode(user=user)
            background_task.add_task(sendmail, user_in.email, verification_code.code)
            self.session.add(verification_code)
            self.session.commit()
            self.session.refresh(user)
            return user
        except IntegrityError:
            raise conflict_exception

    @router.post(
        "/verify/resend",
    )
    def resend_verify_code(self, user_id: int, background_task: BackgroundTasks):
        try:
            user = self.session.get(User, user_id)
            if user is None:
                raise not_found_exception

            verification_code = UserVerificationCode(user_id=user_id)
            background_task.add_task(sendmail, user.email, verification_code.code)
            self.session.add(verification_code)
            self.session.commit()
            return JSONResponse(status_code=200, content={})
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
    def send_reset_password_token(
        *, self, email: EmailStr = Body(embed=True), background_task: BackgroundTasks
    ):
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
            background_task.add_task(sendmail, email, reset_token.token)
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
    def list_projects(
        self,
        tech: List[str] | None = Query(None, max_length=30),
        title: str | None = None,
        sort: SortEnum = SortEnum.date,
        sort_dir: SortDirEnum = SortDirEnum.descending,
        min_price: Optional[int] = 0,
        max_price: Optional[int] = None,
        is_open: Optional[bool] = Query(None, alias="open"),
        page: int = 1,
        limit: int = Query(10, lt=51),
    ):
        select_clause = [Project, Status]
        where_clause = [
            Project.status_id == Status.id,
            Project.price_to >= min_price,
        ]
        second_where_clause = [
            Project.price_to >= min_price,
        ]
        if max_price:
            where_clause.append(
                Project.price_to <= max_price,
            )
            second_where_clause.append(
                Project.price_to <= max_price,
            )
        if is_open is not None:
            open_clause = (
                Status.title == ProjectStatusEnum.unassigned
                if is_open
                else Status.title != ProjectStatusEnum.unassigned
            )
            where_clause.append(open_clause)
            second_where_clause.append(open_clause)

        if tech:
            where_clause += [
                Project.id == ProjectTechnology.project_id,
                Technology.id == ProjectTechnology.technology_id,
                Technology.slug.in_(tech),
            ]
            select_clause += [ProjectTechnology, Technology]

        if title:
            where_clause.append(
                Project.title.like("%" + title + "%"),
            )
            second_where_clause.append(
                Project.title.like("%" + title + "%"),
            )

        result = self.session.exec(
            select(*select_clause)
            .where(*where_clause)
            .order_by(getattr(getattr(Project, sort.value), sort_dir.value)())
            .where(
                Project.id.in_(
                    select(Project.id)
                    .join(Status)
                    .where(*second_where_clause)
                    .order_by(getattr(getattr(Project, sort.value), sort_dir.value)())
                    .offset((page - 1) * limit)
                    .limit(limit)
                )
            )
        )
        projects = []
        current_project = None
        for res in result:
            pro = res[0]
            if current_project is None:
                current_project = ProjectList.from_orm(pro)
                current_project.technologies = []
                for t in pro.project_technologies:
                    current_project.technologies.append(t.technology)

                last_id = pro.id
                projects.append(current_project)

            elif pro.id != last_id:
                current_project = ProjectList.from_orm(pro)
                current_project.technologies = []
                for t in pro.project_technologies:
                    current_project.technologies.append(t.technology)
                projects.append(current_project)
                last_id = current_project.id

        return projects


@cbv(authenticated_router)
class AuthenticatedRouter:
    auth: Auth = Depends(authenticate_user)

    @authenticated_router.delete(
        "/user",
        response_model=UserOut,
        response_model_exclude_none=True,
    )
    def delete_user(self):
        self.auth.session.delete(self.auth.user)
        self.auth.session.commit()
        return JSONResponse(status_code=200, content={})

    @authenticated_router.post(
        "/project",
        response_model=ProjectOut,
        status_code=201,
        response_model_exclude_none=True,
    )
    def create_project(self, project_in: ProjectIn):
        project_technologies = []
        if not self.auth.user.is_verified:
            raise permission_exception
        try:
            project = Project.from_orm(project_in)
            project.owner = self.auth.user
            status = self.auth.session.exec(
                select(Status).where(Status.title == ProjectStatusEnum.unassigned)
            ).first()
            project.status = status
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
            return project_out

        except (IntegrityError, DataError):
            raise invalid_data_exception

    @authenticated_router.get(
        "/my-assigned/projects",
        response_model=List[ProjectList],
        response_model_exclude_none=True,
    )
    def list_my_assigned_projects(
        self,
        title: str | None = None,
        sort: SortEnum = SortEnum.date,
        sort_dir: SortDirEnum = SortDirEnum.descending,
        is_open: Optional[bool] = Query(None, alias="open"),
        page: int = 1,
        limit: int = Query(10, lt=51),
    ):
        where_clause = [Project.doer == self.auth.user]
        if title:
            where_clause.append(
                Project.title.like("%" + title + "%"),
            )
        if is_open is not None:
            open_clause = (
                Status.title == ProjectStatusEnum.unassigned
                if is_open
                else Status.title != ProjectStatusEnum.unassigned
            )
            where_clause.append(open_clause)

        result = self.auth.session.exec(
            select(Project, Status)
            .where(*where_clause)
            .order_by(getattr(getattr(Project, sort.value), sort_dir.value)())
            .where(
                Project.id.in_(
                    select(Project.id)
                    .join(Status)
                    .where(*where_clause)
                    .order_by(getattr(getattr(Project, sort.value), sort_dir.value)())
                    .offset((page - 1) * limit)
                    .limit(limit)
                )
            )
        )
        projects = []
        current_project = None
        for res in result:
            pro = res[0]
            if current_project is None:
                current_project = ProjectList.from_orm(pro)
                current_project.technologies = []
                for t in pro.project_technologies:
                    current_project.technologies.append(t.technology)

                last_id = pro.id
                projects.append(current_project)

            elif pro.id != last_id:
                current_project = ProjectList.from_orm(pro)
                current_project.technologies = []
                for t in pro.project_technologies:
                    current_project.technologies.append(t.technology)
                projects.append(current_project)
                last_id = current_project.id

        return projects

    @authenticated_router.get(
        "/my/projects",
        response_model=List[ProjectList],
        response_model_exclude_none=True,
    )
    def list_my_projects(
        self,
        title: str | None = None,
        sort: SortEnum = SortEnum.date,
        sort_dir: SortDirEnum = SortDirEnum.descending,
        is_open: Optional[bool] = Query(None, alias="open"),
        page: int = 1,
        limit: int = Query(10, lt=51),
    ):
        where_clause = [Project.owner == self.auth.user]
        if title:
            where_clause.append(
                Project.title.like("%" + title + "%"),
            )
        if is_open is not None:
            open_clause = (
                Status.title == ProjectStatusEnum.unassigned
                if is_open
                else Status.title != ProjectStatusEnum.unassigned
            )
            where_clause.append(open_clause)

        result = self.auth.session.exec(
            select(Project, Status)
            .where(*where_clause)
            .order_by(getattr(getattr(Project, sort.value), sort_dir.value)())
            .where(
                Project.id.in_(
                    select(Project.id)
                    .join(Status)
                    .where(*where_clause)
                    .order_by(getattr(getattr(Project, sort.value), sort_dir.value)())
                    .offset((page - 1) * limit)
                    .limit(limit)
                )
            )
        )
        projects = []
        current_project = None
        for res in result:
            pro = res[0]
            if current_project is None:
                current_project = ProjectList.from_orm(pro)
                current_project.technologies = []
                for t in pro.project_technologies:
                    current_project.technologies.append(t.technology)

                last_id = pro.id
                projects.append(current_project)

            elif pro.id != last_id:
                current_project = ProjectList.from_orm(pro)
                current_project.technologies = []
                for t in pro.project_technologies:
                    current_project.technologies.append(t.technology)
                projects.append(current_project)
                last_id = current_project.id

        return projects

    @authenticated_router.get(
        "/project/me",
        response_model=List[ProjectList],
        summary="list projects with my skill",
        response_model_exclude_none=True,
    )
    def list_projects_me(
        self,
        title: str | None = None,
        sort: SortEnum = SortEnum.date,
        sort_dir: SortDirEnum = SortDirEnum.descending,
        min_price: Optional[int] = 0,
        max_price: Optional[int] = None,
        is_open: Optional[bool] = Query(None, alias="open"),
        page: int = 1,
        limit: int = Query(10, lt=51),
    ):
        select_clause = [Project, Status]
        where_clause = [
            Project.status_id == Status.id,
            Project.price_to >= min_price,
        ]
        techs = self.auth.session.exec(
            select(UserTechnology).where(UserTechnology.user == self.auth.user)
        ).all()
        where_clause.append(
            Technology.id.in_(map(lambda t: t.technology_id, techs)),
        )
        second_where_clause = [
            Project.price_to >= min_price,
        ]
        if max_price:
            where_clause.append(
                Project.price_to <= max_price,
            )
            second_where_clause.append(
                Project.price_to <= max_price,
            )
        if is_open is not None:
            open_clause = (
                Status.title == ProjectStatusEnum.unassigned
                if is_open
                else Status.title != ProjectStatusEnum.unassigned
            )
            where_clause.append(open_clause)
            second_where_clause.append(open_clause)

        if techs:
            where_clause += [
                Project.id == ProjectTechnology.project_id,
                Technology.id == ProjectTechnology.technology_id,
                Technology.slug.in_(techs),
            ]
            select_clause += [ProjectTechnology, Technology]

        if title:
            where_clause.append(
                Project.title.like("%" + title + "%"),
            )
            second_where_clause.append(
                Project.title.like("%" + title + "%"),
            )

        result = self.auth.session.exec(
            select(*select_clause)
            .where(*where_clause)
            .order_by(getattr(getattr(Project, sort.value), sort_dir.value)())
            .where(
                Project.id.in_(
                    select(Project.id)
                    .join(Status)
                    .where(*second_where_clause)
                    .order_by(getattr(getattr(Project, sort.value), sort_dir.value)())
                    .offset((page - 1) * limit)
                    .limit(limit)
                )
            )
        )
        projects = []
        current_project = None
        for res in result:
            pro = res[0]
            if current_project is None:
                current_project = ProjectList.from_orm(pro)
                current_project.technologies = []
                for t in pro.project_technologies:
                    current_project.technologies.append(t.technology)

                last_id = pro.id
                projects.append(current_project)

            elif pro.id != last_id:
                current_project = ProjectList.from_orm(pro)
                current_project.technologies = []
                for t in pro.project_technologies:
                    current_project.technologies.append(t.technology)
                projects.append(current_project)
                last_id = current_project.id

        return projects

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

    @authenticated_router.post(
        "/follow",
        response_model=UserShortOut,
    )
    def add_followings(self, user_id: int):
        try:
            if user_id == self.auth.user.id:
                raise permission_exception

            follow = Follower(follower=self.auth.user, following_id=user_id)
            self.auth.session.add(follow)
            self.auth.session.commit()
            self.auth.session.refresh(follow)
            return follow.following
        except IntegrityError:
            raise not_found_exception

    @authenticated_router.delete(
        "/follow",
        response_model=UserShortOut,
    )
    def remove_followings(self, user_id: int):
        try:
            follow = self.auth.session.exec(
                select(Follower).where(
                    Follower.follower == self.auth.user,
                    Follower.following_id == user_id,
                )
            ).first()
            if follow:
                self.auth.session.delete(follow)
                self.auth.session.commit()
                return JSONResponse(status_code=200, content={})
            else:
                raise not_found_exception
        except IntegrityError:
            raise permission_exception

    @authenticated_router.get(
        "/followings",
        response_model=List[UserShortOut],
    )
    def list_followings(self):
        result = self.auth.session.exec(
            select(Follower, User).where(
                Follower.following_id == User.id, Follower.follower == self.auth.user
            )
        )
        followings = []
        for _, user in result:
            followings.append(user)

        return followings

    @authenticated_router.get(
        "/followers",
        response_model=List[UserShortOut],
    )
    def list_followers(self):
        result = self.auth.session.exec(
            select(Follower, User).where(
                Follower.follower_id == User.id, Follower.following == self.auth.user
            )
        )
        followings = []
        for _, user in result:
            followings.append(user)

        return followings

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
                if tech is None:
                    raise IntegrityError("", "", "")
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

    @authenticated_router.post("/project/offer", status_code=201)
    def create_offer(self, offer_in: OfferCreate):
        if self.auth.user.offer_left > 0 or not self.auth.user.is_verified:
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

    @authenticated_router.get("/technology", response_model=List[TechnologyOut])
    def find_technology(self, title: str):
        technologies = self.auth.session.exec(
            select(Technology).where(
                Technology.title.like("%" + title + "%"),
            )
        ).all()
        return technologies

    @authenticated_router.post("/project/done")
    def make_project_done(self, project_id: int):
        project = self.auth.session.get(Project, project_id)
        if (
            project
            and project.owner == self.auth.user
            and project.status.title == ProjectStatusEnum.assigned
        ):
            try:
                done_status = self.auth.session.exec(
                    select(Status).where(Status.title == ProjectStatusEnum.done)
                ).first()
                project.status = done_status
                self.auth.session.add(project)
                self.auth.session.commit()
                return JSONResponse(status_code=200, content={})
            except IntegrityError:
                raise permission_exception
        else:
            raise permission_exception

    @authenticated_router.post("/project/assign", response_model=PickDoer)
    def assign_project(self, project_id: int, doer_id: int):
        project = self.auth.session.get(Project, project_id)
        if (
            project
            and project.owner == self.auth.user
            and project.status.title == ProjectStatusEnum.unassigned
            and doer_id != self.auth.user.id
        ):
            try:
                assigned_status = self.auth.session.exec(
                    select(Status).where(Status.title == ProjectStatusEnum.assigned)
                ).first()
                project.doer_id = doer_id
                project.status = assigned_status
                self.auth.session.add(project)
                self.auth.session.commit()
                self.auth.session.refresh(project)
                return PickDoer(doer=project.doer)
            except IntegrityError:
                raise permission_exception
        else:
            raise permission_exception

    @authenticated_router.post("/project/comment", status_code=201)
    def create_comment(self, comment_in: CommentIn):
        project = self.auth.session.get(Project, comment_in.project_id)
        if project is None:
            raise not_found_exception
        to_user = self.auth.session.get(User, comment_in.to_user_id)
        if to_user is None:
            raise not_found_exception
        if (
            self.auth.user == project.doer or self.auth.user == project.owner
        ) and self.auth.user != to_user:
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

    @authenticated_router.get("/chat/inbox", response_model=List[Message])
    def get_messages_list(self):
        query = f"""
            SELECT m.*
            FROM message m
            WHERE m.created_at = (SELECT MAX(m2.created_at)
                FROM message m2
                WHERE (m2.from_user_id = m.from_user_id AND m2.to_user_id = m.to_user_id) OR
                        (m2.from_user_id = m.to_user_id AND m2.to_user_id = m.from_user_id) 
                ) AND (m.from_user_id = {self.auth.user.id} OR m.to_user_id = {self.auth.user.id})
            ORDER BY m.created_at DESC
        """
        result = self.auth.session.exec(query).all()
        return result

    @authenticated_router.get("/chat", response_model=List[Message])
    def get_user_message(self, user_id: int, page: int = 1, limit: int = 10):
        self.auth.session.exec(
            update(Message)
            .where(Message.from_user_id == user_id, Message.to_user == self.auth.user)
            .values(is_read=True),
        )
        self.auth.session.commit()
        result = self.auth.session.exec(
            select(Message)
            .where(
                or_(
                    and_(
                        Message.from_user == self.auth.user,
                        Message.to_user_id == user_id,
                    ),
                    and_(
                        Message.to_user == self.auth.user,
                        Message.from_user_id == user_id,
                    ),
                )
            )
            .order_by(Message.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
        result.reverse()
        return result

    @authenticated_router.websocket("/chat/ws")
    async def chat_manger(self, websocket: WebSocket):
        try:
            await connection_manager.connect(self.auth.user.id, websocket)
            while True:
                message_block = await websocket.receive_json()
                await connection_manager.send_personal_message(self.auth, message_block)
        except WebSocketDisconnect:
            connection_manager.disconnect(self.auth.user)

    @authenticated_router.post("/user/picture")
    async def upload_profile_picture(self, file: UploadFile):
        if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
            raise permission_exception
        with open(
            settings.BASE_DIR / settings.DATA_PATH / f"{self.auth.user.id}.profile.jpg",
            "wb",
        ) as f:
            f.write(await file.read())
        return JSONResponse(status_code=200, content={})

    @authenticated_router.get(
        "/user/picture",
    )
    def get_profile_pictures(self, user_id: int):
        image_path = settings.BASE_DIR / settings.DATA_PATH / f"{user_id}.profile.jpg"
        if os.path.exists(image_path):
            return FileResponse(image_path)
        else:
            raise not_found_exception

    @authenticated_router.delete("/user/picture", response_class=FileResponse)
    def delete_profile_picture(self):
        image_path = (
            settings.BASE_DIR / settings.DATA_PATH / f"{self.auth.user.id}.profile.jpg"
        )
        if os.path.exists(image_path):
            os.remove(image_path)
            return JSONResponse(status_code=200, content={})
        else:
            raise not_found_exception


@cbv(admin_router)
class AuthenticatedRouter:
    auth: Auth = Depends(authenticate_admin)

    @admin_router.post("/technology", response_model=TechnologyOut, status_code=201)
    def create_technology(self, technology_in: TechnologyCreate):
        try:
            technology = Technology.from_orm(technology_in)
            technology.slug = slugify(technology.title)
            self.auth.session.add(technology)
            self.auth.session.commit()
            return technology
        except IntegrityError:
            raise conflict_exception

    @admin_router.put("/technology", response_model=TechnologyOut)
    def update_technology(self, tech_id: int, title: str = Body(embed=True)):
        technology = self.auth.session.get(Technology, tech_id)
        if technology:
            technology.title = title
            technology.slug = slugify(title)
            self.auth.session.add(technology)
            self.auth.session.commit()
            return technology
        else:
            raise not_found_exception

    @admin_router.delete("/technology", response_model=TechnologyOut)
    def delete_technology(self, tech_id: int):
        technology = self.auth.session.get(Technology, tech_id)
        if technology:
            self.auth.session.delete(technology)
            self.auth.session.commit()
            return technology
        else:
            raise not_found_exception

    @admin_router.delete("/plan", response_model=Plan)
    def delete_plan(self, plan_id: int):
        plan = self.auth.session.get(Plan, plan_id)
        if plan:
            self.auth.session.delete(plan)
            self.auth.session.commit()
            return plan
        else:
            raise not_found_exception

    @admin_router.post("/plan", response_model=Plan, status_code=201)
    def create_plan(self, plan_in: PlanCreate):
        try:
            plan = Plan.from_orm(plan_in)
            self.auth.session.add(plan)
            self.auth.session.commit()
            return plan
        except IntegrityError:
            raise conflict_exception

    @admin_router.put("/plan", response_model=Plan)
    def update_plan(self, plan_update: PlanUpdate):
        plan = self.auth.session.get(Plan, plan_update.id)
        if plan:
            for key, value in plan_update.dict(exclude_unset=True).items():
                setattr(plan, key, value)

            self.auth.session.add(plan)
            self.auth.session.commit()
            return plan
        else:
            raise not_found_exception
