# ADR 003 — Google Calendar Integration: Read-Only, Single Calendar, Informational Notifications

**Date:** 2026-06-07
**Status:** Accepted

---

## Context

The household already uses Google Calendar to track family events. The bot should surface upcoming events to the Family Group Chat so members are reminded without having to check the calendar manually.

Several decisions needed to be made:

**Access mode:** Read-only vs. read-write. Write access would allow Members to add events via the bot, but adds OAuth scope complexity, risk of accidental modification, and significant implementation effort.

**Calendar scope:** Families often have multiple Google Calendars (personal, shared, birthdays, etc.). Supporting multiple calendars requires UI to select which calendars to watch and complicates the credential/scope setup.

**Notification timing:** A single notification may be missed. Too many notifications for the same event becomes noise. Calendar events are typically planned further out than expiry items and warrant a longer lead time.

**Dismissal:** Unlike Expiry Items (which represent an action to take — use or discard the item), calendar events are informational. Dismissing a calendar event has no real-world consequence; the event still happens.

---

## Decision

**Read-Only access:** The bot reads from Google Calendar using read-only OAuth scope (`https://www.googleapis.com/auth/calendar.readonly`). It does not create, modify, or delete events.

**Single shared Family Calendar:** One Google Calendar is configured per bot instance. This is the household's shared calendar. Multiple calendars are out of scope for v1.

**Two-stage notification:** The bot posts a Calendar Event Notification to the Family Group Chat at **1 week before** and again at **1 day before** each event.

**Informational only — no Dismiss button:** Calendar Event Notification messages carry no inline buttons. There is no Dismiss mechanism. These messages are broadcast-only and represent no action item for the household.

---

## Consequences

- Calendar credentials (service account key or OAuth token) must be configured at deployment time. There is no self-service setup flow for calendar access in v1.
- The bot must run a scheduled job that polls the calendar for upcoming events and determines which notifications are due to be sent. Google Calendar API quotas apply; daily polling at household scale is well within free tier limits.
- The bot must track which (event, notification-level) pairs have already been sent to avoid duplicate notifications across polling cycles. This state is stored in SQLite alongside Expiry Item data.
- Events that are cancelled or rescheduled in Google Calendar after a notification has been sent will not trigger a correction message in v1. The notification stands.
- If the household has multiple relevant Google Calendars, Members must consolidate them into the single configured calendar, or wait for v2 multi-calendar support.
- The absence of a Dismiss button means the Family Group Chat will accumulate Calendar Event Notification messages over time. This is acceptable; the chat history serves as a record.
