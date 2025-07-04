from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.types import InlineKeyboardButton, FSInputFile
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram.filters import CommandStart, Command, StateFilter
import app.database.requests as rq
from functools import wraps

from aiogram.fsm.context import FSMContext
from app.states.registration import FSMRegistration

import pandas as pd
import os
from datetime import date

from datetime import datetime

import re

from app.configAdmin import is_admin

router = Router()

user_edit_mode = {}
user_prompt_message_id = {}
user_error_message_id = {}
admin_cons_mode = {}
admin_int_mode = {}
admin_event_mode = {}
admin_event_data = {}
DIRECTIONS = {
    "dir_1": "39.03.01 Социология управления и организаций",
    "dir_2": "38.03.01 Государственное и муниципальное управление",
    "dir_3": "42.03.01 Реклама и связи с общественностью",
    "dir_4": "38.03.06 Маркетинг и логистика в коммерции",
    "dir_5": "38.05.01 Экономико-правовое обеспечение "
    "экономической безопасности",
    "dir_6": "40.03.01 Юриспруденция",
    "dir_7": "40.05.01 Правовое обеспечение национальной безопасности",
    "dir_8": "41.03.06 Публичная политика и управление"
}
REFERRAL_SOURCES = {
    "source_1": "От волонтёра на отборочной комиссии",
    "source_2": "Из социальных сетей",
    "source_3": "От знакомых/друзей",
    "source_4": "Другое"
}


def admin_only(handler):
    @wraps(handler)
    async def wrapper(message: Message, *args, **kwargs):
        if not is_admin(message.from_user.id):
            await message.answer("⛔ Команда доступна только администраторам.")
            return
        return await handler(message, *args, **kwargs)
    return wrapper


def get_edit_profile_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ФИО",
                              callback_data="edit_fio")],
        [InlineKeyboardButton(text="Год поступления",
                              callback_data="edit_year")],
        [InlineKeyboardButton(text="Номер телефона",
                              callback_data="edit_phone")],
        [InlineKeyboardButton(text="Город",
                              callback_data="edit_city")],
        [InlineKeyboardButton(text="Направление",
                              callback_data="edit_direction")],
        [InlineKeyboardButton(text="⬅️ Назад",
                              callback_data="show_profile")]
    ])


def get_events_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить", callback_data="events_add")],
        [InlineKeyboardButton(text="Изменить", callback_data="events_edit")],
        [InlineKeyboardButton(text="Удалить", callback_data="events_delete")]
    ])


def get_change_cons_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить дату",
                              callback_data="change_cons_add")],
        [InlineKeyboardButton(text="Удалить дату",
                              callback_data="change_cons_del")]
    ])


# Отрисовка главного меню
async def send_main_menu(obj):
    if isinstance(obj, CallbackQuery):
        msg = obj.message
        await obj.answer()
    else:
        msg = obj

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Профиль",
                                  callback_data="show_profile")],
            [InlineKeyboardButton(text="Как поступить",
                                  callback_data="entrance")],
            [InlineKeyboardButton(text="Консультация",
                                  callback_data="consultation")],
            [InlineKeyboardButton(text="Календарь",
                                  callback_data="events")],
            [InlineKeyboardButton(text="Связаться с наставником",
                                  callback_data="mentor")],
        ]
    )
    caption = "Добро пожаловать!"
    await msg.answer_photo(
        photo=FSInputFile("app/img/menu.png"),
        caption=caption,
        reply_markup=keyboard,
    )


async def show_slots_list(send_func):
    slots = await rq.get_consultation_slots()
    if not slots:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
        ])
        await send_func("❌ Слоты консультаций не найдены.", reply_markup=kb)
        return

    buttons = [
        [InlineKeyboardButton(text=slot_text,
                              callback_data=f"cons_slot_{slot_id}")]
        for slot_id, slot_text in slots
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад",
                                         callback_data="main_menu")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await send_func("📅 Доступные консультации:", reply_markup=kb)


async def send_users_excel(users, caption, message):
    filename = f"app/temp/{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    df = pd.DataFrame([{
        "Telegram": f"https://t.me/{u.username}" if u.username else f"tg://user?id={u.tg_id}",
        "Фамилия": u.surname,
        "Имя": u.name,
        "Отчество": u.patronymic,
        "Год поступления": u.entry_year,
        "Телефон": u.phone_number,
        "Город": u.city,
        "Направление": u.direction,
        "Как узнали": u.referral_source,
        "Дата регистрации": u.reg_date
    } for u in users])

    df.to_excel(filename, index=False)

    await message.answer_document(FSInputFile(filename), caption=caption)

    os.remove(filename)


async def safe_answer(callback: CallbackQuery, text: str = None,
                      show_alert=False):
    try:
        await callback.answer(text=text, show_alert=show_alert)
    except TelegramBadRequest as e:
        if "query is too old" in str(e):
            await callback.message.answer("Кнопка устарела. Вот новое меню:")
            await send_main_menu(callback.message)


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
        f"Город: {user_p.city}\n"
        f"Направление: {user_p.direction}\n"
        f"Юзернейм: @{user.username or '—'}"
    )

    sub_text = (
        "📩 Отписаться от рассылки"
        if subscribed
        else "📴 Подписаться на рассылку"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏠 Главное меню",
                                     callback_data="main_menu"),
                InlineKeyboardButton(text=sub_text,
                                     callback_data="toggle_subscription")
            ],
            [InlineKeyboardButton(text="Изменить данные",
                                  callback_data="edit_profile")]
        ]
    )

    await send_func(profile_text, parse_mode="HTML", reply_markup=keyboard)


# Отрисовка информации о поступлении
async def send_about_entrance(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Записаться на собеседование",
                              callback_data="appointment_interview")],
        [InlineKeyboardButton(text="🏠 Главное меню",
                              callback_data="main_menu")]
    ])
    await message.answer_photo(
        photo=FSInputFile("app/img/entrance.png"),
        caption="<b>Поступление</b>\n\nМожно записаться на собеседование",
        parse_mode="HTML",
        reply_markup=keyboard
    )


