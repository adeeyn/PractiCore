# Deploying PractiCore on a Hostinger VPS (Ubuntu 22.04 / 24.04)

Stack: **nginx → gunicorn → Flask → MySQL**, managed by **systemd**.
This works on your raw VPS IP today and on your domain once DNS points at it.

Total time: ~30-45 min, mostly waiting on `apt` and MySQL.

---

## 0. What you need

- Your VPS IP (Hostinger hPanel → VPS → Overview)
- SSH access: use **root + password**, or add your key under
  VPS → Settings → SSH keys. Connect with:
  `ssh root@YOUR_VPS_IP`
- Your project folder on the VPS (you said it's already uploaded —
  the guide assumes it ends up at `/var/www/practicore`; adjust the paths in
  `deploy/practicore.service` + `deploy/practicore.nginx` if yours differs)

---

## 1. Point your domain at the VPS (Hostinger hPanel)

1. hPanel → **Domains** → your domain → **DNS / Nameservers**.
2. Make sure it uses Hostinger nameservers, then open **DNS Zone Editor**.
3. Set the **A record for `@`** to your VPS IP (TTL default).
4. Add an **A record for `www`** → same VPS IP.
5. Wait for propagation (`https://dnschecker.org` — usually minutes, up to 24h).

> You can do every step below on the raw IP first and add the domain + HTTPS
> at the end (steps 8-9). Nothing has to wait for DNS.

---

## 2. Server prep (run over SSH as root)

```bash
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip mysql-server nginx git certbot python3-certbot-nginx
systemctl enable --now mysql nginx
```

Secure MySQL (answer YES to most prompts, set a strong root password):

```bash
sudo mysql_secure_installation
```

Allow web traffic through the firewall:

```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable
```

---

## 3. Project + Python environment

```bash
mkdir -p /var/www
# if the folder is already on the VPS, move it here:
#   mv ~/PractiCore /var/www/practicore
# otherwise clone:
#   git clone https://github.com/adeeyn/PractiCore.git /var/www/practicore
cd /var/www/practicore

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

---

## 4. Database (MySQL on the VPS)

```bash
# create the app user + database (replace the password):
sudo mysql <<'SQL'
CREATE DATABASE IF NOT EXISTS practicore CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'practicore'@'127.0.0.1' IDENTIFIED BY 'REPLACE_WITH_STRONG_PASSWORD';
CREATE USER IF NOT EXISTS 'practicore'@'localhost' IDENTIFIED BY 'REPLACE_WITH_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON practicore.* TO 'practicore'@'127.0.0.1';
GRANT ALL PRIVILEGES ON practicore.* TO 'practicore'@'localhost';
FLUSH PRIVILEGES;
SQL
```

Load the schema, then the incremental migrations in order:

```bash
cd /var/www/practicore
mysql -u practicore -p practicore < migrations/mysql_schema_dump.sql
for f in migrations/0*.sql; do
  echo "== $f"; mysql -u practicore -p practicore < "$f"
done
```

Then seed the question banks (safe to re-run — upserts, no duplicates):

```bash
source venv/bin/activate
set -a; source .env; set +a   # needs step 5 first — come back here
flask --app app seed-questions
flask --app app seed-competencies
flask --app app seed-master-bank
flask --app app seed-coverage-bank
flask --app app create-admin    # create YOUR admin login
```

---

## 5. App config (`.env` — secrets live here, never in git)

```bash
cd /var/www/practicore
cp .env.example .env
nano .env
```

Fill in:

```ini
SECRET_KEY=<from: python3 -c "import secrets; print(secrets.token_hex(32))">
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=practicore
DB_PASSWORD=<the password from step 4>
DB_NAME=practicore
SPACY_MODEL=en_core_web_sm
```

Upload dirs (created automatically, but set ownership once):

```bash
mkdir -p practicore/static/uploads/avatars practicore/static/uploads/logos
chown -R practicore:www-data /var/www/practicore
chmod -R 775 practicore/static/uploads
```

Quick smoke test before wiring nginx:

```bash
source venv/bin/activate
set -a; source .env; set +a
gunicorn --config gunicorn.conf.py wsgi:app
# visit http://YOUR_VPS_IP:8000 — Ctrl+C to stop
```

---

## 6. systemd (keeps the app running + restarts on reboot)

```bash
id practicore || useradd -r -m -s /usr/sbin/nologin practicore
sudo cp deploy/practicore.service /etc/systemd/system/practicore.service
sudo nano /etc/systemd/system/practicore.service   # fix User/paths if yours differ
sudo systemctl daemon-reload
sudo systemctl enable --now practicore
sudo systemctl status practicore --no-pager
sudo journalctl -u practicore -f   # live logs, Ctrl+C to exit
```

If it fails: `.env` wrong DB password (Access denied in journal),
migrations not loaded (missing tables), or port clash
(`ss -tlnp | grep 8000`).

---

## 7. nginx (public web server → forwards to gunicorn)

```bash
sudo cp deploy/practicore.nginx /etc/nginx/sites-available/practicore
sudo nano /etc/nginx/sites-available/practicore
# TEMPORARY:  server_name YOUR_VPS_IP;   (test on raw IP)
# LATER:      server_name yourdomain.com www.yourdomain.com;
sudo ln -s /etc/nginx/sites-available/practicore /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

Visit `http://YOUR_VPS_IP` — PractiCore should load.

---

## 8. HTTPS once DNS propagates

```bash
# point nginx at the domain first, then:
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Then harden the session cookie (breaks logins on HTTP — only after certbot):

```bash
nano /var/www/practicore/.env
# uncomment:
#   SESSION_COOKIE_SECURE=1
#   PREFERRED_URL_SCHEME=https
sudo systemctl restart practicore
```

---

## 9. Deploying updates later

```bash
cd /var/www/practicore
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
# apply any NEW migrations only, then restart:
sudo systemctl restart practicore
sudo systemctl reload nginx
```

---

## Troubleshooting

| Symptom | Check |
|---|---|
| 502 Bad Gateway | `systemctl status practicore` — gunicorn down? `.env` wrong? |
| Login loops / session lost | `SESSION_COOKIE_SECURE=1` while still on HTTP — turn it off until certbot is done |
| Logo/avatar upload fails | `practicore/static/uploads` ownership (`practicore:www-data`, 775) |
| Resume upload rejected | packet size: `SHOW VARIABLES LIKE 'max_allowed_packet'` — raise past 5 MB |
| Slow first page / first upload | spaCy model loading — normal, `timeout 120` in `gunicorn.conf.py` covers it |
| No questions in assessments | seed commands in step 4 not run |
| Static files 404 | `alias` path in nginx vs your real project path |

## Why this shape

- **gunicorn, not `python app.py`**: the dev server is single-threaded with
  `debug=True` — unsafe and slow on the open internet.
- **nginx in front**: serves `/static/` without touching Python, buffers slow
  clients, terminates HTTPS via certbot.
- **systemd**: restarts the app on crash/reboot; logs via `journalctl`.
- **`.env` for secrets**: committed code carries zero credentials; the VPS
  `.env` (chmod 600) is the only copy.
