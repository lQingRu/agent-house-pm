# MVP Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add edit/delete, submitter attribution, smart reminder schedule, and /config command to the household expiry bot.

**Architecture:** Four independent improvements that each touch one or two files; tackled in dependency order (pure logic first, then wiring). ConversationHandler drives the multi-step edit flow so the main DM message handler never needs to know about it.

**Tech Stack:** python-telegram-bot v21 (async), SQLite, dateparser, pytest-asyncio

---

## File Map

| File | Status | Responsibility |
|---|---|---|
| `bot/parser.py` | Modify | Extract `parse_date()` helper for reuse in edit flow |
| `bot/handlers.py` | Modify | Smart schedule HTML in add-item confirmation |
| `bot/reminders.py` | Modify | Add `submitted_by` to `ReminderDue` |
| `bot/scheduler.py` | Modify | Add submitter name to reminder message |
| `bot/commands.py` | Modify | `build_list_text` names param, `config_command`, DM list keyboard |
| `bot/edit.py` | **Create** | DB functions + callback/conversation handlers for edit/delete |
| `bot/run_reminders.py` | Modify | Fix async pattern, add submitter name |
| `bot/__main__.py` | Modify | Register `/config`, edit/delete handlers, ConversationHandler |
| `tests/test_schedule_message.py` | **Create** | Unit tests for smart schedule formatter |
| `tests/test_edit.py` | **Create** | Unit tests for edit/delete DB functions |
| `tests/test_commands.py` | Modify | Update for new `build_list_text` signature |

---

## Task 1: Extract `parse_date` helper in `bot/parser.py`

**Files:**
- Modify: `bot/parser.py`
- Test: `tests/test_parser.py`

The edit flow needs to parse a bare date string (e.g. "15 Jul 2026") that the user sends. Extract this from the existing `dateparser.parse` call so both `parse_item_message` and the edit handler can share it.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_parser.py`:

```python
from datetime import date as _date
from bot.parser import parse_date

def test_parse_date_standard_format():
    result = parse_date("15 Jul 2026")
    assert result == _date(2026, 7, 15)

def test_parse_date_iso_format():
    result = parse_date("2026-07-15")
    assert result == _date(2026, 7, 15)

def test_parse_date_month_year_only():
    result = parse_date("Jul 2026")
    assert result is not None
    assert result.year == 2026
    assert result.month == 7

def test_parse_date_invalid_returns_none():
    assert parse_date("banana") is None

def test_parse_date_past_date_returns_none():
    assert parse_date("1 Jan 2020") is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/qingru/Documents/workspace/Projects/telegram-bots/house-pm
.venv/bin/pytest tests/test_parser.py -k "test_parse_date" -v
```

Expected: `ImportError` — `parse_date` not found.

- [ ] **Step 3: Implement `parse_date` and update `parse_item_message` to use it**

Replace the content of `bot/parser.py`:

```python
import re
from dataclasses import dataclass
from datetime import date
from typing import Optional

import dateparser


@dataclass
class ParseResult:
    name: str
    expiry_date: date
    category: Optional[str]


_DATE_KEYWORDS = re.compile(
    r"\b(expires?|expiry\s+date|best\s+before|use\s+by|bb)\b",
    re.IGNORECASE,
)
_CATEGORY_PARENS = re.compile(r"\(([^)]+)\)")


