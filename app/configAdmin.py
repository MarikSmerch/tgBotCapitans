import os
from dotenv import load_dotenv

load_dotenv()


def parse_admins(env_value: str) -> list[int]:
    return [int(uid.strip()) for uid in env_value.split(",") if uid.strip().isdigit()]


ADMINS = parse_admins(os.getenv("ADMINS", ""))


def is_admin(user_id: int) -> bool:
    return user_id in ADMINS