def get_change_int_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить дату",
                              callback_data="change_int_add")],
        [InlineKeyboardButton(text="Удалить дату",
                              callback_data="change_int_del")]
    ])


# Отрисовка особенностей
async def send_features(send_func):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Записаться на консультацию",
                                  callback_data="appointment_consultation")],
            [InlineKeyboardButton(text="🏠 Главное меню",
                                  callback_data="main_menu")]
        ]
    )
    await send_func("Здесь можно записаться на консультацию",
                    reply_markup=keyboard)


# Отрисовка информации о наставников
async def send_mentor(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню",
                                  callback_data="main_menu")]
        ]
    )
    await message.answer_photo(
        photo=FSInputFile("app/img/mentor.png"),
        caption="Связаться с наставником",
        reply_markup=keyboard
    )


# Отрисовка информации о мероприятиях
async def send_events(send_func):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню",
                                  callback_data="main_menu")]
        ]
    )

    events = await rq.get_all_events()
    if not events:
        event_text = ("<b>Мероприятии</b>"
                      "\n\n❌ Нет запланированных мероприятий.")
    else:
        def sort_key(slot: str):
            date_part = slot.split()[0]
            try:
                day_str, month_str = date_part.split(".")
                day, month = int(day_str), int(month_str)
                return (month, day)
            except Exception:
                return (999, 999)

        sorted_events = sorted(events, key=lambda e: sort_key(e[0]))

        lines = [f"{slot} - {content}" for slot, content in sorted_events]
        event_text = ("<b>Мероприятии</b>"
                      "\n\n📅 Расписание мероприятий:\n\n" + "\n".join(lines))

    await send_func(event_text,
                    parse_mode="HTML",
                    reply_markup=keyboard)


async def send_consultation_slots(send_func, tg_id: int):
    slots = await rq.get_consultation_slots()
    user_slot = await rq.get_user_slot(tg_id)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🏠 Главное меню",
                                               callback_data="main_menu")]]
    )

    if not slots:
        await send_func(
            "<b>Консультации</b>\n\n"
            "Здесь вы можете выбрать удобную дату консультации с наставником."
            "\n\n❌ На данный момент даты консультаций ещё не добавлены.",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    buttons = []
    for slot_id, slot_text in slots:
        label = f"{slot_text}{' ✅' if slot_text == user_slot else ''}"
        buttons.append([InlineKeyboardButton(text=label,
                                             callback_data=f"slot_{slot_id}")])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню",
                                         callback_data="main_menu")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await send_func(
        "<b>Консультации</b>\n\n"
        "Выберите дату консультации с наставником:",
        parse_mode="HTML",
        reply_markup=kb
    )


async def send_interview_slots(send_func, tg_id: int):
    slots = await rq.get_interview_consultation_slots()
    user_slot = await rq.get_user_slot_interview(tg_id)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🏠 Главное меню",
                                               callback_data="main_menu")]]
    )

    if not slots:
        await send_func(
            "<b>Собеседование</b>\n\n"
            "Здесь можно выбрать дату записи на собеседование.\n\n"
            "❌ Пока даты собеседований не назначены.",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    buttons = []
    for slot_id, slot_text in slots:
        check_mark = " ✅" if slot_text == user_slot else ""
        label = f"{slot_text}{check_mark}"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"interview_slot_{slot_id}",
                ),
            ],
        )

    buttons.append(
        [InlineKeyboardButton(text="🏠 Главное меню",
                              callback_data="main_menu")]
    )
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await send_func("Выберите дату записи:", reply_markup=kb)


