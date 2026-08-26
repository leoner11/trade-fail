# DESIGN — Email inquiry channel (v1-scope hole)

Status: DESIGN (2026-08-26, session #14) — implement after Leonard's OK on
scope. One paragraph: buyers also write to sales@ inboxes; today those land
in nobody's queue. This channel normalizes inbound email into the EXISTING
glue `route()` path so classification, quoting, KB answers, escalation and
the S4 Threads store behave identically across WhatsApp and email.

## Principle (house rule #2/#5)

No code forks per client, no second brain. Email is a TRANSPORT, not a
pipeline. Client variation lives in `.env`:

```
EMAIL_ENABLED=0                  # off by default; per-client opt-in
EMAIL_IMAP_HOST=imap.example.com
EMAIL_IMAP_PORT=993
EMAIL_SMTP_HOST=smtp.example.com
EMAIL_SMTP_PORT=587
EMAIL_USER=sales@example.com
EMAIL_PASS=<secret>              # never printed/committed
EMAIL_FOLDER=INBOX
```

## Identity model — pseudo-jid

An email contact becomes `email:<addr>` (lowercased), e.g.
`email:buyer@acme.com`. Consequences, all free because spine S4/S3/S8 key
on the jid STRING:

- `_post(SPINE /resolve, {wa_jid: "email:buyer@acme.com", name})` works
  unchanged → tiers/history intact.
- `_mirror()` lands lines in the SAME `conversations`/`messages` rows →
  console Threads page shows email threads next to WhatsApp threads.
- Escalations arm the same way; SLA beacon still nudges BOSS_WHATSAPP
  (correct: staff live on WhatsApp, buyers live on email).
- Thread continuity (`_THREAD`) keys by jid → offer fulfillment and pricing
  continuations work per email thread exactly as per chat.

## Intake — glue owns mail, n8n stays the clock

New glue endpoint `POST /email/poll` (bearer-gated like other ticks):

1. imaplib (stdlib, no new deps) SSL login, select EMAIL_FOLDER, fetch
   UNSEEN (or UID > high-water stored in `data/email_state.json`).
2. Per message: dedupe on Message-ID (reuse the `_seen` set pattern),
   extract From addr+name, Subject, text/plain body (text/html stripped;
   attachments IGNORED in v1 — logged as `[attachment skipped]`).
3. Call the SAME sequence the WhatsApp webhook runs:
   resolve → `_mirror(...,"in","buyer")` → `await asyncio.to_thread(route,
   customer, subject+"\n\n"+body, pseudo_jid)` → mirror out → **SMTP reply**
   instead of evo.
4. Mark seen / bump high-water ONLY after the reply attempt completes
   (crash-safe: worst case a duplicate answer, never silence).

n8n workflow `email-poll` hits `/email/poll` every minute during office
hours (same pattern as b6/a6/c ticks). No long-lived asyncio task in glue —
keeps restart semantics identical to everything else (trap #41 discipline).

## Outbound — dispatch on jid prefix

`send_text` / `send_document` gain one branch each: jid startswith
`email:` → SMTP path (`smtplib`, stdlib). Reply headers: `In-Reply-To` +
`References` = buyer's Message-ID, subject `Re: <original>` so replies
thread in the buyer's mail client. PDFs (B4 formal quote) attach directly —
arguably BETTER than WhatsApp (real MIME attachment).

`b4_deliver(remote=…)` needs no signature change; only `send_document`
branches internally. Same for the B6 follow-up sender.

Staff take-over: `POST /console/threads/{cid}/reply` currently sends via evo
directly. Branch on the conversation's jid prefix → SMTP. Resolve flow
untouched.

## What deliberately does NOT change

- route() internals: noise gate, triage, overrides, calc B-path, autonomy
  dial, always-human list — all transport-blind already.
- Voice contract: same reply generator. (Later knob: slightly longer/formaler
  register for email via voice_guide.md samples — config-as-code, no engine
  change.)
- Gates pin WhatsApp behavior; nothing there moves.

## Escalation notes

Escalated email threads show in Threads with tag + staff note exactly like
WhatsApp ones. Staff reply from the console → SMTP. If staff prefer replying
from their own mail client, that ALSO works naturally: their From: differs
but the buyer sees a human answer either way; spine just won't mirror it
(v1 limitation, documented — do NOT pretend to mirror what we didn't send).

## Testing strategy

- New gate `tests/test_email_channel.py`: drives `_handle_email()`
  (the shared post-fetch handler) directly with synthetic messages —
  inquiry→quote, spec question→KB answer, complaint→escalation armed +
  Threads row, dedupe on repeated Message-ID. SMTP transport stubbed
  (capture dict), IMAP never touched → fully offline, DRY_RUN-grade.
- Manual `--execute` mode (s10 pattern): real mailbox round-trip against a
  test inbox, target <60s poll-to-reply.
- Full board re-run after glue edits (house rule #4).

## Non-goals (v1)

Attachments parsing, HTML-rich replies, multiple mailboxes per appliance,
push (IMAP IDLE) — poll cadence is fine for sales mail. Exchange/EWS —
IMAP is universal enough.
