from aiogram.fsm.state import StatesGroup, State


class FSMRegistration(StatesGroup):
    full_name = State()
    entry_year = State()
    phone = State()
    city = State()
    direction = State()
