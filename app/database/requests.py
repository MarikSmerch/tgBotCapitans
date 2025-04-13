from app.database.models import async_session
from app.database.models import User
from sqlalchemy import select
from sqlalchemy.sql import update


# Добавление пользователя в бд
async def set_user(tg_id: int) -> None:
    async with async_session() as session:
        try:
            user = await session.scalar(select(User)
                                        .where(User.tg_id == tg_id))

            if not user:
                session.add(User(tg_id=tg_id))
                await session.commit()
        except Exception as e:
            await session.rollback()
            raise e


# Добавление ссылки вк в бд
async def set_link(tg_id: int, vk_link: str) -> None:
    async with async_session() as session:
        vk_link_update = (update(User)
                          .values(vk_link=vk_link)
                          .where(User.tg_id == tg_id))
        await session.execute(vk_link_update)
        await session.commit()
