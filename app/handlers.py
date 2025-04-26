from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram.filters import CommandStart, Command, StateFilter
import app.database.requests as rq

from aiogram.fsm.context import FSMContext
from app.states.registration import FSMRegistration

import re

router = Router()

user_edit_mode = {}
user_prompt_message_id = {}
user_error_message_id = {}
admin_cons_mode = {}
admin_int_mode = {}
admin_event_mode = {}
admin_event_data = {}


def get_edit_profile_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ФИО", callback_data="edit_fio")],
        [InlineKeyboardButton(text="Год поступления", callback_data="edit_year")],
        [InlineKeyboardButton(text="Номер телефона", callback_data="edit_phone")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="show_profile")]
    ])


def get_events_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить", callback_data="events_add")],
        [InlineKeyboardButton(text="Изменить", callback_data="events_edit")],
        [InlineKeyboardButton(text="Удалить", callback_data="events_delete")]
    ])


def get_change_cons_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить дату", callback_data="change_cons_add")],
        [InlineKeyboardButton(text="Удалить дату", callback_data="change_cons_del")]
    ])


# Отрисовка главного меню
async def send_main_menu(message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Профиль", callback_data="show_profile")],
            [InlineKeyboardButton(text="Как поступить", callback_data="entrance")],
            [InlineKeyboardButton(text="Консультация", callback_data="consultation")],
            [InlineKeyboardButton(text="Календарь", callback_data="events")],
            [InlineKeyboardButton(text="Связаться с настивником", callback_data="mentor")]
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


# Отрисовка информации о поступлении
async def send_about_entrance(send_func):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Записаться на собеседование", callback_data="appointment_interview")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    await send_func("Можно записаться на собеседование", reply_markup=keyboard)


def get_change_int_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить дату", callback_data="change_int_add")],
        [InlineKeyboardButton(text="Удалить дату", callback_data="change_int_del")]
    ])


# Отрисовка особенностей
async def send_features(send_func):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Записаться на консультацию", callback_data="appointment_consultation")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
    )
    await send_func("Здесь можно записаться на консультацию", reply_markup=keyboard)


# Отрисовка информации о наставников
async def send_mentor(send_func):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
    )
    await send_func("Связаться с наставником", reply_markup=keyboard)


# Отрисовка информации о мероприятиях
async def send_events(send_func):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
    )

    events = await rq.get_all_events()
    if not events:
        event_text = "Нет запланированных мероприятий."
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
        event_text = "📅 Расписание мероприятий:\n\n" + "\n".join(lines)

    await send_func(event_text, reply_markup=keyboard)


async def send_consultation_slots(send_func, tg_id: int):
    slots = await rq.get_consultation_slots()
    user_slot = await rq.get_user_slot(tg_id)

    buttons = []
    for slot_id, slot_text in slots:
        label = f"{slot_text}{' ✅' if slot_text == user_slot else ''}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"slot_{slot_id}")])

    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await send_func("Выберите дату консультации:", reply_markup=kb)