async def show_interview_slots_list(send_func):
    slots = await rq.get_interview_consultation_slots()
    buttons = [
        [InlineKeyboardButton(text=slot_text,
                              callback_data=f"int_slot_{slot_id}")]
        for slot_id, slot_text in slots
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await send_func("Доступные даты собеседований:", reply_markup=kb)


# /start
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id

    await rq.set_user(user_id, message.from_user.username)
    user = await rq.get_user_by_tg_id(user_id)
    if not (
        user.surname
        and user.name
        and user.patronymic
        and user.entry_year
        and user.phone_number
    ):
        await state.set_state(FSMRegistration.full_name)
        await message.answer(
            "Добро пожаловать!\n\n"
            "Введите Ваше <b>ФИО</b> через пробел:\n\n"
            "Пример:\n<b>Иванов Иван Иванович</b>\n\n"
            "Заполняя данные, я даю свое согласие на обработку "
            "моих персональных данных в соответствии с Федеральным "
            "законом от 27.07.2006 №152-ФЗ «О персональных данных», "
            "на условиях и для целей, определённых в Согласии "
            "на обработку персональных данных.",
            parse_mode="HTML",
        )
    else:
        await send_main_menu(message)


# кнопка Главное меню
@router.callback_query(F.data == "main_menu")
async def cb_main(callback: CallbackQuery):
    await rq.set_user(callback.from_user.id)
    await callback.message.delete()
    await send_main_menu(callback.message)
    await safe_answer(callback)


# кнопка Главное меню (из /send)
@router.callback_query(F.data == "main_menu_from_send")
async def cb_main_from_send(callback: CallbackQuery):
    await rq.set_user(callback.from_user.id)
    await send_main_menu(callback.message)
    await safe_answer(callback)


# кнопка Профиль
@router.callback_query(F.data == "show_profile")
async def cb_show_profile(callback: CallbackQuery):
    await callback.message.delete()
    await send_profile_menu(callback.message.answer, callback.from_user)
    await safe_answer(callback)


# кнопка Вкл/Выкл рассылку
@router.callback_query(F.data == "toggle_subscription")
async def cb_toggle(callback: CallbackQuery):
    user_id = callback.from_user.id
    await rq.change_subscribed(user_id)
    await send_profile_menu(callback.message.edit_text, callback.from_user)
    await safe_answer(callback, "Статус обновлён", show_alert=False)


# кнопка Как поступить
@router.callback_query(F.data == "entrance")
async def cb_captains(callback: CallbackQuery):
    await callback.message.delete()
    await send_about_entrance(callback.message)
    await safe_answer(callback)


@router.callback_query(F.data == "appointment_interview")
async def cb_appointment_interview(callback: CallbackQuery):
    await callback.message.delete()
    await send_interview_slots(callback.message.answer, callback.from_user.id)
    await safe_answer(callback)


@router.callback_query(F.data.startswith("interview_slot_"))
async def cb_interview_slot(callback: CallbackQuery):
    slot_id = int(callback.data[len("interview_slot_"):])
    tg_id = callback.from_user.id

    chosen = await rq.get_interview_slot_by_id(slot_id)
    current = await rq.get_user_slot_interview(tg_id)

    if current == chosen:
        await rq.clear_user_slot_interview(tg_id)
        await safe_answer(callback, "Запись на собеседование отменена")
    else:
        await rq.set_user_slot_interview(tg_id, chosen)
        await safe_answer(callback, f"Вы записаны на собеседование: {chosen}")

    await send_interview_slots(callback.message.edit_text, tg_id)


@router.message(Command("events"))
@admin_only
async def cmd_events(message: Message):
    await message.answer("Управление мероприятиями:",
                         reply_markup=get_events_kb())


@router.callback_query(F.data == "events_edit_start")
async def cmd_events_edit_start(query: CallbackQuery):
    await query.message.edit_text("Что менять?", reply_markup=get_events_kb())
    await query.answer()


@router.callback_query(F.data == "events_add")
async def cb_events_add(query: CallbackQuery):
    admin_event_mode[query.from_user.id] = "add_date"
    admin_event_data[query.from_user.id] = {}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Отмена",
                              callback_data="events_add_cancel")]
    ])
    await query.message.edit_text(
        "Введите дату мероприятия в формате <b>ДД.ММ ЧЧ:ММ</b>,"
        " например `26.06 17:00`",
        parse_mode="HTML",
        reply_markup=kb
    )
    await query.answer()


@router.callback_query(F.data == "events_add_cancel")
async def cb_events_add_cancel(query: CallbackQuery):
    admin_event_mode.pop(query.from_user.id, None)
    admin_event_data.pop(query.from_user.id, None)
    await query.message.edit_text("Операция добавления отменена.",
                                  reply_markup=get_events_kb())
    await query.answer()


@router.message(StateFilter(None),
                lambda message: (admin_event_mode
                                 .get(message.from_user.id) == "add_date"))
async def msg_events_add_date(message: Message):
    user_id = message.from_user.id
    if admin_event_mode.get(user_id) != "add_date":
        return
    date_text = message.text.strip()
    admin_event_data[user_id]["date"] = date_text
    admin_event_mode[user_id] = "add_content"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Отмена",
                              callback_data="events_add_cancel")]
    ])
    await message.answer(
        f"Дата сохранена: <b>{date_text}</b>"
        "\nТеперь введите содержимое мероприятия.",
        parse_mode="HTML",
        reply_markup=kb
    )


@router.message(StateFilter(None),
                lambda message: (admin_event_mode
                                 .get(message.from_user.id) == "add_content"))
async def msg_events_add_content(message: Message):
    user_id = message.from_user.id
    if admin_event_mode.get(user_id) != "add_content":
        return
    content = message.text.strip()
    date_text = admin_event_data[user_id]["date"]
    admin_event_data[user_id]["content"] = content
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data="events_add_confirm")],
        [InlineKeyboardButton(text="Нет", callback_data="events_add_cancel")]
    ])
    await message.answer(
        f"Добавить мероприятие?\n<code>{date_text} - {content}</code>",
        parse_mode="HTML",
        reply_markup=kb
    )


@router.callback_query(F.data == "events_add_confirm")
async def cb_events_add_confirm(query: CallbackQuery):
    user_id = query.from_user.id
    data = admin_event_data.get(user_id, {})
    await rq.add_event(data["date"], data["content"])
    admin_event_mode.pop(user_id, None)
    admin_event_data.pop(user_id, None)
    await query.message.edit_text("Мероприятие добавлено.",
                                  reply_markup=get_events_kb())
    await query.answer()


@router.callback_query(F.data == "events_edit")
async def cb_events_edit(query: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Дата",
                              callback_data="events_edit_date")],
        [InlineKeyboardButton(text="Содержимое",
                              callback_data="events_edit_content")],
        [InlineKeyboardButton(text="⬅️ Назад",
                              callback_data="events_edit_start")]
    ])
    await query.message.edit_text("Что менять?", reply_markup=kb)
    await query.answer()


@router.callback_query(F.data == "events_edit_date")
async def cb_events_edit_date(query: CallbackQuery):
    slots = await rq.get_all_events()
    buttons = [
        [
            InlineKeyboardButton(
                text=slot,
                callback_data=f"events_edit_date_sel|{slot}"
            )
        ]
        for slot, _ in slots
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад",
                                         callback_data="events_edit")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await query.message.edit_text("Выберите мероприятие по дате:",
                                  reply_markup=kb)
    await query.answer()


@router.callback_query(F.data.startswith("events_edit_date_sel|"))
async def cb_events_edit_date_sel(query: CallbackQuery):
    _, slot = query.data.split("|", 1)
    admin_event_mode[query.from_user.id] = "edit_set_date"
    admin_event_data[query.from_user.id] = {"old_date": slot}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data="events_edit")]
    ])
    await query.message.edit_text(
        f"Введите новую дату вместо <b>{slot}</b>:", parse_mode="HTML",
        reply_markup=kb
    )
    await query.answer()


