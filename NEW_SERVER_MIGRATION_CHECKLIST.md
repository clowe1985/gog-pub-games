# Grumpy New Server Migration Checklist

Goal: move to a fresh, clean Hetzner dedicated server with a better folder layout, Postgres hot-state storage, controlled logging, and basic game analytics.

## 1. Server Choice

Recommended:

- Hetzner dedicated server
- Ubuntu 24.04 LTS
- 64 GB RAM minimum
- 2x NVMe SSD
- RAID 1
- Prefer 1 TB usable storage or more
- Germany or Finland location

Good target: AX42 or similar. If budget allows, choose a model with 2x1TB NVMe.

## 2. Initial Server Setup

Create a non-root deploy user:

```bash
adduser grumpy
usermod -aG sudo grumpy
```

Set up:

- SSH key login
- Disable password SSH login
- Firewall ports: `22`, `80`, `443`
- Automatic security updates
- UK timezone
- Hostname, e.g. `grumpy-prod-01`

Install base packages:

```bash
apt update
apt upgrade
apt install nginx certbot python3-certbot-nginx python3-venv python3-pip git rsync ufw fail2ban logrotate postgresql postgresql-client libpq-dev
```

## 3. Clean Folder Layout

Use:

```text
/opt/grumpy/
  apps/
    gog_bot/
  data/
    json-imports/
    backups/
  env/
    gog_bot.env
  logs/
  scripts/
  releases/

/var/www/grumpygeorge/
```

Set ownership:

```bash
chown -R grumpy:grumpy /opt/grumpy
chown -R grumpy:www-data /var/www/grumpygeorge
```

## 4. Code Deployment

App code should live here:

```text
/opt/grumpy/apps/gog_bot/
```

Copy from current server:

```text
/root/gog_bot/*.py
/root/gog_bot/scripts/
/root/gog_bot/deploy/
/root/gog_bot/grumpy-token/       if still needed
/root/gog_bot/index.html
/root/gog_bot/script.js
/root/gog_bot/style.css
/root/gog_bot/audio/              if needed
```

Do not copy:

```text
/root/gog_bot/gogenv/
/root/gog_bot/.venv/
/root/gog_bot/backups_manual_*
/root/gog_bot/__pycache__/
/root/gog_bot/.git/               unless deploying via git clone
```

Rebuild the Python environment fresh:

```text
/opt/grumpy/apps/gog_bot/.venv/
```

## 5. Web Files

Frontend files should live here:

```text
/var/www/grumpygeorge/
  index.html
  script.js
  style.css
  audio/
```

## 6. Secrets And Environment

Put secrets here:

```text
/opt/grumpy/env/gog_bot.env
```

Copy values from current:

```text
/root/gog_bot/.env
```

Set permissions:

```bash
chmod 600 /opt/grumpy/env/gog_bot.env
chown grumpy:grumpy /opt/grumpy/env/gog_bot.env
```

Do not keep secrets in the code directory.

## 7. Postgres Hot-State Plan

Install Postgres on the new server from the start. Create a dedicated database/user:

```bash
sudo -u postgres createuser --pwprompt pubgames
sudo -u postgres createdb -O pubgames pubgames
```

Environment variables:

```text
HOT_STATE_BACKEND=postgres
DATABASE_URL=postgresql://pubgames:REPLACE_ME@127.0.0.1:5432/pubgames
```

Install Python dependencies in the fresh venv:

