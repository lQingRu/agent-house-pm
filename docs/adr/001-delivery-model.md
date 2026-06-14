# ADR 001 — Delivery Model: Group Chat for Output, Private DM for Input

**Date:** 2026-06-07
**Status:** Accepted

---

## Context

The bot serves multiple family members. We needed to decide:

1. Where the bot posts reminders and notifications — to each Member individually, to the group, or both.
2. Where Members submit new Expiry Items — in the group, in a private DM, or via slash commands.

Posting individually to each Member means each person must independently track what has been done. Posting to the Family Group Chat creates shared awareness: everyone sees the same Reminders and can see when something is Dismissed.

For item submission, accepting free-text in the group chat would make it noisy. Slash commands impose a rigid syntax that members must learn. A private DM with free-text input is lower friction and keeps the group feed clean.

---

## Decision

All bot output (Reminders, Calendar Event Notifications, command responses) is delivered exclusively to the **Family Group Chat**. There is one group; there is one notification channel.

All item input is submitted via **Private DM** to the bot using **free-text natural language**. Slash commands (`/list`, `/upcoming`) are supported in both the group and DMs.

---

## Consequences

- Every household member sees every Reminder and every Calendar Event Notification. There is no per-member notification preference.
- A Member must initiate a Private DM with the bot before they can add items (standard Telegram flow: message the bot directly).
- Dismissal is a group-level action — any Member can dismiss any item. This is intentional. There is no ownership or permission model per item.
- The Family Group Chat serves as the household's shared dashboard. Its message history is the audit trail of what was reminded and what was dismissed.
- The bot does not need to track individual Member preferences or notification settings in v1.
