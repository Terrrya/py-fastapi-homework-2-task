from typing import Type

import pycountry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import CountryModel, ActorModel, LanguageModel, GenreModel

AllowedModels = ActorModel | LanguageModel | GenreModel


async def get_or_create_by_name(
    names: list[str],
    model: Type[AllowedModels],
    db: AsyncSession,
) -> list[AllowedModels]:
    result = await db.execute(select(model).where(model.name.in_(names)))
    existing_objs = result.scalars().all()
    objs = list(existing_objs)

    existing_names = {obj.name for obj in existing_objs}
    missing_names = [name for name in names if name not in existing_names]

    if missing_names:
        new_objs = [model(name=name) for name in missing_names]
        db.add_all(new_objs)
        objs.extend(new_objs)
        await db.flush()

    return objs


async def get_or_create_country(
    code: str, db: AsyncSession, name: str | None = None
) -> CountryModel:
    result = await db.execute(
        select(CountryModel).where(CountryModel.code == code)
    )
    obj = result.scalars().first()

    if obj is None:
        country = pycountry.countries.get(alpha_3=code.upper())
        name = name or country.name if country else None
        obj = CountryModel(name=name, code=code)
        db.add(obj)
        await db.flush()

    return obj
