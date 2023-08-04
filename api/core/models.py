from sqlmodel import SQLModel, Field, Relationship, Session
from pydantic import EmailStr
from typing import Optional, List
from .types import RoleEnum, PlanEnum


class UserBase(SQLModel):
    email: EmailStr


class UserLogin(UserBase):
    password: str


class UserCreate(UserLogin):
    role: RoleEnum


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="plan.id")
    plan: "Plan" = Relationship()
    hashed_password: str = Field(max_length=32)
    role_id: int = Field(foreign_key="role.id")
    role: "Role" = Relationship()


class UserOut(UserBase):
    id: int


class Plan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: PlanEnum


class Role(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: RoleEnum
    # users: List['User'] = Relationship(back_populates='role')