def parse_date(text: str) -> Optional[date]:
    """Parse a bare date string; returns None for past or unparseable dates."""
    parsed = dateparser.parse(
        text,
        settings={"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False},
    )
    if parsed is None:
        return None
    result = parsed.date()
    if result < date.today():
        return None
    return result


def parse_item_message(text: str) -> Optional[ParseResult]:
    category_match = _CATEGORY_PARENS.search(text)
    category = category_match.group(1).strip() if category_match else None
    clean = _CATEGORY_PARENS.sub("", text).strip()

    parts = _DATE_KEYWORDS.split(clean, maxsplit=1)
    name_part = parts[0].strip().rstrip(",").strip()

    date_text = parts[-1].strip() if len(parts) > 1 else clean

    expiry = parse_date(date_text)
    if expiry is None or not name_part:
        return None

    return ParseResult(name=name_part, expiry_date=expiry, category=category)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_parser.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add bot/parser.py tests/test_parser.py
git commit -m "refactor: extract parse_date helper from parse_item_message"
```

---

## Task 2: Smart reminder schedule in add-item confirmation

**Files:**
- Modify: `bot/handlers.py`
- Create: `tests/test_schedule_message.py`

When an item is added via DM, the bot now shows which reminder thresholds will actually fire, with actual dates. Skipped thresholds (fire date already past) are struck through using HTML.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_schedule_message.py`:

```python
from datetime import date, timedelta
from bot.handlers import build_reminder_schedule_html

today = date.today()


def test_all_thresholds_fire_when_expiry_is_far():
    expiry = today + timedelta(days=10)
    html = build_reminder_schedule_html(expiry)
    assert "<s>" not in html
    assert "7 days" in html
    assert "3 days" in html
    assert "on the day" in html


def test_7d_and_3d_struck_when_expiry_is_in_2_days():
    expiry = today + timedelta(days=2)
    html = build_reminder_schedule_html(expiry)
    assert html.count("<s>") == 2
    assert "<s>7 days</s>" in html
    assert "<s>3 days</s>" in html
    assert "✓ on the day" in html


def test_only_7d_struck_when_expiry_is_in_5_days():
    expiry = today + timedelta(days=5)
    html = build_reminder_schedule_html(expiry)
    assert html.count("<s>") == 1
    assert "<s>7 days</s>" in html
    assert "✓ 3 days" in html
    assert "✓ on the day" in html


def test_all_struck_when_expiry_is_today():
    expiry = today
    html = build_reminder_schedule_html(expiry)
    # fire dates for 7d and 3d are in the past; on-the-day fires today
    assert "<s>7 days</s>" in html
    assert "<s>3 days</s>" in html
    assert "✓ on the day" in html
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/test_schedule_message.py -v
```

Expected: `ImportError` — `build_reminder_schedule_html` not found.

- [ ] **Step 3: Implement `build_reminder_schedule_html` and update the confirmation message**

Replace `bot/handlers.py` with:

```python
import html as _html
import logging
from datetime import date, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from bot.parser import parse_item_message
from bot.ingestion import store_expiry_item

logger = logging.getLogger(__name__)

_THRESHOLDS = [("7 days", 7), ("3 days", 3), ("on the day", 0)]


def build_reminder_schedule_html(expiry_date: date) -> str:
    today = date.today()
    parts = []
    for label, days in _THRESHOLDS:
        fire_date = expiry_date - timedelta(days=days)
        if fire_date < today:
            parts.append(f"<s>{label}</s>")
        else:
            date_display = fire_date.strftime("%-d %b")
            parts.append(f"✓ {label} ({date_display})")
    return ", ".join(parts)


async def dm_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type != "private":
        return

    try:
        text = update.message.text or ""
        result = parse_item_message(text)

        if result is None:
            await update.message.reply_text(
                "I couldn't find an expiry date in your message.\n\n"
                "Try something like:\n"
                "`Panadol (medicine) expires 15 Jul 2026`\n"
                "`Milk best before 25 Jun 2026`\n\n"
                "Or send /help to see all commands.",
                parse_mode="Markdown",
            )
            return

        cfg = context.bot_data["config"]
        store_expiry_item(
            db_path=cfg.db_path,
            group_chat_id=cfg.group_chat_id,
            submitted_by=update.effective_user.id,
            name=result.name,
            category=result.category,
            expiry_date=result.expiry_date,
        )
        logger.info("item_submitted name=%s submitted_by=%s", result.name, update.effective_user.id)

        category_str = f" ({_html.escape(result.category)})" if result.category else ""
        date_str = result.expiry_date.strftime("%-d %b %Y")
        schedule_html = build_reminder_schedule_html(result.expiry_date)

        await update.message.reply_text(
            f"Got it! I've noted <b>{_html.escape(result.name)}</b>{category_str} — expires <b>{date_str}</b>.\n\n"
            f"Reminders: {schedule_html}",
            parse_mode="HTML",
        )
    except Exception:
        logger.error("Unhandled exception in dm_message_handler", exc_info=True)
        await update.message.reply_text("Something went wrong — please try again.")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_schedule_message.py tests/test_ingestion.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add bot/handlers.py tests/test_schedule_message.py
git commit -m "feat: smart reminder schedule in add-item confirmation"
```

---

## Task 3: Add `submitted_by` to `ReminderDue` and update scheduler

**Files:**
- Modify: `bot/reminders.py`
- Modify: `bot/scheduler.py`
- Test: `tests/test_reminders.py`

The `ReminderDue` dataclass gains a `submitted_by` field. The scheduler uses it to resolve a display name and include "Added by X" in the reminder message.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_reminders.py`:

```python
def test_get_due_reminders_includes_submitted_by(db_path):
    add_item(db_path, "Panadol", 7, "medicine")
    dues = get_due_reminders(db_path, today=date.today())
    assert len(dues) == 1
    assert dues[0].submitted_by == 42
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_reminders.py::test_get_due_reminders_includes_submitted_by -v
```

Expected: `AttributeError` — `ReminderDue` has no `submitted_by`.

- [ ] **Step 3: Add `submitted_by` to `ReminderDue` and update the DB query**

Replace `bot/reminders.py` with:

```python
import sqlite3
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

_THRESHOLDS = {"7d": 7, "3d": 3, "0d": 0}


@dataclass
class ReminderDue:
    item_id: int
    item_name: str
    category: Optional[str]
    expiry_date: date
    level: str
    submitted_by: int


def get_due_reminders(db_path: str, today: date) -> list[ReminderDue]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    items = conn.execute(
        "SELECT id, name, category, expiry_date, submitted_by FROM expiry_items WHERE dismissed_at IS NULL"
    ).fetchall()

    due = []
    for item in items:
        expiry = date.fromisoformat(item["expiry_date"])
        for level, days in _THRESHOLDS.items():
            if expiry - timedelta(days=days) != today:
                continue
            already_sent = conn.execute(
                "SELECT 1 FROM reminder_log WHERE item_id = ? AND level = ?",
                (item["id"], level),
            ).fetchone()
            if already_sent:
                continue
            due.append(ReminderDue(
                item_id=item["id"],
                item_name=item["name"],
                category=item["category"],
                expiry_date=expiry,
                level=level,
                submitted_by=item["submitted_by"],
            ))

    conn.close()
    return due


def record_reminder_sent(db_path: str, item_id: int, level: str, message_id: int) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO reminder_log (item_id, level, message_id) VALUES (?, ?, ?)",
        (item_id, level, message_id),
    )
    conn.execute(
        "UPDATE expiry_items SET last_reminder_message_id = ? WHERE id = ?",
        (message_id, item_id),
    )
    conn.commit()
    conn.close()