```bash
cd /opt/grumpy/apps/gog_bot
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

The new hot-state migration code creates these tables automatically when the importer or app starts:

```text
app_kv_state
wallets
wallet_screen_labels
wallet_transactions
paid_entries
fruit_state
```

Hot state to migrate into Postgres:

- users
- wallets
- wallet_transactions
- fruit machine state/balances/events
- bingo cards/state/leaderboard
- quiz entries/scores/questions
- Super 6 entries/leaderboard
- football card state
- higher/lower state
- pub disclaimer acceptances
- moderation strikes
- chat history
- pint state
- watcher cursors / last seen IDs

## 8. JSON Files To Import

Copy old JSON files into:

```text
/opt/grumpy/data/json-imports/
```

Current files to review/import:

```text
/root/gog_bot/user_wallets.json
/root/gog_bot/wallet_transactions.json
/root/gog_bot/virtual_fruit.json
/root/gog_bot/bingo_state.json
/root/gog_bot/bingo_leaderboard.json
/root/gog_bot/quiz_state.json
/root/gog_bot/used_questions.json
/root/gog_bot/super6.json
/root/gog_bot/super6_leaderboard.json
/root/gog_bot/paid_entries.json
/root/gog_bot/pub_disclaimer_acceptances.json
/root/gog_bot/link_spam_strikes.json
/root/gog_bot/chat_history.json
/root/gog_bot/pint_state.json
/root/gog_bot/george_regulars.json
/root/gog_bot/george_drunk_state.json
/root/gog_bot/last_tweet_id.json
/root/gog_bot/twitter_mirror_user_id.json
/root/gog_bot/dead_chat_trivia_scores.json
/root/gog_bot/dead_chat_autonomous_used.json
/root/gog_bot/football_card.json
/root/gog_bot/higherlower.json
/root/gog_bot/airdrop_leaderboard.json
```

Create a one-time importer:

```text
scripts/import_hot_state_to_postgres.py
```

Dry-run first:

```bash
cd /opt/grumpy/apps/gog_bot
.venv/bin/python scripts/import_hot_state_to_postgres.py --repo /opt/grumpy/data/json-imports --dry-run
```

Then import:

```bash
.venv/bin/python scripts/import_hot_state_to_postgres.py --repo /opt/grumpy/data/json-imports
```

After import, the app should read/write Postgres for hot game/app state, not JSON. Keep low-risk George memory/cache JSON files as normal files for now.

## 9. Nginx

Config files:

```text
/etc/nginx/sites-available/grumpygeorge
/etc/nginx/sites-enabled/grumpygeorge
```

Serve static files from:

```text
/var/www/grumpygeorge/
```

Proxy API requests to local GrumpyAPI, for example:

```text
/api/ -> http://127.0.0.1:5000/
```

SSL:

```bash
certbot --nginx -d app.officialgogcoin.com
```

## 10. Systemd Services

Create:

```text
/etc/systemd/system/grumpyapi.service
/etc/systemd/system/georgebot.service
/etc/systemd/system/twitter-watcher.service   if still needed
```

Each service should:

- Run as `grumpy`
- Use `/opt/grumpy/apps/gog_bot` as working directory
- Load `/opt/grumpy/env/gog_bot.env`
- Use the fresh `.venv`
- Restart automatically on failure

Example:

```ini
WorkingDirectory=/opt/grumpy/apps/gog_bot
EnvironmentFile=/opt/grumpy/env/gog_bot.env
ExecStart=/opt/grumpy/apps/gog_bot/.venv/bin/python api_server.py
User=grumpy
Restart=always
```

## 11. Logging Cleanup

Current server logs are too spammy. On the new server:

- Remove or demote noisy `print()` calls.
- Replace random prints with Python `logging`.
- Use `LOG_LEVEL=INFO` in production.
- Use `DEBUG` only temporarily.
- Do not log every poll or successful routine request.
- Log failed requests, slow requests, startup/shutdown, payments, wallet actions, admin actions, and exceptions.
- Never log private keys, secrets, tokens, or full sensitive payloads.

Recommended levels:

- `DEBUG`: noisy developer detail
- `INFO`: important lifecycle events
- `WARNING`: suspicious/recoverable issues
- `ERROR`: failed operations
- `EXCEPTION`: stack traces

Journald limits:

```ini
SystemMaxUse=500M
RuntimeMaxUse=100M
MaxRetentionSec=14day
Compress=yes
```

Then:

```bash
systemctl restart systemd-journald
```

If file logs are used:

```text
/opt/grumpy/logs/*.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
    copytruncate
}
```

Preferred log locations only:

```text
journalctl -u grumpyapi
journalctl -u georgebot
/opt/grumpy/logs/       only if intentionally enabled
```

No random logs in `/root`, app folders, or `/var/www`.

## 12. Game Analytics

Add event tracking from day one.

Create a table:

```text
game_events
```

Suggested fields:

```text
id
created_at
user_id
username
game
event_type
amount_cents
metadata_json
```

Example events:

```text
fruitmachine | spin
fruitmachine | nudge_used
fruitmachine | hold_used
fruitmachine | win
fruitmachine | collect
bingo | card_bought
bingo | claim_attempt
quiz | entered
quiz | answered
super6 | prediction_submitted
football | team_picked
higherlower | guess
```

Track:

- active players today / 7 days / 30 days
- active players per game
- total plays per game
- unique players per game
- revenue/stakes per game
- payouts per game
- net per game
- least-used games
- peak play times
- repeat players / retention

Build:

- `record_game_event(user_id, game, event_type, metadata)`
- admin-only analytics API endpoint
- simple admin dashboard or admin command

Example dashboard output:

```text
Today
- Active players: 23
- Fruit spins: 410
- Bingo cards bought: 12
- Quiz entries: 8

Last 7 days
- Most played: Fruit Machine
- Least played: Football Card
- Highest revenue: Fruit Machine
- Most unique users: Bingo
```

Important: game-critical money events should be database records, not only logs.

## 13. Backups

Backup target:

```text
/opt/grumpy/data/backups/
```

Back up:

- Postgres `pubgames` database via `pg_dump`
- `/opt/grumpy/env/gog_bot.env`
- `/etc/nginx/sites-available/grumpygeorge`
- `/etc/systemd/system/grumpyapi.service`
- `/etc/systemd/system/georgebot.service`
- `/var/www/grumpygeorge/`

Postgres backup:

```bash
pg_dump "$DATABASE_URL" > /opt/grumpy/data/backups/pubgames-YYYYMMDD.sql
```

Custom-format option:

```bash
pg_dump -Fc "$DATABASE_URL" > /opt/grumpy/data/backups/pubgames-YYYYMMDD.dump
```

Retention:

- 7 daily
- 4 weekly
- 3 monthly
- off-server backup if possible

## 14. Test Before Cutover

Before DNS changes:

- API starts locally
- frontend loads
- Telegram auth works
- wallet lookup works
- fruit machine works
- bingo works
- quiz works
- Super 6 works
- football card works
- higher/lower works
- top-up/payment flow tested with tiny amount
- logs are clean
- backup script works
- reboot server and confirm services auto-start

## 15. Cutover Day

On current server:

1. Stop bot/API briefly.
2. Take final JSON snapshot.
3. Copy final snapshot to new server.
4. Re-run JSON to Postgres import.
5. Start services on new server.
6. Point DNS/API domain to new server IP.
7. Issue/confirm SSL.
8. Test Telegram mini app.
9. Keep old server untouched for a few days as rollback.

## 16. Rollback Plan

Keep the old server running but paused for writes if possible.

Rollback:

1. Point DNS back to old server.
2. Restart old services.
3. Investigate the new server issue.

Do not delete the old server until the new one has run cleanly for at least a week.

