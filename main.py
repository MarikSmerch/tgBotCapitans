import os
from dotenv import load_dotenv
import asyncio
import logging
from aiogram import Bot, Dispatcher
from app.handlers import router
from app.database.models import async_mainbd
load_dotenv()


async def main():
    await async_mainbd()
    bot = Bot(token=os.getenv('TOKEN'))
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")
