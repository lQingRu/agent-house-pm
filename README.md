# House PM — Household Expiry & Calendar Bot

A Telegram bot that tracks household expiry items and upcoming calendar events for a family group chat.

- **Members** add items (milk, medicine, passports…) via a private DM to the bot
- The bot posts reminders to a shared **family group chat** at 7 days, 3 days, and on the day of expiry
- Optionally reads a **shared Google Calendar** and posts 7-day and 1-day heads-up notices for upcoming events

---

## Prerequisites

| What                                  | Where to get it                                                      |
| ------------------------------------- | -------------------------------------------------------------------- |
| Telegram bot token                    | Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot` |
| Family group chat ID                  | See [Finding Your Group Chat ID](#finding-your-group-chat-id) below  |
| Python 3.11+                          | [python.org](https://www.python.org/downloads/)                      |
| (Optional) Google service account key | See [Google Calendar Setup](#google-calendar-setup-optional) below   |

---

## Quick Start — Run Locally (long-polling)

This is the easiest way to try the bot. No server needed — it polls Telegram for updates.

**1. Clone and install**

```bash
git clone <this-repo>
cd house-pm
make install
```

**2. Create your `.env` file**

```bash
cp .env.example .env
```

Then edit `.env`:

```env
TELEGRAM_BOT_TOKEN=7123456789:AAFxyz...   # from BotFather
GROUP_CHAT_ID=-1001234567890              # your family group chat (negative number)
DB_PATH=data/house.db                     # where SQLite is stored (default is fine)
REMINDER_JOB_TIME=08:00                   # time of day to send reminders (UTC)
LOG_LEVEL=INFO                            # DEBUG for verbose output
```

**3. Run**

```bash
make run
```

The bot starts and is immediately usable. Send it a DM like:

> `Milk expires 20 Jun 2026`

It replies with a confirmation and will remind the group at 7 days, 3 days, and on the day.

---

## Finding Your Group Chat ID

1. Add your bot to the family group chat (via the Telegram group settings → Add Member)
2. Send any message in the group (e.g. `/start`)
3. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser
4. Look for `"chat":{"id":1001234567890,...}` — the **number** is your group chat ID

---

## How to Use the Bot

### Adding an expiry item (private DM to the bot)

Send the bot a message describing the item and its expiry date. It understands natural language:

```
Milk expires 20 Jun 2026
Panadol (medicine) best before 1 Jan 2027
Passport (documents) use by 15 Mar 2030
Sun cream expires in 3 months
```

The bot will confirm and schedule reminders.

### Commands (in the group chat or DM)

| Command     | What it does                                                                |
| ----------- | --------------------------------------------------------------------------- |
| `/list`     | Shows all tracked items with their status                                   |
| `/upcoming` | Shows items expiring in the next 7 days, plus calendar events if configured |

### Dismissing a reminder

When the bot posts a reminder in the group chat, tap **Dismiss ✓** to mark it as resolved. The first person to dismiss wins — anyone else gets "Already dismissed."

---

## Running Tests

```bash
make test
```

---

## Deploy to PythonAnywhere (free, always-on)

PythonAnywhere's free tier gives you a public HTTPS URL, persistent disk, and daily scheduled tasks — everything the bot needs, forever, for free.

### Step 1 — Create a PythonAnywhere account

Sign up at [pythonanywhere.com](https://www.pythonanywhere.com) (no credit card required). Note your username — it becomes `<username>.pythonanywhere.com`.

### Step 2 — Upload the code

Open a **Bash console** in PythonAnywhere and run:

```bash
git clone <this-repo> ~/house-pm
cd ~/house-pm
mkvirtualenv house-pm --python=python3.11
pip install -e .
```

### Step 3 — Create the database directory

```bash
mkdir -p ~/house-pm/data
```

### Step 4 — Create a Web App

1. Go to the **Web** tab → **Add a new web app**
2. Choose **Manual configuration** (not Flask/Django)
3. Choose **Python 3.11**

Then edit the **WSGI configuration file** (link on the Web tab). Replace its contents with:

```python
import sys
sys.path.insert(0, '/home/<username>/house-pm')

from bot.webhook_app import create_app
import os

application = create_app(
    bot_token=os.environ['TELEGRAM_BOT_TOKEN'],
    db_path=os.environ.get('DB_PATH', '/home/<username>/house-pm/data/house.db'),
    group_chat_id=int(os.environ['GROUP_CHAT_ID']),
)
```

Replace `<username>` with your PythonAnywhere username.

### Step 5 — Set environment variables

Still in the WSGI config file, add your env vars at the top:

```python
import os
os.environ['TELEGRAM_BOT_TOKEN'] = '7123456789:AAFxyz...'
os.environ['GROUP_CHAT_ID'] = '-1001234567890'
os.environ['DB_PATH'] = '/home/<username>/house-pm/data/house.db'
os.environ['LOG_LEVEL'] = 'INFO'
```

### Step 6 — Set your virtualenv

On the Web tab, under **Virtualenv**, enter:

```
/home/<username>/.virtualenvs/house-pm
```

### Step 7 — Reload the web app

Click **Reload** on the Web tab. Your webhook URL is now live at:
`https://<username>.pythonanywhere.com/webhook`

