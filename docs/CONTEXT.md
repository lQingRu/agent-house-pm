# Household Bot — Domain Glossary

## Bounded Context

A Telegram bot that helps a family household manage shared concerns: expiring household items and family calendar events. All family members share a single Telegram group; the bot delivers all notifications there and accepts item input via private DM.

---

## Terms

### Member
A household member who interacts with the bot. Multiple members exist in the same household. Each member has their own Private DM channel with the bot and is a participant in the Family Group Chat.

### Family Group Chat
The single shared Telegram group that all Members belong to. The bot posts all Reminders and Calendar Event Notifications here. Members do not add items here — it is the sole delivery channel for bot output.

### Private DM
A one-on-one conversation between a Member and the bot. The channel through which a Member submits new Expiry Items using free-text natural language (not slash commands). Keeps the Family Group Chat clean.

### Expiry Item
A physical household item that has an expiration date tracked by the bot. A Member submits it via Private DM. The bot posts Escalating Reminders to the Family Group Chat as the expiry date approaches.

### Category
A cosmetic label applied to an Expiry Item (e.g. "medicine", "pantry", "household"). Categories affect display only — they do not change reminder timing or behaviour.

### Escalating Reminder
The sequence of Reminders the bot posts to the Family Group Chat for a single Expiry Item: one at 7 days before expiry, one at 3 days before, and one on the day of expiry. Each is a separate message. Posting stops once the item is Dismissed.

### Reminder
A single notification the bot posts to the Family Group Chat about an Expiry Item approaching or reaching its expiry date. Each Reminder carries an inline Dismiss button.

### Dismissal
An action taken by any Member (in the Family Group Chat) by pressing the inline Dismiss button on a Reminder. Dismissal marks the Expiry Item as Resolved and causes the bot to edit that Reminder message in place to show the Resolved status clearly. No further Reminders are sent for a Dismissed item.

### Resolved Status
The visual state of a Reminder message after Dismissal. The bot edits the original group message to make it clear the item has been dealt with. Any Member may trigger Dismissal — it is a household-wide action.

### Calendar Event
An event the bot reads from the Family Calendar. The bot posts Calendar Event Notifications to the Family Group Chat at 1 week before and 1 day before the event.

### Calendar Event Notification
An informational message the bot posts to the Family Group Chat about an upcoming Calendar Event. These messages have no inline buttons and no Dismissal mechanism.

### Family Calendar
The single shared Google Calendar representing the household's schedule. The bot reads from it in read-only mode. Only one calendar is in scope for v1.

---

## System Boundaries

**The bot does:**
- Accept free-text Expiry Item submissions from Members via Private DM
- Post Escalating Reminders (7d / 3d / day-of) to the Family Group Chat
- Allow any Member to Dismiss an Expiry Item via inline button, editing the message to show Resolved Status
- Read the Family Calendar (read-only) and post Calendar Event Notifications at 1 week and 1 day before each event
- Respond to `/list` (all Expiry Items and their status) and `/upcoming` (next 7 days of Expiry Items and Calendar Events)
- Persist all data in SQLite on the server

**The bot does not (v1):**
- Write to or modify the Family Calendar
- Support per-category reminder timing differences
- Provide a Dismiss button on Calendar Event Notifications
- Support multiple family calendars
- Allow item submission via the Family Group Chat

---

## Deferred to V2 / Open Questions

- Per-category reminder schedules (e.g. medicine gets a shorter window than pantry)
- Write access to Google Calendar (adding events from the bot)
- Support for multiple calendars
- Item editing or correction after submission (currently requires delete + re-add)
- Push notifications to individual Members in addition to the group
- OAuth self-service flow for calendar setup (currently requires manual credential configuration)