```

- [ ] **Step 4: Update `bot/scheduler.py` to resolve and show submitter name**

Replace `bot/scheduler.py` with:

```python
import logging
from datetime import date

from telegram.ext import ContextTypes

from bot.reminders import get_due_reminders, record_reminder_sent

logger = logging.getLogger(__name__)


async def _resolve_name(bot, user_id: int) -> str:
    try:
        chat = await bot.get_chat(user_id)
        return chat.first_name or chat.username or str(user_id)
    except Exception:
        return str(user_id)


async def run_reminder_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = context.bot_data["config"]
    try:
        today = date.today()
        dues = get_due_reminders(cfg.db_path, today)
    except Exception:
        logger.error("Reminder job failed to fetch due reminders", exc_info=True)
        return

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    for due in dues:
        category_str = f" ({due.category})" if due.category else ""
        days_remaining = (due.expiry_date - today).days
        if days_remaining == 0:
            days_str = "expires today"
        else:
            days_str = f"expires in {days_remaining} days ({due.expiry_date.strftime('%-d %b %Y')})"

        submitter_name = await _resolve_name(context.bot, due.submitted_by)

        text = (
            f"⏰ Expiry reminder — {due.item_name}{category_str}\n"
            f"{days_str.capitalize()}\n"
            f"Added by {submitter_name}"
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Dismiss ✓", callback_data=f"dismiss:{due.item_id}")]]
        )
        msg = await context.bot.send_message(
            chat_id=cfg.group_chat_id,
            text=text,
            reply_markup=keyboard,
        )
        record_reminder_sent(cfg.db_path, due.item_id, due.level, msg.message_id)
        logger.info("Sent %s reminder for item %d", due.level, due.item_id)