### Step 8 — Register the webhook with Telegram

Run this once from a Bash console (or your browser):

```bash
curl "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=https://<username>.pythonanywhere.com/webhook"
```

You should see: `{"ok":true,"result":true,...}`

### Step 9 — Set up the daily reminder job

Go to the **Tasks** tab → **Add a new scheduled task**:

- **Command:** `cd /home/<username>/house-pm && /home/<username>/.virtualenvs/house-pm/bin/python -m bot.run_reminders`
- **Hour:** `8` (08:00 UTC — adjust to your preferred time)

### Smoke test

1. Send the bot a DM with an expiry item — it should reply
2. Run `/list` in the group chat — it should respond
3. Run the reminder script manually from a Bash console:
   ```bash
   cd ~/house-pm && python -m bot.run_reminders
   ```

---

## Google Calendar Setup (optional)

Lets the bot post 7-day and 1-day notices for events on a shared Google Calendar.

### Step 1 — Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (e.g. `house-pm-bot`)
3. Enable the **Google Calendar API** (APIs & Services → Library → search "Google Calendar API" → Enable)

### Step 2 — Create a Service Account

1. APIs & Services → Credentials → **Create Credentials** → **Service account**
2. Give it any name (e.g. `house-pm-reader`)
3. No special roles needed — click through to **Done**
4. Click the service account → **Keys** tab → **Add Key** → **JSON**
5. Download the JSON key file (keep it secret — treat it like a password)

### Step 3 — Share your Google Calendar with the service account

1. Open [Google Calendar](https://calendar.google.com) → find your family shared calendar
2. Settings (⚙) → **Share with specific people** → paste the service account email (looks like `house-pm-reader@your-project.iam.gserviceaccount.com`)
3. Permission: **See all event details** (read-only)
4. Find your **Calendar ID**: Calendar Settings → scroll to **Integrate calendar** → copy the Calendar ID (looks like `abc123@group.calendar.google.com` or your email address for the primary calendar)

### Step 4 — Add to your config

**Local (`.env`):**

```env
GOOGLE_SERVICE_ACCOUNT_KEY_PATH=/path/to/key.json
GOOGLE_CALENDAR_ID=your-calendar-id@group.calendar.google.com
```

**PythonAnywhere:** Upload the key JSON file and add to the WSGI config:

```python
os.environ['GOOGLE_SERVICE_ACCOUNT_KEY_PATH'] = '/home/<username>/house-pm/calendar-key.json'
os.environ['GOOGLE_CALENDAR_ID'] = 'your-calendar-id@group.calendar.google.com'
```

Then add to the **Tasks** command (or a separate task at the same time):

```bash
cd /home/<username>/house-pm && /home/<username>/.virtualenvs/house-pm/bin/python -c "
import asyncio, os
os.environ.setdefault('TELEGRAM_BOT_TOKEN', '<token>')
os.environ.setdefault('GROUP_CHAT_ID', '<id>')
from bot.calendar_service import run_calendar_job
# Note: for production, integrate run_calendar_job into a proper async runner
"
```

> **Tip:** The calendar job runs alongside the expiry reminder job during the daily scheduled task when both env vars are set and you're running in long-polling mode. For PythonAnywhere webhook mode, add a separate daily task that runs a small script calling `run_calendar_job`.

If `GOOGLE_CALENDAR_ID` or `GOOGLE_SERVICE_ACCOUNT_KEY_PATH` is missing, the bot starts normally and silently skips calendar functionality.

---

## Environment Variable Reference

| Variable                          | Required | Default         | Description                                                          |
| --------------------------------- | -------- | --------------- | -------------------------------------------------------------------- |
| `TELEGRAM_BOT_TOKEN`              | Yes      | —               | Token from @BotFather                                                |
| `GROUP_CHAT_ID`                   | Yes      | —               | Numeric ID of the family group chat (negative number)                |
| `DB_PATH`                         | No       | `data/house.db` | Path to the SQLite database file                                     |
| `REMINDER_JOB_TIME`               | No       | `08:00`         | Time of day for reminders in `HH:MM` format (UTC, polling mode only) |
| `LOG_LEVEL`                       | No       | `INFO`          | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`               |
| `GOOGLE_SERVICE_ACCOUNT_KEY_PATH` | No       | —               | Path to Google service account JSON key file                         |
| `GOOGLE_CALENDAR_ID`              | No       | —               | Google Calendar ID to watch                                          |

---

## Project Structure

```
bot/
  __main__.py          # Entry point for long-polling mode
  config.py            # Reads env vars into a Config dataclass
  db.py                # SQLite schema initialisation
  handlers.py          # DM message handler (item ingestion)
  ingestion.py         # Store expiry items in the DB
  parser.py            # NLP date parsing from free-text messages
  reminders.py         # Query which reminders are due; record sent
  scheduler.py         # Async job: post reminders via bot
  dismiss.py           # Inline button callback handler
  commands.py          # /list and /upcoming command handlers
  calendar_service.py  # Google Calendar polling + notification logic
  webhook_app.py       # Flask WSGI app for PythonAnywhere deployment
  run_reminders.py     # Standalone script for PythonAnywhere scheduled task

tests/                 # pytest test suite (65 tests)
docs/adr/              # Architecture decision records
```
