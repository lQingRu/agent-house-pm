# ADR 004 — Deployment: Free Always-On Tier

**Date:** 2026-06-07
**Status:** Accepted

---

## Context

The bot must run continuously to:
- Poll Google Calendar on a schedule
- Evaluate expiry reminder escalations on a schedule
- Respond to Telegram webhook or long-poll events in real time

This rules out any platform that suspends or sleeps inactive deployments, because a sleeping bot will miss its scheduled reminder windows and may introduce significant response latency when a Member sends a message.

Cost is a real constraint. This is a household utility, not a commercial product. The deployment should cost nothing to run indefinitely.

Platforms evaluated:

| Platform | Free tier | Sleeps on inactivity? | Notes |
|---|---|---|---|
| Render (free) | Yes | Yes — sleeps after 15 min | Disqualified |
| Railway (hobby) | Trial credits only | No sleep, but not free long-term | Disqualified |
| Oracle Cloud Free Tier | Yes, permanent | No | 2 AMD VMs always free; suitable |
| Fly.io | Yes, with limits | No (with correct config) | Shared-CPU machines stay up |

---

## Decision

The bot is deployed on a **free always-on tier**. The two recommended platforms are:

1. **Oracle Cloud Free Tier** — 2 permanently free AMD Compute VMs (1 OCPU, 1 GB RAM each). The bot runs as a long-lived process (e.g. under systemd or a process manager). SQLite lives on the local disk.

2. **Fly.io** — Free allowance includes shared-CPU VMs that can be kept running. The bot runs as a container. SQLite is mounted on a persistent volume.

Either platform satisfies the always-on requirement. The choice between them is an operational preference, not an architectural one.

Platforms that sleep on inactivity (Render free tier, Railway free trial, Heroku free tier) are explicitly excluded.

---

## Consequences

- The bot process must be supervised and restarted on crash. On Oracle Cloud this is handled by systemd. On Fly.io the container runtime restarts it automatically.
- SQLite state is colocated with the bot process. On Oracle Cloud it sits on the VM's local disk; on Fly.io it must be on a persistent volume (not ephemeral container storage). Loss of the volume means loss of all Expiry Item and reminder history.
- No autoscaling is needed or expected. This is a single-household bot with at most a handful of concurrent users.
- Outbound internet access (to the Telegram Bot API and Google Calendar API) must be available from the deployment host. Both Oracle Cloud and Fly.io provide this by default.
- If the bot is migrated between hosts, the SQLite file must be manually transferred. There is no automated backup in v1.
- Cold starts are not a concern because the process never sleeps. Telegram webhook or long-poll responses are always handled by a live process.
