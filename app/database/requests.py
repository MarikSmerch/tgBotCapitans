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


async def set_fio(tg_id: int, surname: str, name: str, patronymic: str) -> None:
    async with async_session() as session:
        stmt = (
            update(User)
            .where(User.tg_id == tg_id)
            .values(surname=surname, name=name, patronymic=patronymic)
        )
        await session.execute(stmt)
        await session.commit()


# Изменение года поступления
async def set_entry_year(tg_id: int, year: int) -> None:
    async with async_session() as session:
        stmt = update(User).where(User.tg_id == tg_id).values(entry_year=year)
        await session.execute(stmt)
        await session.commit()


# Изменение ссылки
async def set_contact_url(tg_id: int, url: str) -> None:
    async with async_session() as session:
        stmt = update(User).where(User.tg_id == tg_id).values(contact_url=url)
        await session.execute(stmt)
        await session.commit()


# Изменение телефона
async def set_phone_number(tg_id: int, phone: str) -> None:
    async with async_session() as session:
        stmt = update(User).where(User.tg_id == tg_id).values(phone_number=phone)
        await session.execute(stmt)
        await session.commit()


async def get_user_by_tg_id(tg_id: int) -> User | None:
    async with async_session() as session:
        return await session.scalar(select(User).where(User.tg_id == tg_id))