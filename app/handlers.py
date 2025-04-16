from aiogram import F, Router
from aiogram.filters import CommandStart, Command, and_f, or_f
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

import app.database.requests as rq

router = Router()


async def send_main_menu(send_func):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Профиль", callback_data="show_profile")]
        ]
    )
    await send_func("Добро пожаловать!", reply_markup=keyboard)


# 🟩 Обработка команды /start
@router.message(CommandStart())
async def main_menu_message(message: Message):
    await rq.set_user(message.from_user.id)
    await send_main_menu(message.answer)


# 🟦 Обработка кнопки "Главное меню"
@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery):
    await rq.set_user(callback.from_user.id)
    await send_main_menu(callback.message.edit_text)
    await callback.answer()


# 👤 Обработка кнопки "Профиль"
@router.callback_query(F.data == "show_profile")
async def show_profile(callback: CallbackQuery):
    user = callback.from_user

    profile_text = (
        f"👤 <b>Профиль</b>\n"
        f"Имя: {user.full_name}\n"
        f"ID: <code>{user.id}</code>\n"
        f"Юзернейм: @{user.username}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Главное меню", callback_data="main_menu"),
             InlineKeyboardButton(text="Рассылка", callback_data="toggle_subscription")]
        ]
    )

    await callback.message.edit_text(profile_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "toggle_subscription")
async def toggle_subscription(callback: CallbackQuery):
    user = callback.from_user
    result = await rq.get_subscribed(user.id)

    text = "📩 Подписка включена" if result else "📴 Подписка отключена"
    await callback.answer(text, show_alert=False)

    # Обновим профиль после изменения
    profile_text = (
        f"👤 <b>Профиль</b>\n"
        f"Имя: {user.full_name}\n"
        f"ID: <code>{user.id}</code>\n"
        f"Юзернейм: @{user.username}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Главное меню", callback_data="main_menu"),
                InlineKeyboardButton(text="Рассылка", callback_data="toggle_subscription")
            ]
        ]
    )

    await callback.message.edit_text(profile_text, parse_mode="HTML", reply_markup=keyboard)