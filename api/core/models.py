from sqlmodel import SQLModel, Field, Relationship, Session
from pydantic import EmailStr
from pydantic import root_validator
from typing import Optional, List
from .types import RoleEnum, PlanEnum

from datetime import datetime, timedelta
import string
import secrets


class UserBase(SQLModel):
    email: EmailStr = Field(unique=True)


class UserLogin(UserBase):
    password: str


class UserCreate(UserLogin):
    role: RoleEnum


class UserTechnology(SQLModel, table=True):
    technology_id: Optional[int] = Field(
        default=None, foreign_key="technology.id", primary_key=True
    )
    technology: "Technology" = Relationship(back_populates="user_technologies")
    user_id: Optional[int] = Field(
        default=None, foreign_key="user.id", primary_key=True
    )
    user: "User" = Relationship(back_populates="user_technologies")


class UserShortOut(UserBase):
    id: Optional[int] = Field(default=None, primary_key=True)


class PickDoer(SQLModel):
    doer: UserShortOut


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    description: Optional[str] = None
    offer_left: int = Field(default=0, gt=-1)
    plan_id: Optional[int] = Field(default=None, foreign_key="plan.id")
    plan: Optional["Plan"] = Relationship()
    plan_expire_at: Optional[datetime] = None
    hashed_password: str = Field(default=None, max_length=32)
    role_id: Optional[int] = Field(foreign_key="role.id")
    role: Optional["Role"] = Relationship()
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    offers: List["Offer"] = Relationship(back_populates="offerer")
    is_verified: bool = False
    # projects: List["Project"] = Relationship(
    #     back_populates="owner",
    # )
    user_technologies: List["UserTechnology"] = Relationship(back_populates="user")
    reset_token: Optional["ResetPasswordToken"] = Relationship(
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}, back_populates="user"
    )
    verification_code: Optional["UserVerificationCode"] = Relationship(
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}, back_populates="user"
    )
    # doing_projects: List["Project"] = Relationship(
    #     back_populates="doer",
    # )
    # comments: List["Comment"] = Relationship(
    #     back_populates="user_from",
    #     sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    # )