@router.message(StateFilter(None),
                lambda message: (admin_event_mode
                                 .get(message
                                      .from_user.id) == "edit_set_date"))
async def msg_events_edit_set_date(message: Message):
    user_id = message.from_user.id
    if admin_event_mode.get(user_id) != "edit_set_date":
        return
    new_date = message.text.strip()
    old_date = admin_event_data[user_id]["old_date"]
    await rq.update_event_date(old_date, new_date)
    admin_event_mode.pop(user_id, None)
    admin_event_data.pop(user_id, None)
    await message.answer("Дата мероприятия обновлена.",
                         reply_markup=get_events_kb())


@router.callback_query(F.data == "events_edit_content")
async def cb_events_edit_content(query: CallbackQuery):
    slots = await rq.get_all_events()
    buttons = [
        [
            InlineKeyboardButton(
                text=slot,
                callback_data=f"events_edit_content_sel|{slot}"
            )
        ]
        for slot, _ in slots
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад",
                                         callback_data="events_edit")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await query.message.edit_text("Выберите мероприятие"
                                  " для редактирования содержимого:",
                                  reply_markup=kb)
    await query.answer()


@router.callback_query(F.data.startswith("events_edit_content_sel|"))
async def cb_events_edit_content_sel(query: CallbackQuery):
    _, slot = query.data.split("|", 1)
    admin_event_mode[query.from_user.id] = "edit_set_content"
    admin_event_data[query.from_user.id] = {"old_date": slot}
    event = await rq.get_event_by_date(slot)
    old_content = event.content if event else ""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data="events_edit")]
    ])
    await query.message.edit_text(
        f"Старое содержимое:\n<code>{old_content}</code>"
        "\nВведите новое содержимое:",
        parse_mode="HTML",
        reply_markup=kb
    )
    await query.answer()


@router.message(StateFilter(None),
                lambda message: (admin_event_mode
                                 .get(message
                                      .from_user.id) == "edit_set_content"))
async def msg_events_edit_set_content(message: Message):
    user_id = message.from_user.id
    if admin_event_mode.get(user_id) != "edit_set_content":
        return
    new_content = message.text.strip()
    old_date = admin_event_data[user_id]["old_date"]
    await rq.update_event_content_by_date(old_date, new_content)
    admin_event_mode.pop(user_id, None)
    admin_event_data.pop(user_id, None)
    await message.answer("Содержимое мероприятия обновлено.",
                         reply_markup=get_events_kb())


@router.callback_query(F.data == "events_delete")
async def cb_events_delete(query: CallbackQuery):
    slots = await rq.get_all_events()
    buttons = [
        [
            InlineKeyboardButton(
                text=slot,
                callback_data=f"events_delete_sel|{slot}"
            )
        ]
        for slot, _ in slots
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад",
                                         callback_data="events_edit_start")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await query.message.edit_text("Выберите мероприятие для удаления:",
                                  reply_markup=kb)
    await query.answer()


@router.callback_query(F.data.startswith("events_delete_sel|"))
async def cb_events_delete_sel(query: CallbackQuery):
    _, slot = query.data.split("|", 1)
    event = await rq.get_event_by_date(slot)
    content = event.content if event else ""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Удалить",
                              callback_data=f"events_delete_confirm|{slot}")],
        [InlineKeyboardButton(text="⬅️ Отменить",
                              callback_data="events_delete_cancel")]
    ])
    await query.message.edit_text(f"Удалить мероприятие?"
                                  f"\n<code>{slot} - {content}</code>",
                                  parse_mode="HTML", reply_markup=kb)
    await query.answer()


@router.callback_query(F.data == "events_delete_cancel")
async def cb_events_delete_cancel(query: CallbackQuery):
    await query.message.edit_text("Удаление отменено.",
                                  reply_markup=get_events_kb())
    await query.answer()


@router.callback_query(F.data.startswith("events_delete_confirm|"))
async def cb_events_delete_confirm(query: CallbackQuery):
    _, slot = query.data.split("|", 1)
    await rq.delete_event_by_date(slot)
    await query.message.edit_text("Мероприятие удалено.",
                                  reply_markup=get_events_kb())
    await query.answer()


@router.message(Command("change_int"))
@admin_only
async def cmd_change_interview(message: Message):
    await message.answer("Выберите действие с датами собеседований:",
                         reply_markup=get_change_int_kb())


@router.callback_query(F.data == "change_int_add")
async def cb_change_int_add(query: CallbackQuery):
    admin_int_mode[query.from_user.id] = "add"
    await query.message.edit_text(
        "Введите новую дату в формате <b>ДД.ММ ЧЧ:ММ</b>,"
        " например `26.06 17:00`",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Отмена",
                                  callback_data="change_interview_back")]
        ])
    )
    await query.answer()


@router.callback_query(F.data == "change_int_del")
async def cb_change_int_del(query: CallbackQuery):
    slots = await rq.get_interview_consultation_slots()
    if not slots:
        await query.answer("Слотов пока нет", show_alert=True)
        return await query.message.edit_text("Нет дат для удаления.",
                                             reply_markup=get_change_int_kb())

    buttons = [
        [InlineKeyboardButton(text=slot_text,
                              callback_data=f"change_int_delete_{slot_id}")]
        for slot_id, slot_text in slots
    ]
    buttons.append(
        [InlineKeyboardButton(text="⬅️ Назад",
                              callback_data="change_interview_back")]
    )
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await query.message.edit_text("Выберите дату для удаления:",
                                  reply_markup=kb)
    await query.answer()


@router.message(Command("file"))
@admin_only
async def cmd_file(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Все пользователи",
                              callback_data="file_all")],
        [InlineKeyboardButton(text="Консультации",
                              callback_data="file_consult")],
        [InlineKeyboardButton(text="Собеседования",
                              callback_data="file_interview")]
    ])
    await message.answer("Выберите, какой файл вы хотите получить:",
                         reply_markup=kb)


