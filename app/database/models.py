from sqlalchemy import BigInteger, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine


# Создание движка и сессии
engin = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3')
async_session = async_sessionmaker(engin)


# Базовый класс моделей
class Base(AsyncAttrs, DeclarativeBase):
    pass


# Модель пользователя
class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    is_subscribed: Mapped[bool] = mapped_column(default=True,
                                                server_default="1")
    surname: Mapped[str] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=True)
    patronymic: Mapped[str] = mapped_column(String, nullable=True)
    entry_year: Mapped[int] = mapped_column(nullable=True)
    phone_number: Mapped[str] = mapped_column(String, nullable=True)
    city: Mapped[str] = mapped_column(String, nullable=True)
    direction: Mapped[str] = mapped_column(String, nullable=True)
    consultation_slot: Mapped[str] = mapped_column(String, nullable=True)
    interview_slot: Mapped[str] = mapped_column(String, nullable=True)


# Модель дат для консультации
class ConsultationSlot(Base):
    __tablename__ = 'consultation_slots'

    id: Mapped[int] = mapped_column(primary_key=True)
    slot: Mapped[str] = mapped_column(String, unique=True)


# Модель дат для собеседования
class InterviewSlot(Base):
    __tablename__ = 'interview_slots'

    id: Mapped[int] = mapped_column(primary_key=True)
    slot: Mapped[str] = mapped_column(String, unique=True)


class EventSlot(Base):
    __tablename__ = 'event_slot'

    id: Mapped[int] = mapped_column(primary_key=True)
    slot: Mapped[str] = mapped_column(String, unique=True)
    content: Mapped[str] = mapped_column(String)


async def async_mainbd():
    async with engin.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
