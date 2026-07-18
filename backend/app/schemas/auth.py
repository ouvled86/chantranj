import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterIn(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not (re.search(r"[a-zA-Z]", v) and re.search(r"\d", v)):
            raise ValueError("password must contain at least one letter and one digit")
        return v


class LoginIn(BaseModel):
    identifier: str = Field(description="email or username")
    password: str
