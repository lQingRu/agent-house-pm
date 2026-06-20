import os
from dataclasses import dataclass
from typing import Optional


class ConfigError(Exception):
    pass


@dataclass
class Config:
    telegram_bot_token: str
    db_path: str
    group_chat_id: int
    reminder_job_time: str
    log_level: str
    google_service_account_key_path: Optional[str]
    google_calendar_id: Optional[str]


def get_config() -> Config:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ConfigError("TELEGRAM_BOT_TOKEN is required")

    group_chat_id_raw = os.environ.get("GROUP_CHAT_ID")
    if not group_chat_id_raw:
        raise ConfigError("GROUP_CHAT_ID is required")

    db_path = os.environ.get("DB_PATH", "data/house.db")
    reminder_job_time = os.environ.get("REMINDER_JOB_TIME", "08:00")
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    google_service_account_key_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY_PATH")
    google_calendar_id = os.environ.get("GOOGLE_CALENDAR_ID")

    return Config(
        telegram_bot_token=token,
        db_path=db_path,
        group_chat_id=int(group_chat_id_raw),
        reminder_job_time=reminder_job_time,
        log_level=log_level,
        google_service_account_key_path=google_service_account_key_path,
        google_calendar_id=google_calendar_id,
    )