async def show_slots_list(send_func):
    slots = await rq.get_consultation_slots()
    buttons = [
        [InlineKeyboardButton(text=slot_text, callback_data=f"cons_slot_{slot_id}")]
        for slot_id, slot_text in slots
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await send_func("Доступные даты консультаций:", reply_markup=kb)


async def send_interview_slots(send_func, tg_id: int):
    slots = await rq.get_interview_consultation_slots()
    user_slot = await rq.get_user_slot_interview(tg_id)

    buttons = []
    for slot_id, slot_text in slots:
        label = f"{slot_text}{' ✅' if slot_text == user_slot else ''}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"interview_slot_{slot_id}")])

    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await send_func("Выберите дату записи:", reply_markup=kb)


async def show_interview_slots_list(send_func):
    slots = await rq.get_interview_consultation_slots()
    buttons = [
        [InlineKeyboardButton(text=slot_text, callback_data=f"int_slot_{slot_id}")]
        for slot_id, slot_text in slots
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await send_func("Доступные даты собеседований:", reply_markup=kb)


# /start
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id

    await rq.set_user(user_id)
    user = await rq.get_user_by_tg_id(user_id)

    if not (user.surname and user.name and user.patronymic and user.entry_year and user.phone_number):
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


# кнопка Как поступить
@router.callback_query(F.data == "entrance")
async def cb_captains(callback: CallbackQuery):
    await callback.message.delete()
    await send_about_entrance(callback.message.answer)
    await callback.answer()


@router.callback_query(F.data == "appointment_interview")
async def cb_appointment_interview(callback: CallbackQuery):
    await callback.message.delete()
    await send_interview_slots(callback.message.answer, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("interview_slot_"))
async def cb_interview_slot(callback: CallbackQuery):
    slot_id = int(callback.data[len("interview_slot_"):])
    tg_id = callback.from_user.id

    chosen = await rq.get_interview_slot_by_id(slot_id)
    current = await rq.get_user_slot_interview(tg_id)

    if current == chosen:
        await rq.clear_user_slot_interview(tg_id)
        await callback.answer("Запись на собеседование отменена")
    else:
        await rq.set_user_slot_interview(tg_id, chosen)
        await callback.answer(f"Вы записаны на собеседование: {chosen}")

    await send_interview_slots(callback.message.edit_text, tg_id)


@router.message(Command("events"))
async def cmd_events(message: Message):
    await message.answer("Управление мероприятиями:", reply_markup=get_events_kb())


@router.callback_query(F.data == "events_edit_start")
async def cmd_events_edit_start(query: CallbackQuery):
    await query.message.edit_text("Что менять?", reply_markup=get_events_kb())
    await query.answer()


@router.callback_query(F.data == "events_add")
async def cb_events_add(query: CallbackQuery):
    admin_event_mode[query.from_user.id] = "add_date"
    admin_event_data[query.from_user.id] = {}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data="events_add_cancel")]
    ])
    await query.message.edit_text(
        "Введите дату мероприятия в формате <b>ДД.ММ ЧЧ:ММ</b>, например `26.06 17:00`",
        parse_mode="HTML",
        reply_markup=kb
    )
    await query.answer()


@router.callback_query(F.data == "events_add_cancel")
async def cb_events_add_cancel(query: CallbackQuery):
    admin_event_mode.pop(query.from_user.id, None)
    admin_event_data.pop(query.from_user.id, None)
    await query.message.edit_text("Операция добавления отменена.", reply_markup=get_events_kb())
    await query.answer()


@router.message(StateFilter(None),
                lambda message: admin_event_mode.get(message.from_user.id) == "add_date")
async def msg_events_add_date(message: Message):
    user_id = message.from_user.id
    if admin_event_mode.get(user_id) != "add_date":
        return
    date_text = message.text.strip()
    admin_event_data[user_id]["date"] = date_text
    admin_event_mode[user_id] = "add_content"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data="events_add_cancel")]
    ])
    await message.answer(
        f"Дата сохранена: <b>{date_text}</b>\nТеперь введите содержимое мероприятия.",
        parse_mode="HTML",
        reply_markup=kb
    )


@router.message(StateFilter(None),
                lambda message: admin_event_mode.get(message.from_user.id) == "add_content")
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
    await query.message.edit_text("Мероприятие добавлено.", reply_markup=get_events_kb())
    await query.answer()


@router.callback_query(F.data == "events_edit")
async def cb_events_edit(query: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Дата", callback_data="events_edit_date")],
        [InlineKeyboardButton(text="Содержимое", callback_data="events_edit_content")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="events_edit_start")]
    ])
    await query.message.edit_text("Что менять?", reply_markup=kb)
    await query.answer()


@router.callback_query(F.data == "events_edit_date")
async def cb_events_edit_date(query: CallbackQuery):
    slots = await rq.get_all_events()
    buttons = [[InlineKeyboardButton(text=slot, callback_data=f"events_edit_date_sel|{slot}")]
               for slot, _ in slots]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="events_edit")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await query.message.edit_text("Выберите мероприятие по дате:", reply_markup=kb)
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
        f"Введите новую дату вместо <b>{slot}</b>:", parse_mode="HTML", reply_markup=kb
    )
    await query.answer()


@router.message(StateFilter(None),
                lambda message: admin_event_mode.get(message.from_user.id) == "edit_set_date")
async def msg_events_edit_set_date(message: Message):
    user_id = message.from_user.id
    if admin_event_mode.get(user_id) != "edit_set_date":
        return
    new_date = message.text.strip()
    old_date = admin_event_data[user_id]["old_date"]
    await rq.update_event_date(old_date, new_date)
    admin_event_mode.pop(user_id, None)
    admin_event_data.pop(user_id, None)
    await message.answer("Дата мероприятия обновлена.", reply_markup=get_events_kb())