```

- [ ] **Step 5: Run all reminder tests**

```bash
.venv/bin/pytest tests/test_reminders.py -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add bot/reminders.py bot/scheduler.py tests/test_reminders.py
git commit -m "feat: add submitted_by to ReminderDue and show submitter in reminders"
```

---

## Task 4: `/config` command

**Files:**
- Modify: `bot/commands.py`
- Modify: `bot/__main__.py`

Add a `/config` command showing reminder time and schedule. Update `/help` to mention it.

- [ ] **Step 1: Add `config_command` to `bot/commands.py`**

Open `bot/commands.py`. Replace the `_HELP_TEXT` constant and add `config_command` after `add_command`:

```python
_HELP_TEXT = (
    "Here's what I can do:\n\n"
    "*Add an item* — just send me a message like:\n"
    "  `Panadol (medicine) expires 15 Jul 2026`\n"
    "  `Milk best before 25 Jun 2026`\n"
    "  `Sunscreen (skincare) use by 2027-03`\n\n"
    "*/add* — show this add reminder\n"
    "*/list* — list all tracked items\n"
    "*/upcoming* — items expiring in the next 7 days\n"
    "*/config* — show current bot settings\n"
    "*/help* — show this message"
)
```

Add after `add_command`:

```python
async def config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = context.bot_data["config"]
    lines = [
        "⚙️ <b>Bot configuration</b>",
        "",
        f"Reminder time: {cfg.reminder_job_time} daily",
        "Reminder schedule: 7 days, 3 days, on the day",
    ]
    if cfg.google_calendar_id and cfg.google_service_account_key_path:
        lines.append("Google Calendar: connected ✅")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
```

- [ ] **Step 2: Register `/config` in `bot/__main__.py`**

In `bot/__main__.py`, add to the import line:

```python
from bot.commands import list_command, upcoming_command, start_command, help_command, add_command, config_command
```

Add after the existing `CommandHandler("upcoming", upcoming_command)` line:

```python
app.add_handler(CommandHandler("config", config_command))
```

- [ ] **Step 3: Run existing tests to confirm nothing broke**

```bash
.venv/bin/pytest tests/ -v --tb=short
```

Expected: all existing tests pass.

- [ ] **Step 4: Commit**

```bash
git add bot/commands.py bot/__main__.py
git commit -m "feat: add /config command showing reminder time and schedule"
```

---

## Task 5: Show who added an item in `/list`

**Files:**
- Modify: `bot/commands.py`
- Modify: `tests/test_commands.py`

`build_list_text` gains an optional `names: dict[int, str]` parameter. When provided, the "added by" attribution appears next to each item. `list_command` resolves names from Telegram before building the text.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_commands.py`:

```python
def test_build_list_text_shows_submitter_when_names_provided(db_path):
    add_item(db_path, "Panadol", 7)  # submitted_by=42 per the fixture
    text = build_list_text(db_path, names={42: "Alice"})
    assert "added by Alice" in text


def test_build_list_text_omits_submitter_when_names_not_provided(db_path):
    add_item(db_path, "Panadol", 7)
    text = build_list_text(db_path)
    assert "added by" not in text
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/test_commands.py -k "submitter" -v
```

Expected: `TypeError` — `build_list_text()` got unexpected keyword argument `names`.

- [ ] **Step 3: Update `build_list_text` to accept and use `names`**

In `bot/commands.py`, replace the `build_list_text` function:

```python
def build_list_text(db_path: str, names: dict[int, str] | None = None) -> str:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT name, category, expiry_date, dismissed_at, submitted_by FROM expiry_items ORDER BY expiry_date"
    ).fetchall()
    conn.close()

    if not rows:
        return "No items tracked yet."

    lines = []
    for r in rows:
        cat = f" ({r['category']})" if r["category"] else ""
        status = "✅ Resolved" if r["dismissed_at"] else f"expires {r['expiry_date']}"
        by = ""
        if names and r["submitted_by"] in names:
            by = f" (added by {names[r['submitted_by']]})"
        lines.append(f"• {r['name']}{cat}{by} — {status}")
    return "\n".join(lines)
```

- [ ] **Step 4: Update `list_command` to resolve names before building text**

Replace the `list_command` function in `bot/commands.py`:

```python
async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = context.bot_data["config"]

    conn = sqlite3.connect(cfg.db_path)
    conn.row_factory = sqlite3.Row
    user_id_rows = conn.execute(
        "SELECT DISTINCT submitted_by FROM expiry_items"
    ).fetchall()
    conn.close()

    names: dict[int, str] = {}
    for row in user_id_rows:
        uid = row["submitted_by"]
        try:
            chat = await context.bot.get_chat(uid)
            names[uid] = chat.first_name or chat.username or str(uid)
        except Exception:
            names[uid] = str(uid)

    text = build_list_text(cfg.db_path, names=names)
    await update.message.reply_text(text)
```

- [ ] **Step 5: Run tests**

```bash
.venv/bin/pytest tests/test_commands.py -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add bot/commands.py tests/test_commands.py
git commit -m "feat: show who added each item in /list output"
```

---

## Task 6: DB functions for edit/delete in `bot/edit.py`

**Files:**
- Create: `bot/edit.py`
- Create: `tests/test_edit.py`

Pure DB layer — no Telegram imports. Functions: `get_item`, `update_item_name`, `update_item_category`, `update_item_expiry`, `delete_item`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_edit.py`:

```python
import sqlite3
import tempfile
import os
from datetime import date, timedelta
import pytest
from bot.db import init_db
from bot.ingestion import store_expiry_item
from bot.edit import get_item, update_item_name, update_item_category, update_item_expiry, delete_item


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    init_db(path)
    yield path
    os.unlink(path)


def add_item(db_path, name="Panadol", days=7):
    expiry = date.today() + timedelta(days=days)
    return store_expiry_item(db_path, -100123, 42, name, "medicine", expiry)


def test_get_item_returns_dict_for_existing_item(db_path):
    item_id = add_item(db_path, "Panadol")
    item = get_item(db_path, item_id)
    assert item is not None
    assert item["name"] == "Panadol"
    assert item["id"] == item_id


def test_get_item_returns_none_for_missing_id(db_path):
    assert get_item(db_path, 9999) is None


def test_get_item_returns_none_for_dismissed_item(db_path):
    item_id = add_item(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE expiry_items SET dismissed_at = datetime('now') WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    assert get_item(db_path, item_id) is None


def test_update_item_name_changes_name(db_path):
    item_id = add_item(db_path, "Panadol")
    update_item_name(db_path, item_id, "Panadol Extra")
    item = get_item(db_path, item_id)
    assert item["name"] == "Panadol Extra"


def test_update_item_category_changes_category(db_path):
    item_id = add_item(db_path)
    update_item_category(db_path, item_id, "food")
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT category FROM expiry_items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    assert row[0] == "food"


def test_update_item_category_accepts_none(db_path):
    item_id = add_item(db_path)
    update_item_category(db_path, item_id, None)
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT category FROM expiry_items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    assert row[0] is None


def test_update_item_expiry_changes_date(db_path):
    item_id = add_item(db_path)
    new_date = date.today() + timedelta(days=30)
    update_item_expiry(db_path, item_id, new_date)
    item = get_item(db_path, item_id)
    assert item["expiry_date"] == new_date.isoformat()


def test_delete_item_removes_row(db_path):
    item_id = add_item(db_path)
    delete_item(db_path, item_id)
    assert get_item(db_path, item_id) is None
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT id FROM expiry_items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    assert row is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/test_edit.py -v
```

Expected: `ModuleNotFoundError` — `bot.edit` not found.

- [ ] **Step 3: Create `bot/edit.py` with DB functions**

```python
import sqlite3
from datetime import date
from typing import Optional


def get_item(db_path: str, item_id: int) -> Optional[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id, name, category, expiry_date FROM expiry_items WHERE id = ? AND dismissed_at IS NULL",
        (item_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_item_name(db_path: str, item_id: int, new_name: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE expiry_items SET name = ? WHERE id = ?", (new_name, item_id))
    conn.commit()
    conn.close()


def update_item_category(db_path: str, item_id: int, new_category: Optional[str]) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE expiry_items SET category = ? WHERE id = ?", (new_category, item_id))
    conn.commit()
    conn.close()


def update_item_expiry(db_path: str, item_id: int, new_expiry: date) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE expiry_items SET expiry_date = ? WHERE id = ?",
        (new_expiry.isoformat(), item_id),
    )
    conn.commit()
    conn.close()


def delete_item(db_path: str, item_id: int) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM expiry_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/pytest tests/test_edit.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add bot/edit.py tests/test_edit.py
git commit -m "feat: add DB functions for edit/delete in bot/edit.py"
```

---

## Task 7: Edit/delete callback handlers and ConversationHandler

**Files:**
- Modify: `bot/edit.py` (add handlers)
- Modify: `bot/__main__.py` (register handlers)

Add Telegram callback handlers for the edit flow (ConversationHandler) and delete flow (plain callbacks) to `bot/edit.py`. Wire them up in `__main__.py`.

- [ ] **Step 1: Add callback handlers to `bot/edit.py`**

First, add these imports at the top of `bot/edit.py` (alongside the existing `sqlite3` / `datetime` imports):

```python
import html as _html
import logging

import dateparser
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

logger = logging.getLogger(__name__)
```

Then append the following constants and functions at the **bottom** of `bot/edit.py` (after the DB functions):

```python
EDIT_FIELD_SELECT = 0
EDIT_VALUE_AWAIT = 1


async def edit_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    item_id = int(query.data.split(":", 1)[1])
    cfg = context.bot_data["config"]
    item = get_item(cfg.db_path, item_id)
    if not item:
        await query.edit_message_text("Item not found or already deleted.")
        return ConversationHandler.END

    context.user_data["edit_item_id"] = item_id
    context.user_data["edit_item_name"] = item["name"]

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Name", callback_data=f"edit_field:{item_id}:name"),
            InlineKeyboardButton("Category", callback_data=f"edit_field:{item_id}:category"),
            InlineKeyboardButton("Expiry date", callback_data=f"edit_field:{item_id}:expiry_date"),
        ],
        [InlineKeyboardButton("Cancel", callback_data=f"edit_cancel:{item_id}")],
    ])
    await query.edit_message_text(
        f"What would you like to change about <b>{_html.escape(item['name'])}</b>?",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    return EDIT_FIELD_SELECT


async def edit_field_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":", 2)  # edit_field:<item_id>:<field>
    item_id = int(parts[1])
    field = parts[2]

    context.user_data["edit_item_id"] = item_id
    context.user_data["edit_field"] = field

    prompts = {
        "name": "Send the new name (or /cancel to abort).",
        "category": "Send the new category, e.g. medicine, food (or /cancel to abort).",
        "expiry_date": "Send the new expiry date, e.g. 15 Jul 2026 (or /cancel to abort).",
    }
    await query.edit_message_text(prompts[field])
    return EDIT_VALUE_AWAIT


