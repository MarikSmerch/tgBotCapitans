from sqlalchemy import BigInteger, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine


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
    vk_url: Mapped[str] = mapped_column(String, nullable=True)


async def async_mainbd():
    async with engin.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