@router.callback_query(F.data == "file")
@admin_only
async def file_back(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Все пользователи",
                              callback_data="file_all")],
        [InlineKeyboardButton(text="Консультации",
                              callback_data="file_consult")],
        [InlineKeyboardButton(text="Собеседования",
                              callback_data="file_interview")]
    ])
    await callback.message.edit_text("Выберите,"
                                     " какой файл вы хотите получить:",
                                     reply_markup=kb)
    await safe_answer(callback)


@router.callback_query(F.data == "file_consult")
async def file_consult(callback: CallbackQuery):
    slots = await rq.get_consultation_slots()
    if not slots:
        await safe_answer(callback, "Нет доступных дат.", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=slot_text,
                              callback_data=f"file_consult_date_{slot_id}")]
        for slot_id, slot_text in slots
    ] + [[InlineKeyboardButton(text="⬅️ Назад", callback_data="file")]])

    await callback.message.edit_text("Выберите дату консультации:",
                                     reply_markup=kb)


@router.callback_query(F.data.startswith("file_consult_date_"))
async def file_by_consult_date(callback: CallbackQuery):
    slot_id = int(callback.data.split("_")[-1])
    slot_text = await rq.get_slot_by_id(slot_id)
    users = await rq.get_users_by_slot(slot_text)

    if not users:
        await safe_answer(callback, "Нет записей на эту дату.",
                          show_alert=True)
        return

    await send_users_excel(users, caption=f"Консультация: {slot_text}",
                           message=callback.message)
    await safe_answer(callback)


@router.callback_query(F.data == "file_interview")
async def file_interview(callback: CallbackQuery):
    slots = await rq.get_interview_consultation_slots()
    if not slots:
        await safe_answer(callback, "Нет доступных дат.", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=slot_text,
                              callback_data=f"file_interview_date_{slot_id}")]
        for slot_id, slot_text in slots
    ] + [[InlineKeyboardButton(text="⬅️ Назад", callback_data="file")]])

    await callback.message.edit_text("Выберите дату собеседования:",
                                     reply_markup=kb)


@router.callback_query(F.data.startswith("file_interview_date_"))
async def file_by_interview_date(callback: CallbackQuery):
    slot_id = int(callback.data.split("_")[-1])
    slot_text = await rq.get_interview_slot_by_id(slot_id)
    users = await rq.get_users_by_slot_interview(slot_text)

    if not users:
        await safe_answer(callback, "Нет записей на эту дату.",
                          show_alert=True)
        return

    await send_users_excel(users, caption=f"Собеседование: {slot_text}",
                           message=callback.message)
    await safe_answer(callback)


@router.callback_query(F.data == "file_all")
async def file_all(callback: CallbackQuery):
    users = await rq.get_all_users()

    if not users:
        await safe_answer(callback, "Нет пользователей.", show_alert=True)
        return

    await send_users_excel(users, caption="Все пользователи",
                           message=callback.message)
    await safe_answer(callback)


@router.message(Command("int"))
@admin_only
async def cmd_int(message: Message):
    await show_interview_slots_list(message.answer)


@router.callback_query(F.data.startswith("int_slot_"))
async def cb_int_slot(callback: CallbackQuery):
    slot_id = int(callback.data.split("_")[-1])
    slot_text = await rq.get_interview_slot_by_id(slot_id)
    users = await rq.get_users_by_slot_interview(slot_text)

    if not users:
        text = f"На <b>{slot_text}</b> ещё никто не записан."
    else:
        lines = []
        for idx, user in enumerate(users, start=1):
            chat = await callback.bot.get_chat(user.tg_id)
            username_text = (
                f"@{chat.username}" if chat.username else "(нет юзернейма)"
            )
            fio = (
                " ".join(part for part in [user.surname,
                                           user.name,
                                           user.patronymic] if part)
                or "(ФИО не указано)"
            )
            phone = user.phone_number or "(телефон не указан)"
            year = user.entry_year or "(год не указан)"
            lines.append(f"{idx}. {fio} | {phone} | {year} | {username_text}")
        text = f"Записанные на <b>{slot_text}</b>:\n" + "\n".join(lines)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="int_back")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await safe_answer(callback)


@router.callback_query(F.data == "int_back")
async def cb_int_back(callback: CallbackQuery):
    await show_interview_slots_list(callback.message.edit_text)
    await safe_answer(callback)


@router.callback_query(F.data.startswith("change_int_delete_"))
async def cb_change_int_delete(query: CallbackQuery):
    slot_id = int(query.data.split("_")[-1])
    await rq.delete_interview_slot(slot_id)
    await query.answer("Дата удалена")
    await cb_change_int_del(query)


@router.callback_query(F.data == "change_interview_back")
async def cb_change_interview_back(query: CallbackQuery):
    admin_int_mode.pop(query.from_user.id, None)
    await query.message.edit_text(
        "Выберите действие с датами собеседований:",
        reply_markup=get_change_int_kb()
    )
    await query.answer()


@router.message(lambda message: admin_int_mode
                .get(message.from_user.id) == "add")
async def handle_add_interview_slot(message: Message):
    if admin_int_mode.get(message.from_user.id) != "add":
        return

    text = message.text.strip()
    if not re.fullmatch(r"\d{2}\.\d{2} \d{2}:\d{2}", text):
        return await message.answer("Неверный формат. "
                                    "Введите, например, `26.06 17:00`.",
                                    parse_mode="Markdown")

    try:
        await rq.add_interview_slot(text)
        await message.answer(f"Дата «{text}» успешно добавлена.")
    except Exception:
        await message.answer("Ошибка: возможно, такая дата уже существует.")
    finally:
        admin_int_mode.pop(message.from_user.id, None)
        await message.answer("Выберите действие:",
                             reply_markup=get_change_int_kb())


