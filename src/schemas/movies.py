from datetime import date as date_
from datetime import timedelta
from typing import Literal, Annotated

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator


class MovieUpdateInputSchema(BaseModel):
    name: str = Field(default=None, max_length=255)
    date: date_ | None = None
    score: float | None = Field(default=None, ge=0, le=100)
    overview: str | None = None
    status: Literal["Released", "Post Production", "In Production"] | None = (
        None
    )
    budget: float | None = Field(default=None, ge=0)
    revenue: float | None = Field(default=None, ge=0)

    @field_validator("date")
    @classmethod
    def validate_date(cls, value):
        today = date_.today()
        if value is not None and value > today + timedelta(weeks=52):
            raise HTTPException(status_code=400, detail="Invalid input data.")
        return value


class MovieDetailInputSchema(MovieUpdateInputSchema):
    name: str = Field(max_length=255)
    date: Annotated[date_, Field(le=date_.today() + timedelta(weeks=52))]
    score: float = Field(ge=0, le=100)
    overview: str
    status: Literal["Released", "Post Production", "In Production"]
    budget: float = Field(ge=0)
    revenue: float = Field(ge=0)
    country: str = Field(min_length=2, max_length=3, pattern=r"^[A-Z]{2,3}$")
    genres: list[str]
    actors: list[str]
    languages: list[str]


class BaseDetailSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class CountryDetailSchema(BaseDetailSchema):
    code: str
    name: str | None


class GenreDetailSchema(BaseDetailSchema):
    pass


class ActorDetailSchema(BaseDetailSchema):
    pass


class LanguageDetailSchema(BaseDetailSchema):
    pass


class MovieDetailSchema(BaseDetailSchema):
    date: date_
    score: float
    overview: str
    status: Literal["Released", "Post Production", "In Production"]
    budget: float
    revenue: float
    country: CountryDetailSchema
    genres: list[GenreDetailSchema]
    actors: list[ActorDetailSchema]
    languages: list[LanguageDetailSchema]


class MovieListItemSchema(BaseModel):
    id: int
    name: str
    date: date_
    score: float
    overview: str

    model_config = {"from_attributes": True}


class MovieListResponseSchema(BaseModel):
    movies: list[MovieListItemSchema]
    prev_page: str | None
    next_page: str | None
    total_pages: int
    total_items: int
