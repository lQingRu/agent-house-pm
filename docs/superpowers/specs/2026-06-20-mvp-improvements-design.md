# MVP Improvements Design

**Date:** 2026-06-20  
**Status:** Approved

## Overview

Four improvements to the household bot MVP:

1. Edit/delete items via DM inline keyboard
2. Show who added an item (in `/list` and reminder messages)
3. Smart reminder schedule on item confirmation
4. Expose bot config via `/config` command and `/help`

---

## 1. Edit/Delete Flow

`/list` in DM renders each item with two inline buttons per item:

```
• Panadol (medicine) — expires 15 Jul 2026
  [✏️ Edit]  [🗑 Delete]
```

### Delete path

Tapping Delete replaces the message with a confirmation prompt:

> "Delete Panadol? This can't be undone."  
> `[Yes, delete]`  `[Cancel]`

Confirming removes the item from the DB (`DELETE FROM expiry_items WHERE id = ?`) and edits the message to "✅ Panadol deleted." Cancelling restores the original list message.

### Edit path

Tapping Edit shows three sub-buttons inline:

> `[Name]`  `[Category]`  `[Expiry date]`

Tapping one triggers a `ConversationHandler` state: the bot replies "Send the new [field]." and waits for the user's next message. That message is validated (date format check for expiry date) and written to the DB. Bot confirms: "Updated! Panadol → Panadol Extra." Then exits the conversation state.

### Authorisation

Any household member can edit or delete any item. No ownership restriction — this is a trusted family context.

### Implementation notes

- Add a `ConversationHandler` in `__main__.py` to handle the edit flow states.
- States: `EDIT_FIELD_SELECT`, `EDIT_VALUE_AWAIT`
- Callback data patterns: `edit:<item_id>`, `edit_field:<item_id>:<field>`, `delete:<item_id>`, `delete_confirm:<item_id>`
- The existing `/list` command needs a DM-specific variant that includes the inline buttons (group `/list` stays read-only, no buttons).

---

## 2. Who Added It

`submitted_by` (Telegram user ID) is already stored in `expiry_items`. Surface it in two places.

### In `/list` output

```
• Panadol (medicine) — expires 15 Jul 2026 (added by Alice)
• Milk — expires 25 Jun 2026 (added by Bob)
```

Resolve name via `bot.get_chat(user_id)` → use `first_name`. Cache results within a single `/list` call to avoid redundant API calls when multiple items share a submitter.

### In reminder messages

```
⏰ Expiry reminder — Panadol (medicine)
Expires in 7 days (15 Jul 2026)
Added by Alice
```

In `run_reminders.py`, resolve name via `bot.get_chat(submitted_by)`. This works because the user must have DM'd the bot to add the item, so Telegram allows the lookup.

---

## 3. Smart Reminder Schedule on Confirmation

When an item is added via DM, calculate which of the three thresholds (7d, 3d, 0d) are still in the future. Show actual calendar dates; strike through skipped ones.

**Item expiring in 10 days (30 Jun):**
```
Got it! I've noted Milk — expires 30 Jun 2026.

Reminders: ✓ 7 days (23 Jun), ✓ 3 days (27 Jun), ✓ on the day (30 Jun)
```

**Item expiring in 2 days (22 Jun):**
```
Got it! I've noted Panadol (medicine) — expires 22 Jun 2026.

Reminders: <s>7 days</s>, <s>3 days</s>, ✓ on the day (22 Jun)
```

Use HTML parse mode for this confirmation message (`parse_mode="HTML"`) to use `<s>` for strikethrough, avoiding MarkdownV2 escaping complexity. The rest of the bot remains on Markdown.

### Logic

```python
thresholds = [("7 days", 7), ("3 days", 3), ("on the day", 0)]
today = date.today()
parts = []
for label, days in thresholds:
    fire_date = expiry_date - timedelta(days=days)
    if fire_date < today:
        parts.append(f"<s>{label}</s>")
    else:
        date_str = fire_date.strftime("%-d %b")
        parts.append(f"✓ {label} ({date_str})")
```

---

## 4. Config Exposure

### `/config` command

Available in DM and group. Reads from the live `Config` object.

```
⚙️ Bot configuration

Reminder time: 08:00 daily
Reminder schedule: 7 days, 3 days, on the day
```

Google Calendar line is only shown if both `GOOGLE_SERVICE_ACCOUNT_KEY_PATH` and `GOOGLE_CALENDAR_ID` are set. If neither is configured (current state), the line is omitted.

### `/help` update

Add one line at the end of `_HELP_TEXT`:

```
/config — show current bot settings (reminder time, schedule)
```

And in the start message, after listing reminders:

```
Reminders fire daily at {cfg.reminder_job_time} — use /config to see all settings.
```

`reminder_job_time` is injected dynamically from the Config object so it reflects the actual env var value.

---

## Files Affected

| File | Change |
|---|---|
| `bot/commands.py` | Add `config_command`, update `build_list_text` to show submitter name and inline buttons in DM context, update `_HELP_TEXT` |
| `bot/handlers.py` | Update confirmation message: HTML mode, smart schedule |
| `bot/dismiss.py` | Add `edit_callback_handler`, `delete_callback_handler` |
| `bot/run_reminders.py` | Add submitter name resolution to reminder text |
| `bot/__main__.py` | Register `ConversationHandler` for edit flow, register `/config` command |

---

## Out of Scope

- In-bot config editing (settings changed via env vars only)
- Per-category reminder thresholds
- Group-side edit buttons on reminder messages