# кнопка Консультация
@router.callback_query(F.data == "consultation")
async def cb_consultation(callback: CallbackQuery):
    await callback.message.delete()
    await send_consultation_slots(callback.message.answer,
                                  callback.from_user.id)
    await safe_answer(callback)


@router.callback_query(F.data.startswith("slot_"))
async def cb_slot(callback: CallbackQuery):
    slot_id = int(callback.data.split("_", 1)[1])
    tg_id = callback.from_user.id

    chosen = await rq.get_slot_by_id(slot_id)
    current = await rq.get_user_slot(tg_id)

    if current == chosen:
        await rq.clear_user_slot(tg_id)
        await safe_answer(callback, "Запись отменена")
    else:
        await rq.set_user_slot(tg_id, chosen)
        await safe_answer(callback, f"Вы записаны на {chosen}")

    await send_consultation_slots(callback.message.edit_text, tg_id)


# кнопка Связь с наставником
@router.callback_query(F.data == "mentor")
async def cb_mentor(callback: CallbackQuery):
    await callback.message.delete()
    await send_mentor(callback.message)
    await safe_answer(callback)


# кнопка Календарь
@router.callback_query(F.data == "events")
async def cb_events(callback: CallbackQuery):
    await callback.message.delete()
    await send_events(callback.message.answer)
    await safe_answer(callback)


@router.message(Command("change_cons"))
@admin_only
async def cmd_change_cons(message: Message):
    await message.answer("Выберите действие с датами консультаций:",
                         reply_markup=get_change_cons_kb())


@router.callback_query(F.data == "change_cons_add")
async def cb_change_cons_add(query: CallbackQuery):
    admin_cons_mode[query.from_user.id] = "add"
    await query.message.edit_text(
        "Введите новую дату в формате <b>ДД.ММ ЧЧ:ММ</b>,"
        " например `26.06 17:00`",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Отмена",
                                      callback_data="change_cons_back")]
            ]
        )
    )
    await query.answer()


@router.callback_query(F.data == "change_cons_del")
async def cb_change_cons_del(query: CallbackQuery):
    slots = await rq.get_consultation_slots()
    if not slots:
        await query.answer("Слотов пока нет", show_alert=True)
        return await query.message.edit_text("Нет дат для удаления.",
                                             reply_markup=get_change_cons_kb())

    buttons = [
        [InlineKeyboardButton(text=slot_text,
                              callback_data=f"change_cons_delete_{slot_id}")]
        for slot_id, slot_text in slots
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад",
                                         callback_data="change_cons_back")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await query.message.edit_text("Выберите дату для удаления:",
                                  reply_markup=kb)
    await query.answer()


@router.callback_query(F.data.startswith("change_cons_delete_"))
async def cb_change_cons_delete(query: CallbackQuery):
    slot_id = int(query.data.split("_")[-1])
    await rq.delete_consultation_slot(slot_id)
    await query.answer("Дата удалена", show_alert=False)
    await cb_change_cons_del(query)


@router.callback_query(F.data == "change_cons_back")
async def cb_change_cons_back(query: CallbackQuery):
    admin_cons_mode.pop(query.from_user.id, None)
    await query.message.edit_text("Выберите действие с датами консультаций:",
                                  reply_markup=get_change_cons_kb())
    await query.answer()


@router.message(StateFilter(None),
                lambda message: (admin_cons_mode
                                 .get(message.from_user.id) == "add"))
async def handle_add_slot(message: Message):
    user_id = message.from_user.id
    if admin_cons_mode.get(user_id) != "add":
        return

    text = message.text.strip()
    if not re.fullmatch(r"\d{2}\.\d{2} \d{2}:\d{2}", text):
        return await message.answer("Неверный формат."
                                    " Введите, например, `26.06 17:00`.",
                                    parse_mode="Markdown")

    try:
        await rq.add_consultation_slot(text)
        await message.answer(f"Дата «{text}» успешно добавлена.")
    except Exception:
        await message.answer("Ошибка: возможно, такая дата уже существует.")
    finally:
        admin_cons_mode.pop(user_id, None)
        await message.answer("Выберите действие:",
                             reply_markup=get_change_cons_kb())


@router.message(Command("cons"))
@admin_only
async def cmd_cons(message: Message):
    await show_slots_list(message.answer)


@router.callback_query(F.data.startswith("cons_slot_"))
async def cb_cons_slot(callback: CallbackQuery):
    slot_id = int(callback.data.split("_", 2)[2])
    slot_text = await rq.get_slot_by_id(slot_id)

    users = await rq.get_users_by_slot(slot_text)

    if not users:
        text = f"На <b>{slot_text}</b> ещё никто не записан."
    else:
        lines = []
        for idx, user in enumerate(users, start=1):
            chat = await callback.bot.get_chat(user.tg_id)
            username_text = (
                f"@{chat.username}" if chat.username else "(нет юзернейма)"
            )
            fio = (
                " ".join(part for part in [user.surname,
                                           user.name,
                                           user.patronymic] if part)
                or "(ФИО не указано)"
            )
            phone = user.phone_number or "(телефон не указан)"
            year = user.entry_year or "(год не указан)"

            lines.append(f"{idx}. {fio} | {phone} | {year} | {username_text}")

        text = f"Записанные на <b>{slot_text}</b>:\n" + "\n".join(lines)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="cons_back")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await safe_answer(callback)


@router.callback_query(F.data == "cons_back")
async def cb_cons_back(callback: CallbackQuery):
    await show_slots_list(callback.message.edit_text)
    await safe_answer(callback)


