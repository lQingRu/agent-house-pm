# ADR 002 — Expiry Reminders: Escalating Schedule, Open Dismissal, SQLite Storage, Cosmetic Categories

**Date:** 2026-06-07
**Status:** Accepted

---

## Context

Several interlinked decisions needed to be made together because they constrain each other:

**Reminder frequency:** A single reminder may be missed or ignored. Too many reminders becomes noise. We needed a schedule that gives the household meaningful lead time without spamming.

**Dismissal:** Once an item has been dealt with (used, discarded, noted), continued reminders are wasteful. We needed a way to stop the escalation and communicate resolution back to the group.

**Dismissal ownership:** Should only the person who added an item be able to dismiss it, or can any Member? In a household context, anyone may act on an item — e.g. someone else may use the medicine or throw out the expired food.

**Message fate after dismissal:** Delete the reminder message, leave it as-is, or edit it? Deletion loses history. Editing in-place preserves context while showing the resolution.

**Storage:** Expiry dates, submission timestamps, dismissal state, and category labels must be persisted somewhere. Options considered: hosted database, SQLite on the server, external key-value store.

**Categories:** Do different item types (medicine vs. pantry) warrant different reminder schedules? This adds significant logic complexity.

---

## Decision

**Escalating Reminder Schedule:** The bot sends three reminders per Expiry Item: at **7 days before**, **3 days before**, and **on the day of** expiry. Once dismissed, all subsequent reminders for that item are suppressed.

**Open Dismissal:** Any Member may dismiss any Expiry Item by pressing the inline Dismiss button on any of its Reminder messages in the Family Group Chat. There is no per-item ownership or permission check.

**Group Message Edit on Dismissal:** When an item is dismissed, the bot edits the most recently posted Reminder message for that item to display its Resolved Status clearly. The edit happens in the Family Group Chat so all Members see the resolution without any action on their part.

**SQLite on the Server:** All Expiry Items, their categories, submission metadata, reminder send history, and dismissal state are stored in a SQLite database on the deployment server. No external database service is required.

**Cosmetic Categories Only:** Categories (e.g. "medicine", "pantry", "household") are display labels. They do not affect reminder timing, escalation schedule, or any other behaviour in v1.

---

## Consequences

- The bot must run a scheduled job (e.g. daily) to evaluate which items are due for a reminder at each escalation level and post accordingly.
- Each item must track which escalation levels have already been sent to avoid duplicate reminders.
- Editing a message requires the bot to store the Telegram message ID of the most recently sent Reminder for each item.
- Any Member can resolve any item. There is no recourse if a Member dismisses an item prematurely. This is acceptable given the household trust context.
- SQLite ties state to the deployment host. Moving servers requires migrating the database file. This is a reasonable trade-off for a household-scale application.
- Category free-text from the user is stored as-is; the bot does not validate or normalise categories in v1. This means "Medicine" and "medicine" are stored as separate strings.
- Per-category reminder schedules are deferred to v2 if ever needed.
