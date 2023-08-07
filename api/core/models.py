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
    # technology: Technology = Relationship()
    user_id: Optional[int] = Field(
        default=None, foreign_key="user.id", primary_key=True
    )
    # user: User = Relationship()


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: Optional[int] = Field(default=None, foreign_key="plan.id")
    plan: Optional["Plan"] = Relationship()
    hashed_password: str = Field(default=None, max_length=32)
    role_id: Optional[int] = Field(foreign_key="role.id")
    role: Optional["Role"] = Relationship()
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    offers: List["Offer"] = Relationship(back_populates="offerer")
    is_verified: bool = False
    # projects: List["Project"] = Relationship(
    #     back_populates="owner",
    # )
    technologies: List["Technology"] = Relationship(link_model=UserTechnology)
    reset_token: Optional["ResetPasswordToken"] = Relationship(
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}, back_populates="user"
    )
    verification_code: Optional["UserVerificationCode"] = Relationship(
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}, back_populates="user"
    )
    # doing_projects: List["Project"] = Relationship(
    #     back_populates="doer",
    # )


class UserOut(UserBase):
    id: int


class PlanChange(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str


class Plan(PlanChange, table=True):
    users: List[User] = Relationship(back_populates="plan")


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
    duration_day: int = Field(gt=0)


class OfferOut(SQLModel):
    offer_price: int
    duration_day: int = Field(gt=0)
    offerer: UserOut


class TechnologyCreate(SQLModel):
    title: str = Field(unique=True)


class Technology(TechnologyCreate, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


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


class ProjectOut(ProjectBase):
    technologies: List["Technology"] = None
    offers: List[OfferOut] = None


class Model(SQLModel):
    a: str


class Model2(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    b: List[Model]


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
    # technologies: List['Technology'] = Relationship(link_model='ProjectTechnology')


class ProjectTechnology(SQLModel, table=True):
    technology_id: Optional[int] = Field(
        default=None, foreign_key="technology.id", primary_key=True
    )
    technology: Technology = Relationship()
    project_id: Optional[int] = Field(
        default=None, foreign_key="project.id", primary_key=True
    )
    project: Project = Relationship()


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
    duration_day: int = Field(gt=0)
