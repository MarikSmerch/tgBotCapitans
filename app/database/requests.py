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


async def change_subscribed(tg_id: int) -> int:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

        new_status = not user.is_subscribed

        change_sub = (
            update(User)
            .values(is_subscribed=new_status)
            .where(User.tg_id == tg_id)
        )

        await session.execute(change_sub)
        await session.commit()


async def get_subscribed(tg_id: int) -> int:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        return user.is_subscribed


async def get_all_subscribed_users():
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.is_subscribed)
        )
        return result.scalars().all()
