from pydantic import BaseModel, HttpUrl, Field


class VerificationLink(BaseModel):
    platform: str = Field(min_length=1)
    url: HttpUrl | str
