from aiogram.fsm.state import StatesGroup, State


class FSMRegistration(StatesGroup):
    surname = State()
    name = State()
    patronymic = State()
    entry_year = State()
    phone = State()
    social_link = State()
