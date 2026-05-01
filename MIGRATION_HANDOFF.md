# Migration handoff (shared context)

**Why this file exists:** Cursor chats and operators do not share memory. Use this document as the single place to record **current migration decisions and server-specific facts**. Read it before doing migration work; update it when reality changes (paths, imports, gates).

**Canonical copy:** Track this file in **git** under `gog_bot/MIGRATION_HANDOFF.md`. On GrumpyAdmin the deployed path is **`/opt/grumpy/apps/gog_bot/MIGRATION_HANDOFF.md`** (expect ownership **`grumpy:grumpy`**). If server and git disagree, merge into **one** doc and reconcile the changelog below—do not maintain divergent copies long term.

**Full procedure:** Long-form checklist in git: [NEW_SERVER_MIGRATION_CHECKLIST.md](./NEW_SERVER_MIGRATION_CHECKLIST.md). **`/root/NEW_SERVER_MIGRATION_CHECKLIST.md`** on a server is an **optional mirror** only—prefer editing the git-tracked checklist. On GrumpyAdmin a copy may also live next to the app as **`/opt/grumpy/apps/gog_bot/NEW_SERVER_MIGRATION_CHECKLIST.md`** so paths align with repo layout (sync from git when it changes).

---

## Deploy / sync (GrumpyAdmin)

**`/opt/grumpy/apps/gog_bot/` is not required to be a git checkout.** Today it may be populated only via **rsync/scp from a machine that has the repo** (no `.git` on server → no `git pull` until someone clones into that path or replaces deploy with git-based checkout).

After edits land in git: **`rsync`** at least `gog_bot/MIGRATION_HANDOFF.md` and `gog_bot/NEW_SERVER_MIGRATION_CHECKLIST.md` (plus code as usual) to **`grumpy@GrumpyAdmin:/opt/grumpy/apps/gog_bot/`**. Alternatively, adopt a **real clone** at `/opt/grumpy/apps/gog_bot` and document remote + branch here when that happens.

---

## GrumpyAdmin layout (canonical)

| Area | Path |
|------|------|
| Application code | `/opt/grumpy/apps/gog_bot/` |
| Secrets / env | `/opt/grumpy/env/gog_bot.env` (`DATABASE_URL`, `HOT_STATE_BACKEND`, etc.) |
| Static site (nginx) | `/var/www/grumpygeorge/` |
| JSON snapshots for Postgres import | `/opt/grumpy/data/json-imports/` |
| Backups (checklist-style) | `/opt/grumpy/data/backups/` (also confirm whether `/opt/grumpy/backups/` is still in use anywhere) |

Ownership expectations match the checklist (`grumpy` user, web dirs as documented there).

---

## Nginx (GrumpyAdmin — snapshot)

Live config path for diffing: **`/etc/nginx/sites-available/grumpygeorge`** (enable via `sites-enabled` as usual).

Observed shape (HTTP-only phase):

- **`default_server`** on port **80**
- **`root`** `/var/www/grumpygeorge`
- **`location /api/`** → **`proxy_pass http://127.0.0.1:5000`** with **`Host`**, **`X-Real-IP`**, and **`X-Forwarded-*`** headers set appropriately for the upstream
- Static side uses **`try_files`** as needed for `/`

**HTTPS:** not enabled yet until DNS/SSL gates—adjust this section after certbot/Certbot nginx changes.

Adjust this section when TLS or vhosts change.

---

## Systemd (GrumpyAdmin — snapshot)

- **`grumpyapi.service`** runs the API on the box (alongside nginx proxy above).
- **George bot:** not deployed on GrumpyAdmin **by current plan** (only API here unless that decision changes—update this row if georgebot is added).

---

## Runtime (hot state)

- **`HOT_STATE_BACKEND=postgres`** and **`DATABASE_URL`** (or `POSTGRES_URL`) come from `/opt/grumpy/env/gog_bot.env`.
- Wallet/game state that goes through **`hot_state_store`** is authoritative in **Postgres** while the API runs in Postgres mode—not by editing duplicate JSON copies by hand.

---

## Postgres import script

