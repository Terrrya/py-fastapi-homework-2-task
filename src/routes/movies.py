import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from pydantic import ValidationError
from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, load_only

from database import (
    get_db,
    MovieModel,
    GenreModel,
    ActorModel,
    LanguageModel,
    crud,
)
from schemas import (
    MovieListResponseSchema,
    MovieDetailSchema,
    MovieDetailInputSchema,
    MovieUpdateInputSchema,
)

router = APIRouter()


@router.get("/movies/", response_model=MovieListResponseSchema)
async def get_all_movies(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=20)] = 10,
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page

    result = await db.execute(
        select(MovieModel)
        .options(
            load_only(
                MovieModel.id,
                MovieModel.name,
                MovieModel.date,
                MovieModel.score,
                MovieModel.overview,
            )
        )
        .order_by(*MovieModel.default_order_by())
        .limit(per_page)
        .offset(offset)
    )
    movies = result.scalars().all()

    if movies:
        total_result = await db.execute(
            select(func.count()).select_from(MovieModel)
        )
        total_items = total_result.scalar()
        total_pages = math.ceil(total_items / per_page)

        url_page = "/theater/movies/?page={}&per_page={}"
        prev_page = url_page.format(page - 1, per_page) if page > 1 else None
        next_page = (
            url_page.format(page + 1, per_page)
            if (page + 1) * per_page < total_items
            else None
        )

        return {
            "movies": movies,
            "total_items": total_items,
            "total_pages": total_pages,
            "next_page": next_page,
            "prev_page": prev_page,
        }

    raise HTTPException(status_code=404, detail="No movies found.")


@router.post(
    "/movies/",
    response_model=MovieDetailSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_movie(
    body_data: Annotated[dict, Body()],
    db: AsyncSession = Depends(get_db),
):
    try:
        movie_data = MovieDetailInputSchema(**body_data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail="Invalid input data.")

    genres = await crud.get_or_create_by_name(
        movie_data.genres, GenreModel, db
    )
    actors = await crud.get_or_create_by_name(
        movie_data.actors, ActorModel, db
    )
    languages = await crud.get_or_create_by_name(
        movie_data.languages, LanguageModel, db
    )
    country = await crud.get_or_create_country(movie_data.country, db)

    movie = MovieModel(
        **movie_data.model_dump(
            exclude={"genres", "actors", "languages", "country"}
        ),
        genres=genres,
        country=country,
        actors=actors,
        languages=languages,
    )
    db.add(movie)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"A movie with the name '{movie_data.name}' and release date '{movie_data.date}' already exists.",
        )

    await db.refresh(
        movie, attribute_names=["genres", "actors", "languages", "country"]
    )

    return movie


@router.get("/movies/{movie_id}/", response_model=MovieDetailSchema)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MovieModel)
        .options(
            joinedload(MovieModel.genres),
            joinedload(MovieModel.actors),
            joinedload(MovieModel.country),
            joinedload(MovieModel.languages),
        )
        .where(MovieModel.id == movie_id)
    )
    movie = result.scalars().first()

    if movie:
        return movie

    raise HTTPException(
        status_code=404, detail="Movie with the given ID was not found."
    )


@router.delete("/movies/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MovieModel).where(MovieModel.id == movie_id)
    )
    db_movie = result.scalars().first()

    if db_movie:
        await db.delete(db_movie)
        await db.commit()
        return

    raise HTTPException(
        status_code=404, detail="Movie with the given ID was not found."
    )


@router.patch("/movies/{movie_id}/")
async def update_movie(
    movie_id: int,
    body_data: Annotated[dict, Body()],
    db: AsyncSession = Depends(get_db),
):
    try:
        MovieUpdateInputSchema(**body_data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail="Invalid input data.")

    result = await db.execute(
        update(MovieModel).where(MovieModel.id == movie_id).values(**body_data)
    )
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=404, detail="Movie with the given ID was not found."
        )

    return {"detail": "Movie updated successfully."}
