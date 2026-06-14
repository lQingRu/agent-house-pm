# Household Bot — Domain Glossary

## Bounded Context

A Telegram bot that helps a family household manage shared concerns: expiring items and family calendar events.

---

## Terms

### Family Group Chat
The single shared Telegram group that all household members belong to. The bot posts reminders and notifications here. Members do not add items here — it is a read destination for bot output.

### Member
A household member who interacts with the bot. Each member has their own private Telegram DM channel with the bot.

### Private DM
A one-on-one conversation between a Member and the bot. The channel through which a Member adds items to the system. Keeps the Family Group Chat clean.

### Expiry Item
A physical household item that has an expiration date tracked by the bot. A Member adds it via Private DM. The bot reminds the Family Group Chat before the item expires.

### Reminder
A notification the bot posts to the Family Group Chat warning that an Expiry Item is approaching or has reached its expiry date.

### Family Calendar
An external Google Calendar representing the household's shared schedule. The bot reads events from it and surfaces them to the Family Group Chat.

---

## Open Questions

- Reminder timing: how far in advance? Single or escalating?
- Item categories: do medicine and food need different reminder behaviour?
- Google Calendar scope: read-only? Which calendars? OAuth flow?
- Data storage: where does expiry data live?
- Deployment: always-on server vs. cloud functions?