Script: `scripts/import_hot_state_to_postgres.py`  
Typical run (after `DATABASE_URL` is set):

```bash
cd /opt/grumpy/apps/gog_bot
.venv/bin/python scripts/import_hot_state_to_postgres.py --repo /opt/grumpy/data/json-imports --dry-run
.venv/bin/python scripts/import_hot_state_to_postgres.py --repo /opt/grumpy/data/json-imports
```

**Imported JSON → Postgres (as implemented in repo):**

| JSON file (under `--repo`) | Postgres destination |
|---------------------------|----------------------|
| `user_wallets.json` | `wallets` |
| `wallet_screen_labels.json` | `wallet_screen_labels` |
| `wallet_transactions.json` | `wallet_transactions` |
| `paid_entries.json` | `paid_entries` |
| `virtual_fruit.json` | `fruit_state` |
| `bingo_state.json` | `app_kv_state` key `bingo_state` |
| `quiz_state.json` | `app_kv_state` key `quiz_state` |
| `super6.json` | `app_kv_state` key `super6` |
| `football_card.json` | `app_kv_state` key `football_card` |
| `higherlower.json` | `app_kv_state` key `higherlower` |
| `beer_fund_state.json` | `app_kv_state` key `beer_fund` |

Keep **`beer_fund_state.json`** in the json-imports bundle when syncing from the old server so KV can be seeded without relying on file fallback after cutover.

**Not covered by this importer:** chat history, pint state, leaderboard JSON files, quiz used-questions file paths owned by George modules, `pub_predictions.db`, and other file-backed state unless explicitly migrated later.

---

## Path fixes (deploy under `/opt/grumpy/apps/gog_bot`)

Previously some modules hard-coded `/root/gog_bot/` for JSON paths. That breaks on GrumpyAdmin unless symlinked.

**Resolved in repo (use `__file__` / repo-relative paths):**

- `george_agent.py` — quiz leaderboard, used questions, football card JSON, super6 JSON relative to bot dir.
- `sunday_quiz.py` — leaderboard + used questions via `_QUIZ_DIR`.
- `football_card.py` — `football_card.json` next to the module.

**Ops alignment:** `scripts/weekly_log_prune.sh`, `scripts/backup_pub_snapshot.sh`, and `deploy/log-prune.service` should target `/opt/grumpy/apps/gog_bot` and backup destinations under `/opt/grumpy/data/backups/` (verify on server after pull).

---

## Housekeeping policy

- Duplicate copies of **already-imported** JSON may still exist under `/opt/grumpy/apps/gog_bot/` and in `json-imports/`; they can drift from Postgres. **Do not** treat them as source of truth in Postgres mode.
- **Defer** archiving or deleting those duplicates until **`pg_dump` / backup strategy** is trusted; rollback and audits are easier with redundant files until then.

---

## Gates (reminder)

Do not skip org-defined cutover gates (SSH approval, DNS/SSL, traffic switch) documented in the checklist—this file does not replace those steps.

---

## Workflow

Before migration-related work on either host: **read this file**. When something material changes (imports, paths, nginx/systemd, cutover milestones): **append the changelog** below. If the live server and this doc disagree, **edit the doc** or explicitly call out the mismatch until merged.

---

## Changelog (edit when you change something)

| Date | Change |
|------|--------|
| 2026-05-01 | Initial git handoff: layout, import map, path-fix note, beer_fund import, housekeeping. |
| 2026-05-01 | Merged GrumpyAdmin snapshot: canonical paths note; checklist pointer (git vs `/root/` copy); nginx (`grumpygeorge`, `/api/` → `127.0.0.1:5000`, HTTP until DNS/SSL); systemd `grumpyapi.service`; George bot not on GrumpyAdmin by plan. |
| 2026-05-01 | GrumpyAdmin deploy note: `/opt/grumpy/apps/gog_bot` may have **no `.git`** — sync via **rsync** from repo (or adopt git clone later). Added checklist copy under app dir on server for layout parity. Nginx stanza detail: `/etc/nginx/sites-available/grumpygeorge`. Git handoff merge pending rsync until clone adopted. |