# команда /send
@router.message(Command("send"))
@admin_only
async def send_broadcast(message: Message):
    if message.caption:
        content = message.caption
        if content.lower().startswith("/send"):
            content = content[5:].strip()
    else:
        content = message.text.removeprefix("/send").strip()

    if not content and not (message.photo or message.video):
        return await message.answer("⚠️ Укажи текст "
                                    " после команды /send или"
                                    " прикрепи фото/видео с подписью.")

    users = await rq.get_all_subscribed_users()
    success, failed = 0, 0

    user_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню",
                                  callback_data="main_menu_from_send")]
        ]
    )

    for user in users:
        try:
            if message.photo:
                await message.bot.send_photo(
                    chat_id=user.tg_id,
                    photo=message.photo[-1].file_id,
                    caption=content,
                    reply_markup=user_keyboard
                )
            elif message.video:
                await message.bot.send_video(
                    chat_id=user.tg_id,
                    video=message.video.file_id,
                    caption=content,
                    reply_markup=user_keyboard
                )
            else:
                await message.bot.send_message(
                    chat_id=user.tg_id,
                    text=content,
                    reply_markup=user_keyboard
                )
            success += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1

    await message.answer(
        f"📣 Рассылка завершена\n\n✅ Отправлено: {success}\n❌ Ошибок: {failed}"
    )


@router.message(FSMRegistration.full_name)
async def reg_full_name(message: Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) == 3:
        surname, name, patronymic = parts
    elif len(parts) == 2:
        surname, name = parts
        patronymic = "-"
    else:
        await message.answer(
            "⚠️ Пожалуйста, введите ФИО целиком через пробел, например:\n"
            "Иванов Иван Иванович\n"
            "Или без отчества: Иванов Иван"
        )
        return

    await state.update_data(surname=surname, name=name, patronymic=patronymic)
    await state.set_state(FSMRegistration.entry_year)

    await message.answer(
        "Выберите <b>год поступления</b>:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="2025",
                                      callback_data="year_2025")],
                [InlineKeyboardButton(text="2026",
                                      callback_data="year_2026")],
                [InlineKeyboardButton(text="2027",
                                      callback_data="year_2027")],
                [InlineKeyboardButton(text="После 2027",
                                      callback_data="year_2027+")],
            ]
        )
    )


@router.callback_query(F.data.startswith("year_"), FSMRegistration.entry_year)
async def reg_entry_year(callback: CallbackQuery, state: FSMContext):
    year = callback.data.split("_")[1]
    if year == "2027+":
        await state.update_data(entry_year="После 2027")
    else:
        await state.update_data(entry_year=year)
    await state.set_state(FSMRegistration.phone)
    await callback.message.delete()
    await callback.message.answer("Введите ваш <b>номер телефона</b>"
                                  " в формате +7XXXXXXXXXX или "
                                  "укажите прочерк:", parse_mode="HTML")
    await safe_answer(callback)


@router.message(FSMRegistration.phone)
async def reg_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not re.fullmatch(r"\+7\d{3}\d{3}\d{2}\d{2}", phone) and phone != "-":
        await message.answer("⚠️ Неверный формат."
                             " Попробуйте ещё раз:"
                             " +7XXXXXXXXXX\nИли укажите -")
        return
    await state.update_data(phone=phone)

    await state.set_state(FSMRegistration.city)
    await message.answer("Укажите ваш <b>город</b>: ", parse_mode="HTML")


@router.message(FSMRegistration.city)
async def reg_city(message: Message, state: FSMContext):
    city = message.text.strip()
    await state.update_data(city=city)

    await state.set_state(FSMRegistration.direction)
    await message.answer(
        "Выберите <b>направление подготовки</b>:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="39.03.01 Социология управления"
                                      " и организаций",
                                      callback_data="dir_1")],
                [InlineKeyboardButton(text="38.03.01 Государственное и"
                                      " муниципальное управление",
                                      callback_data="dir_2")],
                [InlineKeyboardButton(text="42.03.01 Реклама и связи с "
                                      "общественностью",
                                      callback_data="dir_3")],
                [InlineKeyboardButton(text="38.03.06 Маркетинг и "
                                      "логистика в коммерции",
                                      callback_data="dir_4")],
                [InlineKeyboardButton(text="38.05.01 Экономико-правовое"
                                      " обеспечение экономической"
                                      " безопасности", callback_data="dir_5")],
                [InlineKeyboardButton(text="40.03.01 Юриспруденция",
                                      callback_data="dir_6")],
                [InlineKeyboardButton(text="40.05.01 Правовое обеспечение"
                                      " национальной безопасности",
                                      callback_data="dir_7")],
                [InlineKeyboardButton(text="41.03.06 Публичная "
                                      "политика и управление",
                                      callback_data="dir_8")]
            ]
        )
    )


@router.callback_query(F.data.startswith("dir_"), FSMRegistration.direction)
async def reg_direction(callback: CallbackQuery, state: FSMContext):
    direction_code = callback.data.strip()
    direction = DIRECTIONS.get(direction_code, "Неизвестное направление")

    await state.update_data(direction=direction)

    await callback.message.delete()

    await callback.message.answer(
        "Откуда Вы <b>узнали о нас</b>:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="От волонтёра на отборочной комиссии",
                                      callback_data="source_1")],
                [InlineKeyboardButton(text="Из социальных сетей",
                                      callback_data="source_2")],
                [InlineKeyboardButton(text="От знакомых/друзей",
                                      callback_data="source_3")],
                [InlineKeyboardButton(text="Другое",
                                      callback_data="source_4")]
            ]
        )
    )