@router.callback_query(F.data == "events_edit_content")
async def cb_events_edit_content(query: CallbackQuery):
    slots = await rq.get_all_events()
    buttons = [[InlineKeyboardButton(text=slot, callback_data=f"events_edit_content_sel|{slot}")]
               for slot, _ in slots]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="events_edit")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await query.message.edit_text("Выберите мероприятие для редактирования содержимого:", reply_markup=kb)
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
        f"Старое содержимое:\n<code>{old_content}</code>\nВведите новое содержимое:",
        parse_mode="HTML",
        reply_markup=kb
    )
    await query.answer()


@router.message(StateFilter(None),
                lambda message: admin_event_mode.get(message.from_user.id) == "edit_set_content")
async def msg_events_edit_set_content(message: Message):
    user_id = message.from_user.id
    if admin_event_mode.get(user_id) != "edit_set_content":
        return
    new_content = message.text.strip()
    old_date = admin_event_data[user_id]["old_date"]
    await rq.update_event_content_by_date(old_date, new_content)
    admin_event_mode.pop(user_id, None)
    admin_event_data.pop(user_id, None)
    await message.answer("Содержимое мероприятия обновлено.", reply_markup=get_events_kb())


@router.callback_query(F.data == "events_delete")
async def cb_events_delete(query: CallbackQuery):
    slots = await rq.get_all_events()
    buttons = [[InlineKeyboardButton(text=slot, callback_data=f"events_delete_sel|{slot}")]
               for slot, _ in slots]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="events_edit_start")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await query.message.edit_text("Выберите мероприятие для удаления:", reply_markup=kb)
    await query.answer()


@router.callback_query(F.data.startswith("events_delete_sel|"))
async def cb_events_delete_sel(query: CallbackQuery):
    _, slot = query.data.split("|", 1)
    event = await rq.get_event_by_date(slot)
    content = event.content if event else ""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Удалить", callback_data=f"events_delete_confirm|{slot}" )],
        [InlineKeyboardButton(text="⬅️ Отменить", callback_data="events_delete_cancel")]
    ])
    await query.message.edit_text(f"Удалить мероприятие?\n<code>{slot} - {content}</code>", parse_mode="HTML", reply_markup=kb)
    await query.answer()


@router.callback_query(F.data == "events_delete_cancel")
async def cb_events_delete_cancel(query: CallbackQuery):
    await query.message.edit_text("Удаление отменено.", reply_markup=get_events_kb())
    await query.answer()


@router.callback_query(F.data.startswith("events_delete_confirm|"))
async def cb_events_delete_confirm(query: CallbackQuery):
    _, slot = query.data.split("|", 1)
    await rq.delete_event_by_date(slot)
    await query.message.edit_text("Мероприятие удалено.", reply_markup=get_events_kb())
    await query.answer()


@router.message(Command("change_interview"))
async def cmd_change_interview(message: Message):
    await message.answer("Выберите действие с датами собеседований:", reply_markup=get_change_int_kb())


@router.callback_query(F.data == "change_int_add")
async def cb_change_int_add(query: CallbackQuery):
    admin_int_mode[query.from_user.id] = "add"
    await query.message.edit_text(
        "Введите новую дату в формате <b>ДД.ММ ЧЧ:ММ</b>, например `26.06 17:00`",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="change_interview_back")]
        ])
    )
    await query.answer()


@router.callback_query(F.data == "change_int_del")
async def cb_change_int_del(query: CallbackQuery):
    slots = await rq.get_interview_consultation_slots()
    if not slots:
        await query.answer("Слотов пока нет", show_alert=True)
        return await query.message.edit_text("Нет дат для удаления.", reply_markup=get_change_int_kb())

    buttons = [
        [InlineKeyboardButton(text=slot_text, callback_data=f"change_int_delete_{slot_id}")]
        for slot_id, slot_text in slots
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="change_interview_back")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await query.message.edit_text("Выберите дату для удаления:", reply_markup=kb)
    await query.answer()


@router.message(Command("int"))
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
            username_text = f"@{chat.username}" if chat.username else "(нет юзернейма)"
            fio = " ".join(filter(None, [user.surname, user.name, user.patronymic])) or "(ФИО не указано)"
            phone = user.phone_number or "(телефон не указан)"
            year = user.entry_year or "(год не указан)"
            lines.append(f"{idx}. {fio} | {phone} | {year} | {username_text}")
        text = f"Записанные на <b>{slot_text}</b>:\n" + "\n".join(lines)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="int_back")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "int_back")
async def cb_int_back(callback: CallbackQuery):
    await show_interview_slots_list(callback.message.edit_text)
    await callback.answer()


@router.callback_query(F.data.startswith("change_int_delete_"))
async def cb_change_int_delete(query: CallbackQuery):
    slot_id = int(query.data.split("_")[-1])
    await rq.delete_interview_slot(slot_id)
    await query.answer("Дата удалена")
    # Обновляем список удаления
    await cb_change_int_del(query)


