from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram.filters import CommandStart, Command
import app.database.requests as rq

router = Router()


# Отрисовка главного меню
async def send_main_menu(message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Профиль", callback_data="show_profile")],
            [InlineKeyboardButton(text="О Капитанах", callback_data="about_captains")],
            [InlineKeyboardButton(text="Особенности", callback_data="features")],
            [InlineKeyboardButton(text="Собеседование", callback_data="interview")],
            [InlineKeyboardButton(text="Мероприятия", callback_data="events")]
        ]
    )
    caption = "Добро пожаловать!"
    await message.answer_photo(photo=FSInputFile("C:\\Users\\aramb\\projects\\tgBotCapitans\\app\\img\\cards.jpg"), caption=caption, reply_markup=keyboard)


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
                InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"),
                InlineKeyboardButton(text=sub_text, callback_data="toggle_subscription")
            ],
            [InlineKeyboardButton(text="Изменить данные", callback_data="edit_profile")]
        ]
    )

    await send_func(profile_text, parse_mode="HTML", reply_markup=keyboard)


# Отрисовка информации о Капитанах
async def send_about_captains(send_func):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
    )
    await send_func("Здесь будет информация!", reply_markup=keyboard)


# Отрисовка особенностей
async def send_features(send_func):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
    )
    await send_func("Особенности:)", reply_markup=keyboard)


# Отрисовка информации о собеседованиях
async def send_interview(send_func):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
    )
    await send_func("Собеседование", reply_markup=keyboard)


# Отрисовка информации о мероприятиях
async def send_events(send_func):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
    )
    await send_func("Мероприятие: сдача бумаги", reply_markup=keyboard)


# /start
@router.message(CommandStart())
async def cmd_start(message: Message):
    await rq.set_user(message.from_user.id)
    await send_main_menu(message)


# кнопка Главное меню
@router.callback_query(F.data == "main_menu")
async def cb_main(callback: CallbackQuery):
    await rq.set_user(callback.from_user.id)
    await callback.message.delete()
    await send_main_menu(callback.message)
    await callback.answer()


# кнопка Главное меню (из /send)
@router.callback_query(F.data == "main_menu_from_send")
async def cb_main_from_send(callback: CallbackQuery):
    await rq.set_user(callback.from_user.id)
    await send_main_menu(callback.message)
    await callback.answer()


# кнопка Профиль
@router.callback_query(F.data == "show_profile")
async def cb_show_profile(callback: CallbackQuery):
    await callback.message.delete()
    await send_profile_menu(callback.message.answer, callback.from_user)
    await callback.answer()


# кнопка Вкл/Выкл рассылку
@router.callback_query(F.data == "toggle_subscription")
async def cb_toggle(callback: CallbackQuery):
    user_id = callback.from_user.id
    await rq.change_subscribed(user_id)
    await send_profile_menu(callback.message.edit_text, callback.from_user)
    await callback.answer("Статус обновлён", show_alert=False)


# кнопка О Капитанах
@router.callback_query(F.data == "about_captains")
async def cb_captains(callback: CallbackQuery):
    await callback.message.delete()
    await send_about_captains(callback.message.answer)
    await callback.answer()


# кнопка Особенности
@router.callback_query(F.data == "features")
async def cb_features(callback: CallbackQuery):
    await callback.message.delete()
    await send_features(callback.message.answer)
    await callback.answer()


# кнопка Собеседование
@router.callback_query(F.data == "interview")
async def cb_interview(callback: CallbackQuery):
    await callback.message.delete()
    await send_interview(callback.message.answer)
    await callback.answer()


# кнопка Мероприятия
@router.callback_query(F.data == "events")
async def cb_events(callback: CallbackQuery):
    await callback.message.delete()
    await send_events(callback.message.answer)
    await callback.answer()


# команда /send
@router.message(Command("send"))
async def send_broadcast(message: Message):
    if message.from_user.id != 807480894:
        return await message.answer("🚫 У тебя нет прав использовать эту команду.")

    content = message.text.removeprefix("/send").strip()
    if not content:
        return await message.answer("⚠️ Укажи текст после команды /send")

    users = await rq.get_all_subscribed_users()

    success, failed = 0, 0

    user_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu_from_send")]
        ]
    )

    for user in users:
        try:
            await message.bot.send_message(user.tg_id, content, reply_markup=user_keyboard)
            success += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1

    await message.answer(
        f"📣 Рассылка завершена\n\n✅ Отправлено: {success}\n❌ Ошибок: {failed}"
    )
