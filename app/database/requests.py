from app.database.models import async_session
from app.database.models import User, ConsultationSlot, InterviewSlot
from app.database.models import EventSlot
from sqlalchemy import select, delete
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


async def set_fio(tg_id: int, surname: str, name: str, patronymic: str):
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


# Изменение телефона
async def set_phone_number(tg_id: int, phone: str) -> None:
    async with async_session() as session:
        stmt = update(User).where((User.tg_id == tg_id)
                                  .values(phone_number=phone))
        await session.execute(stmt)
        await session.commit()


async def set_city(tg_id: int, city: str) -> None:
    async with async_session() as session:
        stmt = update(User).where(User.tg_id == tg_id).values(city=city)
        await session.execute(stmt)
        await session.commit()


async def set_direction(tg_id: int, direction: str) -> None:
    async with async_session() as session:
        stmt = update(User).where((User.tg_id == tg_id)
                                  .values(direction=direction))
        await session.execute(stmt)
        await session.commit()


async def get_user_by_tg_id(tg_id: int) -> User | None:
    async with async_session() as session:
        return await session.scalar(select(User).where(User.tg_id == tg_id))


async def get_consultation_slots():
    async with async_session() as session:
        result = await session.execute(select(ConsultationSlot.id,
                                              ConsultationSlot.slot))
        return result.all()  # List[ (id, slot) ]


async def get_slot_by_id(slot_id: int) -> str | None:
    async with async_session() as session:
        row = await session.get(ConsultationSlot, slot_id)
        return row.slot if row else None


async def get_user_slot(tg_id: int) -> str | None:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        return user.consultation_slot


async def set_user_slot(tg_id: int, slot: str) -> None:
    async with async_session() as session:
        stmt = (
            update(User)
            .where(User.tg_id == tg_id)
            .values(consultation_slot=slot)
        )
        await session.execute(stmt)
        await session.commit()


async def clear_user_slot(tg_id: int) -> None:
    async with async_session() as session:
        stmt = (
            update(User)
            .where(User.tg_id == tg_id)
            .values(consultation_slot=None)
        )
        await session.execute(stmt)
        await session.commit()


async def get_users_by_slot(slot: str) -> list[User]:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.consultation_slot == slot)
        )
        return result.scalars().all()


async def add_consultation_slot(slot: str) -> None:
    async with async_session() as session:
        session.add(ConsultationSlot(slot=slot))
        await session.commit()


async def delete_consultation_slot(slot_id: int) -> None:
    async with async_session() as session:
        stmt = delete(ConsultationSlot).where(ConsultationSlot.id == slot_id)
        await session.execute(stmt)
        await session.commit()


async def get_interview_consultation_slots():
    async with async_session() as session:
        result = await session.execute(select(InterviewSlot.id,
                                              InterviewSlot.slot))
        return result.all()  # List[ (id, slot) ]


async def get_interview_slot_by_id(slot_id: int) -> str | None:
    async with async_session() as session:
        row = await session.get(InterviewSlot, slot_id)
        return row.slot if row else None


async def get_user_slot_interview(tg_id: int) -> str | None:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        return user.interview_slot


async def set_user_slot_interview(tg_id: int, slot: str) -> None:
    async with async_session() as session:
        stmt = (
            update(User)
            .where(User.tg_id == tg_id)
            .values(interview_slot=slot)
        )
        await session.execute(stmt)
        await session.commit()


async def clear_user_slot_interview(tg_id: int) -> None:
    async with async_session() as session:
        stmt = (
            update(User)
            .where(User.tg_id == tg_id)
            .values(interview_slot=None)
        )
        await session.execute(stmt)
        await session.commit()


async def get_users_by_slot_interview(slot: str) -> list[User]:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.interview_slot == slot)
        )
        return result.scalars().all()


async def add_interview_slot(slot: str) -> None:
    async with async_session() as session:
        session.add(InterviewSlot(slot=slot))
        await session.commit()


async def delete_interview_slot(slot_id: int) -> None:
    async with async_session() as session:
        stmt = delete(InterviewSlot).where(InterviewSlot.id == slot_id)
        await session.execute(stmt)
        await session.commit()


async def get_all_events() -> list[EventSlot]:
    async with async_session() as session:
        result = await session.execute(select(EventSlot.slot,
                                              EventSlot.content))
        return result.all()


async def get_event_by_date(date: str) -> EventSlot | None:
    async with async_session() as session:
        result = await session.execute(
            select(EventSlot).where(EventSlot.slot == date)
        )
        return result.scalar_one_or_none()


async def delete_event_by_date(date: str) -> None:
    async with async_session() as session:
        stmt = delete(EventSlot).where(EventSlot.slot == date)
        await session.execute(stmt)
        await session.commit()


async def add_event(date: str, content: str) -> None:
    async with async_session() as session:
        session.add(EventSlot(slot=date, content=content))
        await session.commit()


async def update_event_content_by_date(date: str, new_content: str) -> None:
    async with async_session() as session:
        stmt = (
            update(EventSlot)
            .where(EventSlot.slot == date)
            .values(content=new_content)
        )
        await session.execute(stmt)
        await session.commit()


async def update_event_date(old_date: str, new_date: str) -> None:
    async with async_session() as session:
        stmt = (
            update(EventSlot)
            .where(EventSlot.slot == old_date)
            .values(slot=new_date)
        )
        await session.execute(stmt)
        await session.commit()


async def get_all_users() -> list[User]:
    async with async_session() as session:
        result = await session.execute(select(User))
        return result.scalars().all()