@router.callback_query(F.data == "change_interview_back")
async def cb_change_interview_back(query: CallbackQuery):
    admin_int_mode.pop(query.from_user.id, None)
    await query.message.edit_text(
        "Выберите действие с датами собеседований:",
        reply_markup=get_change_int_kb()
    )
    await query.answer()


@router.message(lambda message: admin_int_mode.get(message.from_user.id) == "add")
async def handle_add_interview_slot(message: Message):
    if admin_int_mode.get(message.from_user.id) != "add":
        return

    text = message.text.strip()
    if not re.fullmatch(r"\d{2}\.\d{2} \d{2}:\d{2}", text):
        return await message.answer("Неверный формат. Введите, например, `26.06 17:00`.", parse_mode="Markdown")

    try:
        await rq.add_interview_slot(text)
        await message.answer(f"Дата «{text}» успешно добавлена.")
    except Exception:
        await message.answer("Ошибка: возможно, такая дата уже существует.")
    finally:
        admin_int_mode.pop(message.from_user.id, None)
        await message.answer("Выберите действие:", reply_markup=get_change_int_kb())


# кнопка Консультация
@router.callback_query(F.data == "consultation")
async def cb_consultation(callback: CallbackQuery):
    await callback.message.delete()
    await send_consultation_slots(callback.message.answer, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("slot_"))
async def cb_slot(callback: CallbackQuery):
    slot_id = int(callback.data.split("_", 1)[1])
    tg_id = callback.from_user.id

    chosen = await rq.get_slot_by_id(slot_id)
    current = await rq.get_user_slot(tg_id)

    if current == chosen:
        await rq.clear_user_slot(tg_id)
        await callback.answer("Запись отменена")
    else:
        await rq.set_user_slot(tg_id, chosen)
        await callback.answer(f"Вы записаны на {chosen}")

    await send_consultation_slots(callback.message.edit_text, tg_id)


# кнопка Связь с наставником
@router.callback_query(F.data == "mentor")
async def cb_mentor(callback: CallbackQuery):
    await callback.message.delete()
    await send_mentor(callback.message.answer)
    await callback.answer()


# кнопка Календарь
@router.callback_query(F.data == "events")
async def cb_events(callback: CallbackQuery):
    await callback.message.delete()
    await send_events(callback.message.answer)
    await callback.answer()


@router.message(Command("change_cons"))
async def cmd_change_cons(message: Message):
    await message.answer("Выберите действие с датами консультаций:", reply_markup=get_change_cons_kb())


@router.callback_query(F.data == "change_cons_add")
async def cb_change_cons_add(query: CallbackQuery):
    admin_cons_mode[query.from_user.id] = "add"
    await query.message.edit_text(
        "Введите новую дату в формате <b>ДД.ММ ЧЧ:ММ</b>, например `26.06 17:00`",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Отмена", callback_data="change_cons_back")]]
        )
    )
    await query.answer()


@router.callback_query(F.data == "change_cons_del")
async def cb_change_cons_del(query: CallbackQuery):
    slots = await rq.get_consultation_slots()
    if not slots:
        await query.answer("Слотов пока нет", show_alert=True)
        return await query.message.edit_text("Нет дат для удаления.", reply_markup=get_change_cons_kb())

    buttons = [
        [InlineKeyboardButton(text=slot_text, callback_data=f"change_cons_delete_{slot_id}")]
        for slot_id, slot_text in slots
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="change_cons_back")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await query.message.edit_text("Выберите дату для удаления:", reply_markup=kb)
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
    await query.message.edit_text("Выберите действие с датами консультаций:", reply_markup=get_change_cons_kb())
    await query.answer()


@router.message(StateFilter(None),
                lambda message: admin_cons_mode.get(message.from_user.id) == "add")
async def handle_add_slot(message: Message):
    user_id = message.from_user.id
    if admin_cons_mode.get(user_id) != "add":
        return

    text = message.text.strip()
    if not re.fullmatch(r"\d{2}\.\d{2} \d{2}:\d{2}", text):
        return await message.answer("Неверный формат. Введите, например, `26.06 17:00`.", parse_mode="Markdown")

    try:
        await rq.add_consultation_slot(text)
        await message.answer(f"Дата «{text}» успешно добавлена.")
    except Exception:
        await message.answer("Ошибка: возможно, такая дата уже существует.")
    finally:
        admin_cons_mode.pop(user_id, None)
        await message.answer("Выберите действие:", reply_markup=get_change_cons_kb())


