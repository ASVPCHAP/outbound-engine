# Outbound Engine

A human-in-the-loop LinkedIn outbound engine for B2B teams. It finds accounts at the right moment, scores them,
drafts short source-backed messages and queues them for approval. **People send every message by hand, from their
own account.** Nothing in this codebase talks to linkedin.com.

Built by [Anthony Chapman](https://github.com/ASVPCHAP) ([Rockwall Partners](https://rockwallpartners.com)). It runs on
Rockwall's own outbound first, and each client install is one `.env` plus one `clients/<id>.json`.

## Why it's built this way

Most "AI SDR" tools automate the sending, which gets accounts restricted and burns the sender's network.
This engine automates everything *before* the send and leaves the send to a person:

```
SIGNAL -> ENRICH -> SCORE -> DRAFT -> APPROVE -> MANUAL SEND -> LOG -> FOLLOW-UP -> REPLIES -> REPORT/LEARN
```

**Guardrails are enforced in code, not policy:**
1. No code path sends to, scrapes or scripts LinkedIn.
2. Every draft passes an approval queue. The one exception is opt-outs.
3. Per-sender invite caps with a ramp (5/10/15 a day, 100 a week). The queue refuses to release drafts past the cap.
4. Any "stop" on any channel marks the person do-not-contact everywhere, automatically.
5. A draft may only use facts that carry a source tag. No invented compliments, mutual connections or profile visits.
6. No secrets in the repo. A pre-commit hook blocks key-shaped strings.

## Design

- **Warm first.** Each batch is ordered network, then engaged, then past customers, then cold lookalikes.
- **Signals must be visible, recent (30-90 days), causal and usable in a first line.** Keep 2-4 per ICP, and favor accounts showing two at once.
- **Scoring (0-100):** ICP fit 40, event strength 30, signal strength 20, recency 10. The breakdown is stored as readable text.
- **Seven gate checks** before a draft reaches review: source, fit, no-repeat/cooldown, volume, message lint, sender ownership, reply SLA.
- **Learning loop:** every approve/edit/reject is saved with a diff and reason. Outcomes are scored 14 days after a send.
  The top examples per segment and signal feed the next prompt. Proposed rules wait for human approval. Prompts are versioned.
- **One codebase, many clients:** `client_id` is on every table, and each client runs in its own Airtable base with its own keys.

## Data model

Twelve Airtable tables defined as code in [`engine/schema.py`](engine/schema.py): ICP, Clients, Senders, Accounts,
Contacts, Signals, Drafts, Send Log, Replies, Examples, Rules, Experiments. `python -m engine.provision` creates the base
or adds missing tables and fields, and never deletes anything.

## Status

| Phase | What | State |
|---|---|---|
| 0 | Schema-as-code provisioning, client seed, smoke test, secret guard | Done |
| 1 | Warm ingest: LinkedIn connections export, past customers/CRM CSV, warm-entry form, ICP title match | Done |
| 2 | Non-LinkedIn signals (news, filtered job posts, funding) with a per-run budget guard | Next |
| 3-4 | Enrichment, scoring, gate checks | Planned |
| 5 | Claude drafting, voice lint, approval interface | Planned |
| 6-8 | Send list and caps, cadence, reply sorting and DNC, weekly scorecard | Planned |

## Install

1. Create an Airtable personal access token (`data.records:read/write`, `schema.bases:read/write`).
2. `copy .env.example .env` and paste in the values.
3. Copy `clients/example.json` to `clients/<client_id>.json`, fill in ICP, segments and senders, and set `CLIENT_ID` in `.env`.
4. `python -m engine.provision`, then put the printed base id in `.env` as `AIRTABLE_BASE_ID` and run it again.
5. `python -m engine.seed`, then `python -m engine.smoke`.

Warm ingest:

    python -m engine.ingest connections Connections.csv --dry-run   # your own LinkedIn data export
    python -m engine.ingest past-customers export.csv
    python -m engine.ingest normalize                               # ids for warm-form rows

## Development

    git config core.hooksPath .githooks
    python -m unittest discover -s tests -t .

Python 3.12, standard library only.