async def edit_value_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cfg = context.bot_data["config"]
    item_id = context.user_data["edit_item_id"]
    field = context.user_data["edit_field"]
    old_name = context.user_data.get("edit_item_name", "item")
    new_value = update.message.text.strip()

    if field == "name":
        update_item_name(cfg.db_path, item_id, new_value)
        await update.message.reply_text(f"Updated! {_html.escape(old_name)} → {_html.escape(new_value)}", parse_mode="HTML")

    elif field == "category":
        update_item_category(cfg.db_path, item_id, new_value if new_value else None)
        await update.message.reply_text(f"Category updated to: {_html.escape(new_value)}", parse_mode="HTML")

    elif field == "expiry_date":
        parsed = dateparser.parse(
            new_value,
            settings={"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False},
        )
        if parsed is None or parsed.date() < date.today():
            await update.message.reply_text(
                "Couldn't parse that date. Try: 15 Jul 2026, 2026-07-15, Jul 2026.\n"
                "Send a date or /cancel to abort."
            )
            return EDIT_VALUE_AWAIT
        update_item_expiry(cfg.db_path, item_id, parsed.date())
        await update.message.reply_text(
            f"Expiry date updated to: {parsed.date().strftime('%-d %b %Y')}"
        )

    context.user_data.clear()
    return ConversationHandler.END


async def edit_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Edit cancelled.")
    context.user_data.clear()
    return ConversationHandler.END


async def edit_cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Edit cancelled.")
    context.user_data.clear()
    return ConversationHandler.END


def build_edit_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_start_callback, pattern=r"^edit:\d+$")],
        states={
            EDIT_FIELD_SELECT: [
                CallbackQueryHandler(edit_field_select_callback, pattern=r"^edit_field:\d+:(name|category|expiry_date)$"),
                CallbackQueryHandler(edit_cancel_callback, pattern=r"^edit_cancel:\d+$"),
            ],
            EDIT_VALUE_AWAIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, edit_value_receive),
            ],
        },
        fallbacks=[CommandHandler("cancel", edit_cancel_command)],
        per_message=False,
    )