class SampleProjectOut(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    link: Optional[str] = None


class SampleProject(SampleProjectOut, table=True):
    user_id: Optional[int] = Field(nullable=False, foreign_key="user.id")
    user: User = Relationship()


class EducationOut(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    institution_name: str
    major: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    in_progress: Optional[bool] = False

    @root_validator
    def validate_in_progress(cls, values):
        if values.get("finished_at") is None:
            values["in_progress"] = True
            return values
        else:
            if values.get("in_progress"):
                values["finished_at"] = None
            return values


class Education(EducationOut, table=True):
    user_id: Optional[int] = Field(nullable=False, foreign_key="user.id")
    user: User = Relationship()


class CommentOut(SQLModel):
    star: Optional[int] = Field(default=0, gt=-1, lt=6)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    from_user: UserShortOut
    message: str


class CommentIn(SQLModel):
    star: Optional[int] = Field(default=0, nullable=False, gt=-1, lt=6)
    to_user_id: int
    project_id: int
    message: str


class Comment(SQLModel, table=True):
    star: Optional[int] = Field(default=0, nullable=False, gt=-1, lt=6)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    project_id: Optional[int] = Field(primary_key=True, foreign_key="project.id")
    project: "Project" = Relationship()
    from_user_id: Optional[int] = Field(primary_key=True, foreign_key="user.id")
    to_user_id: Optional[int] = Field(nullable=False, foreign_key="user.id")
    from_user: "User" = Relationship(
        sa_relationship_kwargs=dict(foreign_keys="[Comment.from_user_id]"),
    )
    to_user: "User" = Relationship(
        # back_populates="comments",
        sa_relationship_kwargs=dict(foreign_keys="[Comment.to_user_id]"),
    )
    message: str


class ExperienceOut(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_name: str
    in_progress: Optional[bool] = False
    started_at: datetime
    finished_at: Optional[datetime] = None
    position: str

    @root_validator
    def validate_in_progress(cls, values):
        if values.get("finished_at") is None:
            values["in_progress"] = True
            return values
        else:
            if values.get("in_progress"):
                values["finished_at"] = None
            return values


class Experience(ExperienceOut, table=True):
    user_id: Optional[int] = Field(nullable=False, foreign_key="user.id")
    user: User = Relationship()


class TechnologyCreate(SQLModel):
    title: str = Field(unique=True)


class TechnologyOut(TechnologyCreate):
    id: int
    slug: Optional[str] = None


class Technology(TechnologyCreate, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_technologies: List["ProjectTechnology"] = Relationship(
        back_populates="technology"
    )
    user_technologies: List["UserTechnology"] = Relationship(
        back_populates="technology"
    )
    slug: Optional[str] = Field(index=True, max_length=30, nullable=False)


class UserOut(UserBase):
    id: int
    description: Optional[str] = None
    offer_left: int = Field(default=0, gt=-1)
    educations: List[EducationOut] = None
    experiences: List[ExperienceOut] = None
    sample_projects: List[SampleProjectOut] = None
    comments: List[CommentOut] = None
    technologies: List[TechnologyOut] = None
    star: Optional[int] = Field(default=0, nullable=False, gt=-1, lt=6)


class UserUpdate(SQLModel):
    description: Optional[str] = None
    educations: List[EducationOut] = None
    experiences: List[ExperienceOut] = None
    sample_projects: List[SampleProjectOut] = None
    technologies_id: List[int] = None


class PlanChange(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str


class Plan(PlanChange, table=True):
    users: List[User] = Relationship(back_populates="plan")
    duration_day: Optional[int] = None
    offer_number: int


class Role(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    users: List[User] = Relationship(back_populates="role")


class ProjectIn(SQLModel):
    title: str
    description: Optional[str] = None
    price_from: int = Field(gt=299999)
    price_to: int = Field(gt=300000)
    technologies_id: List[int] = None

    @root_validator()
    def validate_price_range(cls, values):
        if values.get("price_from") < values.get("price_to"):
            return values
        else:
            raise ValueError


class OfferCreate(SQLModel):
    project_id: int
    offer_price: int = Field(gt=299999)
    duration_day: int = Field(gt=-1)


class OfferOut(SQLModel):
    offer_price: int
    duration_day: int = Field(gt=-1)
    offerer: UserOut


class ProjectBase(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    price_from: int
    price_to: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expire_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(days=15)
    )
    finished_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    deadline_until: Optional[datetime] = None


class ProjectList(ProjectBase):
    technologies: List["TechnologyOut"] = None

class ProjectOut(ProjectBase):
    technologies: List["TechnologyOut"] = None
    offers: List[OfferOut] = None
    doer: Optional[UserShortOut] = None
    owner: Optional[UserShortOut] = None


class Project(ProjectBase, table=True):
    offers: List["Offer"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    owner_id: Optional[int] = Field(foreign_key="user.id", nullable=False)
    owner: Optional["User"] = Relationship(
        sa_relationship_kwargs=dict(foreign_keys="[Project.owner_id]")
    )
    doer_id: Optional[int] = Field(foreign_key="user.id")
    doer: Optional["User"] = Relationship(
        sa_relationship_kwargs=dict(foreign_keys="[Project.doer_id]")
    )
    project_technologies: List["ProjectTechnology"] = Relationship(
        back_populates="project"
    )


class ProjectTechnology(SQLModel, table=True):
    technology_id: Optional[int] = Field(
        default=None, foreign_key="technology.id", primary_key=True
    )
    technology: Technology = Relationship(back_populates="project_technologies")
    project_id: Optional[int] = Field(
        default=None, foreign_key="project.id", primary_key=True
    )
    project: Project = Relationship(back_populates="project_technologies")


class UserVerificationCode(SQLModel, table=True):
    code: str = Field(
        default_factory=lambda: "".join(
            secrets.choice(string.digits) for _ in range(6)
        ),
        primary_key=True,
    )
    user_id: Optional[int] = Field(foreign_key="user.id", nullable=False)
    user: Optional[User] = Relationship(back_populates="verification_code")
    expire_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(minutes=5), nullable=False
    )


class ResetPasswordToken(SQLModel, table=True):
    token: str = Field(default_factory=secrets.token_hex, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship(back_populates="reset_token")
    expire_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(minutes=5), nullable=False
    )


class Offer(SQLModel, table=True):
    offerer_id: Optional[int] = Field(foreign_key="user.id", primary_key=True)
    offerer: User = Relationship()
    project_id: Optional[int] = Field(foreign_key="project.id", primary_key=True)
    project: Project = Relationship(back_populates="offers")
    offer_price: int
    duration_day: int = Field(gt=-1)