@router.message(Command("cons"))
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
            username_text = f"@{chat.username}" if chat.username else "(нет юзернейма)"
            fio = " ".join(filter(None, [user.surname, user.name, user.patronymic])) or "(ФИО не указано)"
            phone = user.phone_number or "(телефон не указан)"
            year = user.entry_year or "(год не указан)"

            lines.append(f"{idx}. {fio} | {phone} | {year} | {username_text}")

        text = f"Записанные на <b>{slot_text}</b>:\n" + "\n".join(lines)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="cons_back")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "cons_back")
async def cb_cons_back(callback: CallbackQuery):
    await show_slots_list(callback.message.edit_text)
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
            "⚠️ Пожалуйста, введите ФИО целиком через пробел, например:\n"
            "Иванов Иван Иванович"
        )
        return

    surname, name, patronymic = parts
    await state.update_data(surname=surname, name=name, patronymic=patronymic)
    await state.set_state(FSMRegistration.entry_year)

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
    await callback.message.edit_text("Введите ваш <b>номер телефона</b> в формате +7XXXXXXXXXX или укажите прочерк:", parse_mode="HTML")
    await callback.answer()


@router.message(FSMRegistration.phone)
async def reg_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not re.fullmatch(r"\+7\d{3}\d{3}\d{2}\d{2}", phone) and phone != "-":
        await message.answer("⚠️ Неверный формат. Попробуйте ещё раз: +7XXXXXXXXXX\nИли укажите -")
        return
    await state.update_data(phone=phone)

    data = await state.get_data()
    await rq.set_fio(message.from_user.id, data["surname"], data["name"], data["patronymic"])
    await rq.set_entry_year(message.from_user.id, data["entry_year"])
    await rq.set_phone_number(message.from_user.id, data["phone"])
    await state.clear()

    await message.answer("✅ Регистрация завершена!")
    await send_main_menu(message)


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

    prompt = await callback.message.edit_text("Введите новое <b>ФИО</b> через пробел:", parse_mode="HTML")
    user_prompt_message_id[user_id] = prompt.message_id
    await callback.answer()


@router.callback_query(F.data == "edit_phone")
async def cb_edit_phone_number(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_edit_mode[user_id] = "phone"

    prompt = await callback.message.edit_text("Введите ваш <b>номер телефона</b> в формате +7XXXXXXXXXX:", parse_mode="HTML")
    user_prompt_message_id[user_id] = prompt.message_id
    await callback.answer()


@router.callback_query(F.data == "edit_year")
async def cb_edit_year(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_edit_mode[user_id] = "year"

    await callback.message.edit_text("Выберите год поступления:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="2023", callback_data="year_2023")],
        [InlineKeyboardButton(text="2024", callback_data="year_2024")],
        [InlineKeyboardButton(text="2025", callback_data="year_2025")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="edit_profile")]
    ]))
    await callback.answer()


@router.callback_query(F.data.startswith("year_"))
async def cb_select_year(callback: CallbackQuery):
    user_id = callback.from_user.id
    year = callback.data.split("_")[1]

    if year not in ("2023", "2024", "2025"):
        return

    await rq.set_entry_year(user_id, int(year))

    user_edit_mode.pop(user_id, None)
    user_prompt_message_id.pop(user_id, None)

    await callback.message.delete()

    await callback.message.answer(
        "Что вы хотите изменить?",
        reply_markup=get_edit_profile_kb()
    )
    await callback.answer()


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
            err = await message.answer("⚠️ Введите ФИО в формате:\nФамилия Имя Отчество")
            user_error_message_id[user_id] = err.message_id
            return
        surname, name, patronymic = parts
        await rq.set_fio(user_id, surname, name, patronymic)

    elif mode == "phone":
        phone = message.text.strip()
        if not re.fullmatch(r"\+7\d{3}\d{3}\d{2}\d{2}", phone) and phone != "-":
            await message.delete()
            err = await message.answer("⚠️ Неверный формат. Попробуйте ещё раз: +7XXXXXXXXXX\nИли укажите -")
            user_error_message_id[user_id] = err.message_id
            return
        await rq.set_phone_number(user_id, phone)

    user_edit_mode.pop(user_id, None)
    user_prompt_message_id.pop(user_id, None)

    await message.delete()
    if prompt_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_id)
        except:
            pass

    err_id = user_error_message_id.pop(user_id, None)
    if err_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=err_id)
        except:
            pass

    await message.answer(
        "Что вы хотите изменить?",
        reply_markup=get_edit_profile_kb()
    )
