from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str
    name: str
    temp_password: str | None = None


class UserOut(BaseModel):
    id: str
    email: str
    name: str
