import os
import pytest
from bot.config import get_config, ConfigError


def test_get_config_reads_required_vars(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-abc")
    monkeypatch.setenv("DB_PATH", "/tmp/test.db")
    monkeypatch.setenv("GROUP_CHAT_ID", "-100123456")

    cfg = get_config()

    assert cfg.telegram_bot_token == "token-abc"
    assert cfg.db_path == "/tmp/test.db"
    assert cfg.group_chat_id == -100123456


def test_get_config_raises_when_token_missing(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("DB_PATH", "/tmp/test.db")
    monkeypatch.setenv("GROUP_CHAT_ID", "-100123456")

    with pytest.raises(ConfigError):
        get_config()


def test_get_config_raises_when_group_chat_id_missing(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-abc")
    monkeypatch.setenv("DB_PATH", "/tmp/test.db")
    monkeypatch.delenv("GROUP_CHAT_ID", raising=False)

    with pytest.raises(ConfigError):
        get_config()


def test_get_config_db_path_defaults_to_data_dir(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-abc")
    monkeypatch.setenv("GROUP_CHAT_ID", "-100123456")
    monkeypatch.delenv("DB_PATH", raising=False)

    cfg = get_config()

    assert cfg.db_path.endswith(".db")


def test_get_config_reminder_job_time_defaults_to_0800(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-abc")
    monkeypatch.setenv("DB_PATH", "/tmp/test.db")
    monkeypatch.setenv("GROUP_CHAT_ID", "-100123456")

    cfg = get_config()

    assert cfg.reminder_job_time == "08:00"