@router.callback_query(F.data.startswith("source_"), FSMRegistration.direction)
async def reg_direction(callback: CallbackQuery, state: FSMContext):
    referral_code = callback.data.strip()
    referral_source = REFERRAL_SOURCES.get(referral_code, "Другое")
    
    await state.update_data(referral_source=referral_source)
    
    await callback.message.delete()

    data = await state.get_data()
    await rq.set_fio(callback.from_user.id, data["surname"], data["name"],
                     data["patronymic"])
    await rq.set_entry_year(callback.from_user.id, data["entry_year"])
    await rq.set_phone_number(callback.from_user.id, data["phone"])
    await rq.set_city(callback.from_user.id, data["city"])
    await rq.set_direction(callback.from_user.id, data["direction"])
    await rq.set_referral_source(callback.from_user.id, data["referral_source"])
    await rq.set_reg_date(callback.from_user.id, date.today())
    await state.clear()

    await safe_answer(callback, "✅ Регистрация завершена!")
    await send_main_menu(callback)


@router.callback_query(F.data == "edit_profile")
async def cb_edit_profile(callback: CallbackQuery):
    await callback.message.edit_text(
        "Что вы хотите изменить?",
        reply_markup=get_edit_profile_kb()
    )


@router.callback_query(F.data == "edit_fio")
async def cb_edit_fio(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_edit_mode[user_id] = "fio"

    prompt = await callback.message.edit_text("Введите новое <b>ФИО</b>"
                                              " через пробел:",
                                              parse_mode="HTML")
    user_prompt_message_id[user_id] = prompt.message_id
    await safe_answer(callback)


@router.callback_query(F.data == "edit_phone")
async def cb_edit_phone_number(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_edit_mode[user_id] = "phone"

    prompt = await callback.message.edit_text("Введите ваш"
                                              " <b>номер телефона</b>"
                                              " в формате +7XXXXXXXXXX:",
                                              parse_mode="HTML")
    user_prompt_message_id[user_id] = prompt.message_id
    await safe_answer(callback)


@router.callback_query(F.data == "edit_year")
async def cb_edit_year(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_edit_mode[user_id] = "year"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="2025", callback_data="year_2025")],
        [InlineKeyboardButton(text="2026", callback_data="year_2026")],
        [InlineKeyboardButton(text="2027", callback_data="year_2027")],
        [InlineKeyboardButton(text="После 2027", callback_data="year_2027+")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="edit_profile")]
    ])

    await callback.message.edit_text("Выберите год поступления:",
                                     reply_markup=keyboard)
    await safe_answer(callback)


@router.callback_query(F.data.startswith("year_"))
async def cb_select_year(callback: CallbackQuery):
    user_id = callback.from_user.id
    year = callback.data.split("_")[1]

    if year not in ("2025", "2026", "2027", "2027+"):
        return

    if year == "2027+":
        await rq.set_entry_year(user_id, "После 2027")
    else:
        await rq.set_entry_year(user_id, year)

    user_edit_mode.pop(user_id, None)
    user_prompt_message_id.pop(user_id, None)

    await callback.message.delete()

    await callback.message.answer(
        "Что вы хотите изменить?",
        reply_markup=get_edit_profile_kb()
    )
    await safe_answer(callback)


@router.callback_query(F.data == "edit_city")
async def cb_edit_city(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_edit_mode[user_id] = "city"

    prompt = await callback.message.edit_text(
        "Укажите ваш <b>город</b>:",
        parse_mode="HTML"
    )
    user_prompt_message_id[user_id] = prompt.message_id
    await safe_answer(callback)


@router.callback_query(F.data == "edit_direction")
async def cb_edit_direction(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_edit_mode[user_id] = "direction"

    buttons = [
        [InlineKeyboardButton(text=text, callback_data=code)]
        for code, text in DIRECTIONS.items()
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад",
                                         callback_data="edit_profile")])

    await callback.message.edit_text(
        "Выберите <b>направление подготовки</b>:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await safe_answer(callback)


@router.callback_query(F.data.startswith("dir_"))
async def cb_edit_direction_select(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_edit_mode.get(user_id) != "direction":
        return

    direction_code = callback.data.strip()
    direction = DIRECTIONS.get(direction_code, "Неизвестное направление")

    await rq.set_direction(user_id, direction)

    user_edit_mode.pop(user_id, None)
    user_prompt_message_id.pop(user_id, None)

    await callback.message.delete()

    await callback.message.answer(
        "Что вы хотите изменить?",
        reply_markup=get_edit_profile_kb()
    )
    await safe_answer(callback)


@router.message(StateFilter(None),
                lambda message: message.from_user.id in user_edit_mode)
async def msg_edit_profile(message: Message):
    user_id = message.from_user.id

    if user_id not in user_edit_mode:
        return

    mode = user_edit_mode[user_id]
    prompt_id = user_prompt_message_id.get(user_id)

    if mode == "fio":
        parts = message.text.strip().split()
        if len(parts) != 3:
            await message.delete()
            err = await message.answer("⚠️ Введите ФИО в"
                                       " формате:\nФамилия Имя Отчество")
            user_error_message_id[user_id] = err.message_id
            return
        surname, name, patronymic = parts
        await rq.set_fio(user_id, surname, name, patronymic)

    elif mode == "phone":
        phone = message.text.strip()
        if not re.fullmatch(r"\+7\d{3}\d{3}\d{2}\d{2}",
                            phone) and phone != "-":
            await message.delete()
            err = await message.answer("⚠️ Неверный формат."
                                       " Попробуйте ещё раз: +7XXXXXXXXXX"
                                       "\nИли укажите -")
            user_error_message_id[user_id] = err.message_id
            return
        await rq.set_phone_number(user_id, phone)

    elif mode == "city":
        city = message.text.strip()
        await rq.set_city(user_id, city)

    user_edit_mode.pop(user_id, None)
    user_prompt_message_id.pop(user_id, None)

    await message.delete()
    if prompt_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id,
                                             message_id=prompt_id)
        except Exception:
            pass

    err_id = user_error_message_id.pop(user_id, None)
    if err_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id,
                                             message_id=err_id)
        except Exception:
            pass

    await message.answer(
        "Что вы хотите изменить?",
        reply_markup=get_edit_profile_kb()
    )