async def delete_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    item_id = int(query.data.split(":", 1)[1])
    cfg = context.bot_data["config"]
    item = get_item(cfg.db_path, item_id)
    if not item:
        await query.edit_message_text("Item not found or already deleted.")
        return
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Yes, delete", callback_data=f"delete_confirm:{item_id}"),
        InlineKeyboardButton("Cancel", callback_data=f"delete_cancel:{item_id}"),
    ]])
    await query.edit_message_text(
        f"Delete <b>{_html.escape(item['name'])}</b>? This can't be undone.",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def delete_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    item_id = int(query.data.split(":", 1)[1])
    cfg = context.bot_data["config"]
    item = get_item(cfg.db_path, item_id)
    name = item["name"] if item else "item"
    delete_item(cfg.db_path, item_id)
    await query.edit_message_text(f"✅ {_html.escape(name)} deleted.", parse_mode="HTML")


async def delete_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Deletion cancelled.")
```

- [ ] **Step 2: Register handlers in `bot/__main__.py`**

Add to the imports in `bot/__main__.py`:

```python
from bot.edit import build_edit_conversation_handler, delete_start_callback, delete_confirm_callback, delete_cancel_callback
```

Add these handlers **before** the `dm_message_handler` registration (ConversationHandler must be registered first to capture text messages during edit flow):

```python
app.add_handler(build_edit_conversation_handler())
app.add_handler(CallbackQueryHandler(delete_start_callback, pattern=r"^delete:\d+$"))
app.add_handler(CallbackQueryHandler(delete_confirm_callback, pattern=r"^delete_confirm:\d+$"))
app.add_handler(CallbackQueryHandler(delete_cancel_callback, pattern=r"^delete_cancel:\d+$"))
```

The existing `dm_message_handler` line must appear **after** these four lines.

- [ ] **Step 3: Run all tests**

```bash
.venv/bin/pytest tests/ -v --tb=short
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add bot/edit.py bot/__main__.py
git commit -m "feat: add edit/delete conversation handler for DM item management"
```

---

## Task 8: DM `/list` with inline edit/delete buttons

**Files:**
- Modify: `bot/commands.py`
- Modify: `bot/__main__.py` (already has the right imports from Task 7)

When `/list` is called from a private DM, the response includes an inline keyboard with `[✏️ Name]` and `[🗑 Name]` buttons for each active item.

- [ ] **Step 1: Add `build_dm_list_keyboard` to `bot/commands.py`**

Add the import at the top of `bot/commands.py`:

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
```

Add the helper function after `build_upcoming_text`:

```python
def build_dm_list_keyboard(db_path: str) -> InlineKeyboardMarkup | None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, name FROM expiry_items WHERE dismissed_at IS NULL ORDER BY expiry_date"
    ).fetchall()
    conn.close()
    if not rows:
        return None
    buttons = [
        [
            InlineKeyboardButton(f"✏️ {r['name']}", callback_data=f"edit:{r['id']}"),
            InlineKeyboardButton(f"🗑 {r['name']}", callback_data=f"delete:{r['id']}"),
        ]
        for r in rows
    ]
    return InlineKeyboardMarkup(buttons)
```

- [ ] **Step 2: Write a test for `build_dm_list_keyboard`**

Add to `tests/test_commands.py`:

```python
from bot.commands import build_dm_list_keyboard

def test_build_dm_list_keyboard_returns_none_when_no_active_items(db_path):
    keyboard = build_dm_list_keyboard(db_path)
    assert keyboard is None


def test_build_dm_list_keyboard_returns_one_row_per_active_item(db_path):
    add_item(db_path, "Panadol", 7)
    add_item(db_path, "Milk", 3)
    keyboard = build_dm_list_keyboard(db_path)
    assert keyboard is not None
    assert len(keyboard.inline_keyboard) == 2
    row0 = keyboard.inline_keyboard[0]
    assert any("Panadol" in btn.text for btn in row0)
    assert any("edit:1" in btn.callback_data or "delete:1" in btn.callback_data for btn in row0)


def test_build_dm_list_keyboard_excludes_dismissed_items(db_path):
    add_item(db_path, "Panadol", 7, dismissed=True)
    keyboard = build_dm_list_keyboard(db_path)
    assert keyboard is None
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/test_commands.py -k "keyboard" -v
```

Expected: `ImportError` — `build_dm_list_keyboard` not found.

- [ ] **Step 4: Update `list_command` to send keyboard in DM**

Replace the `list_command` function in `bot/commands.py`:

```python
async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = context.bot_data["config"]

    conn = sqlite3.connect(cfg.db_path)
    conn.row_factory = sqlite3.Row
    user_id_rows = conn.execute(
        "SELECT DISTINCT submitted_by FROM expiry_items"
    ).fetchall()
    conn.close()

    names: dict[int, str] = {}
    for row in user_id_rows:
        uid = row["submitted_by"]
        try:
            chat = await context.bot.get_chat(uid)
            names[uid] = chat.first_name or chat.username or str(uid)
        except Exception:
            names[uid] = str(uid)

    text = build_list_text(cfg.db_path, names=names)

    if update.effective_chat.type == "private":
        keyboard = build_dm_list_keyboard(cfg.db_path)
        await update.message.reply_text(text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text)
```

- [ ] **Step 5: Run all tests**

```bash
.venv/bin/pytest tests/ -v --tb=short
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add bot/commands.py tests/test_commands.py
git commit -m "feat: show edit/delete buttons on /list in DM"
```

---

## Task 9: Fix `run_reminders.py` async and add submitter name

**Files:**
- Modify: `bot/run_reminders.py`

The standalone reminder runner (for cron/systemd use) has been using `with Bot(...)` synchronously without `await`, which is incorrect for PTB v21+. Fix it with `asyncio.run()` and add submitter name resolution.

- [ ] **Step 1: Replace `bot/run_reminders.py`**

```python
"""
Standalone reminder runner for cron/systemd scheduled tasks.

Usage:
    python -m bot.run_reminders
"""
import asyncio
import logging
import os
from datetime import date

from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from bot.config import get_config
from bot.db import init_db
from bot.reminders import get_due_reminders, record_reminder_sent

logger = logging.getLogger(__name__)


async def _run(cfg) -> None:
    today = date.today()
    dues = get_due_reminders(cfg.db_path, today)

    if not dues:
        logger.info("No reminders due today")
        return

    async with Bot(token=cfg.telegram_bot_token) as bot:
        for due in dues:
            days_remaining = (due.expiry_date - today).days
            category_str = f" ({due.category})" if due.category else ""
            if days_remaining == 0:
                days_str = "expires today"
            else:
                days_str = f"expires in {days_remaining} days ({due.expiry_date.strftime('%-d %b %Y')})"

            try:
                chat = await bot.get_chat(due.submitted_by)
                submitter_name = chat.first_name or chat.username or str(due.submitted_by)
            except Exception:
                submitter_name = str(due.submitted_by)

            text = (
                f"⏰ Expiry reminder — {due.item_name}{category_str}\n"
                f"{days_str.capitalize()}\n"
                f"Added by {submitter_name}"
            )
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("Dismiss ✓", callback_data=f"dismiss:{due.item_id}")]]
            )
            try:
                msg = await bot.send_message(
                    chat_id=cfg.group_chat_id,
                    text=text,
                    reply_markup=keyboard,
                )
                record_reminder_sent(cfg.db_path, due.item_id, due.level, msg.message_id)
                logger.info("reminder_sent item_id=%d level=%s", due.item_id, due.level)
            except Exception:
                logger.error(
                    "Failed to send reminder item_id=%d level=%s", due.item_id, due.level,
                    exc_info=True,
                )


def main() -> None:
    load_dotenv()
    cfg = get_config()

    logging.basicConfig(
        level=cfg.log_level,
        format='{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}',
    )

    os.makedirs(os.path.dirname(cfg.db_path) or ".", exist_ok=True)
    init_db(cfg.db_path)

    asyncio.run(_run(cfg))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run all tests**

```bash
.venv/bin/pytest tests/ -v --tb=short
```

Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add bot/run_reminders.py
git commit -m "fix: make run_reminders.py properly async for PTB v21, add submitter name"
```

---

## Final verification

- [ ] **Run the full test suite one last time**

```bash
.venv/bin/pytest tests/ -v
```

Expected: all tests pass, no warnings about unexpected failures.
