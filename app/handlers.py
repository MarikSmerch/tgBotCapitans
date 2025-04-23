from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram.filters import CommandStart, Command
import app.database.requests as rq

from aiogram.fsm.context import FSMContext
from app.states.registration import FSMRegistration

import re

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
    user_p = await rq.get_user_by_tg_id(user.id)

    if user_p.phone_number != "-":
        hidden_phone = user_p.phone_number[:-4] + "XXXX"
    else:
        hidden_phone = user_p.phone_number

    profile_text = (
        f"👤 <b>Профиль</b>\n"
        f"Имя: {user_p.surname} {user_p.name} {user_p.patronymic}\n"
        f"Год поступления: {user_p.entry_year}\n"
        f"Номер телефона: {hidden_phone}\n"
        f"Ссылка на вк: {user_p.contact_url}\n"
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
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id

    await rq.set_user(user_id)
    user = await rq.get_user_by_tg_id(user_id)

    if not (user.surname and user.name and user.patronymic and user.entry_year and user.phone_number and user.contact_url):
        await state.set_state(FSMRegistration.full_name)
        await message.answer("Добро пожаловать!\n\nВведите Ваше <b>ФИО</b> через пробел:", parse_mode="HTML")
    else:
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


@router.message(FSMRegistration.full_name)
async def reg_full_name(message: Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) != 3:
        await message.answer(
            "⚠️ Пожалуйста, введи ФИО целиком через пробел, например:\n"
            "Иванов Иван Иванович"
        )
        return

    surname, name, patronymic = parts
    await state.update_data(surname=surname, name=name, patronymic=patronymic)
    await state.set_state(FSMRegistration.entry_year)

    # сразу предлагаем выбрать год
    await message.answer(
        "Выберите <b>год поступления</b>:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="2023", callback_data="year_2023")],
                [InlineKeyboardButton(text="2024", callback_data="year_2024")],
                [InlineKeyboardButton(text="2025", callback_data="year_2025")]
            ]
        )
    )


@router.callback_query(F.data.startswith("year_"), FSMRegistration.entry_year)
async def reg_entry_year(callback: CallbackQuery, state: FSMContext):
    year = int(callback.data.split("_")[1])
    await state.update_data(entry_year=year)
    await state.set_state(FSMRegistration.phone)
    await callback.message.edit_text("Введите ваш <b>номер телефона</b> в формате +7XXXXXXXXXX:", parse_mode="HTML")
    await callback.answer()


@router.message(FSMRegistration.phone)
async def reg_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not re.fullmatch(r"\+7\d{3}\d{3}\d{2}\d{2}", phone) and phone != "-":
        await message.answer("⚠️ Неверный формат. Попробуйте ещё раз: +7XXXXXXXXXX\nИли укажите -")
        return
    await state.update_data(phone=phone)
    await state.set_state(FSMRegistration.social_link)
    await message.answer("Укажите ссылку на вк:")


@router.message(FSMRegistration.social_link)
async def reg_social(message: Message, state: FSMContext):
    link = message.text.strip()
    if not link.startswith("http") and link != "-":
        await message.answer("⚠️ Ссылка должна начинаться с http\nИли укажите -")
        return

    await state.update_data(contact_url=link)
    data = await state.get_data()
    await rq.set_fio(message.from_user.id, data["surname"], data["name"], data["patronymic"])
    await rq.set_entry_year(message.from_user.id, data["entry_year"])
    await rq.set_phone_number(message.from_user.id, data["phone"])
    await rq.set_contact_url(message.from_user.id, data["contact_url"])
    await state.clear()

    await message.answer("✅ Регистрация завершена!")
    await send_main_menu(message)
