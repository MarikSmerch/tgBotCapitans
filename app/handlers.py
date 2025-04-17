from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
import app.database.requests as rq

router = Router()


# Отрисовка главного меню
async def send_main_menu(send_func):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Профиль", callback_data="show_profile")],
            [InlineKeyboardButton(text="О Капитанах", callback_data="about_captains")],
            [InlineKeyboardButton(text="Особенности", callback_data="features")],
            [InlineKeyboardButton(text="Собеседование", callback_data="interview")],
            [InlineKeyboardButton(text="Мероприятия", callback_data="events")]
        ]
    )
    await send_func("Добро пожаловать!", reply_markup=keyboard)


# Отрисовка профиля с кнопкой подписки
async def send_profile_menu(send_func, user):
    subscribed = bool(await rq.get_subscribed(user.id))

    profile_text = (
        f"👤 <b>Профиль</b>\n"
        f"Имя: {user.full_name}\n"
        f"ID: <code>{user.id}</code>\n"
        f"Юзернейм: @{user.username or '—'}"
    )

    sub_text = "📩 Отписаться" if subscribed else "📴 Подписаться"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Главное меню", callback_data="main_menu"),
                InlineKeyboardButton(text=sub_text, callback_data="toggle_subscription")
            ]
        ]
    )

    await send_func(profile_text, parse_mode="HTML", reply_markup=keyboard)


# Отрисовка информации о Капитанах
async def send_about_captains(send_func):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Главное меню", callback_data="main_menu")]
        ]
    )
    await send_func("Здесь будет информация!", reply_markup=keyboard)


# Отрисовка особенностей
async def send_features(send_func):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Главное меню", callback_data="main_menu")]
        ]
    )
    await send_func("Особенности:)", reply_markup=keyboard)


# Отрисовка информации о собеседованиях
async def send_interview(send_func):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Главное меню", callback_data="main_menu")]
        ]
    )
    await send_func("Собеседование", reply_markup=keyboard)


# Отрисовка информации о мероприятиях
async def send_events(send_func):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Главное меню", callback_data="main_menu")]
        ]
    )
    await send_func("Мероприятие: сдача бумаги", reply_markup=keyboard)


# /start
@router.message(CommandStart())
async def cmd_start(message: Message):
    await rq.set_user(message.from_user.id)
    await send_main_menu(message.answer)


# кнопка Главное меню
@router.callback_query(F.data == "main_menu")
async def cb_main(callback: CallbackQuery):
    await rq.set_user(callback.from_user.id)
    await send_main_menu(callback.message.edit_text)
    await callback.answer()


# кнопка Профиль
@router.callback_query(F.data == "show_profile")
async def cb_show_profile(callback: CallbackQuery):
    await send_profile_menu(callback.message.edit_text, callback.from_user)
    await callback.answer()


# кнопка Вкл/Выкл рассылку
@router.callback_query(F.data == "toggle_subscription")
async def cb_toggle(callback: CallbackQuery):
    user_id = callback.from_user.id
    # меняем статус в БД
    await rq.change_subscribed(user_id)
    # и сразу рендерим профиль по-новой
    await send_profile_menu(callback.message.edit_text, callback.from_user)
    # небольшой ответ для убирания часов
    await callback.answer("Статус обновлён", show_alert=False)


# кнопка О Капитанах
@router.callback_query(F.data == "about_captains")
async def cb_captains(callback: CallbackQuery):
    await send_about_captains(callback.message.edit_text)
    await callback.answer()


# кнопка Особенности
@router.callback_query(F.data == "features")
async def cb_features(callback: CallbackQuery):
    await send_features(callback.message.edit_text)
    await callback.answer()


# кнопка Собеседование
@router.callback_query(F.data == "interview")
async def cb_interview(callback: CallbackQuery):
    await send_interview(callback.message.edit_text)
    await callback.answer()


# кнопка Мероприятия
@router.callback_query(F.data == "events")
async def cb_events(callback: CallbackQuery):
    await send_events(callback.message.edit_text)
    await callback.answer()
