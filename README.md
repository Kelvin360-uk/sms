# School Management System (SMS)

A locally-hosted, network-based school management system. Single-server Django + PostgreSQL build with role-based access, audit logging, exam-result and payment workflows, notifications, and messaging.

---

## Contents
1. [What's included](#whats-included)
2. [Roles and what each can do](#roles-and-what-each-can-do)
3. [Setup on the server machine](#setup-on-the-server-machine)
4. [Initial data](#initial-data)
5. [Running the server](#running-the-server)
6. [Connecting other machines on the LAN](#connecting-other-machines-on-the-lan)
7. [Testing on your own laptop](#testing-on-your-own-laptop)
8. [Automated backups and cloud log sync](#automated-backups-and-cloud-log-sync)
9. [Production deployment notes](#production-deployment-notes)
10. [Maintenance checklist](#maintenance-checklist)

---

## What's included

| Module | What it does |
|---|---|
| `apps/users` | Custom User model with 7 roles, login, session-renewal workflow, download permissions |
| `apps/students` | Student profiles (fees, parents, class), gender breakdowns, CSV export |
| `apps/teachers` | Teacher profiles (subjects, classes, class-teacher assignment), CSV export |
| `apps/classes` | School classes + subjects |
| `apps/exams` | Exam sessions, results workflow: Teacher → Class Teacher remarks → Asst Headmaster signature |
| `apps/payments` | Payment ledger, Finance → IT Admin co-approval, immutable post-approval with reversals |
| `apps/audit` | Every action logged with user, IP, table, before/after values |
| `apps/notifications` | In-app notifications, role broadcast |
| `apps/messaging` | Internal messages (default to IT Admin) for access requests / problems |
| `middleware/session_timeout.py` | 120-min teacher sessions, 240-min admin sessions |
| `scripts/cloud_sync.py` | Hourly upload of audit logs to a cloud endpoint when internet detected |
| `scripts/backup_db.py` | Daily PostgreSQL dump + media archive, 30-day retention |
| `scripts/seed_initial_data.py` | First-run seed: admin user, default subjects/classes |

---

## Roles and what each can do

| Role | Can do |
|---|---|
| **IT Admin** | Everything. Approves payments, manages users, grants downloads, handles session renewals, views audit log |
| **Headmaster** | Read-only access to all data, payment ledger, audit log, can approve cash/cheque |
| **Asst Headmaster** | Same as Headmaster + adds remarks and signature to exam reports, sends deadline reminders |
| **Class Teacher** | Edits grades for own class students, adds remarks for each student's report card, views whole class records |
| **Teacher** | Submits exam scores for students they teach. Cannot download anything without explicit permission |
| **Finance** | Temporarily approves payments, records receipts/cheques, views fee balances and class collection performance |
| **HR** | Views student and staff totals and profiles |

---

## Setup on the server machine

The "server" is the one school PC where data lives. Reasonable target: any modern laptop / desktop with 8+ GB RAM running Ubuntu 22.04 or 24.04 LTS.

### 1. Install system packages

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib \
    libpq-dev build-essential git nginx
```

### 2. Create the PostgreSQL database

```bash
sudo -u postgres psql

-- Inside psql:
CREATE DATABASE sms_db;
CREATE USER sms_user WITH PASSWORD 'pick-a-strong-password';
ALTER ROLE sms_user SET client_encoding TO 'utf8';
ALTER ROLE sms_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE sms_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE sms_db TO sms_user;
\q
```

### 3. Get the code and set up Python

```bash
cd /opt
sudo mkdir sms && sudo chown $USER:$USER sms
cd sms
# Copy the project folder here, or git clone
# e.g., unzip sms_project.zip
cd sms_project

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
nano .env
```

Edit the values:
- `SECRET_KEY` — generate one: `python -c "import secrets; print(secrets.token_urlsafe(50))"`
- `DEBUG=False` for production
- `ALLOWED_HOSTS=192.168.1.100,localhost` — the server's LAN IP
- `DB_PASSWORD` — match the password from step 2
- `TEACHER_SESSION_MINUTES=120`
- `CLOUD_SYNC_ENABLED=False` until you set up a cloud endpoint

### 5. Run migrations

```bash
python manage.py makemigrations users classes students teachers exams payments audit notifications messaging
python manage.py migrate
```

### 6. Collect static files

```bash
python manage.py collectstatic --noinput
```

---

## Initial data

Seed the IT Admin user and default classes/subjects:

```bash
python scripts/seed_initial_data.py
```

This creates:
- IT Admin user: `admin` / `ChangeMe123!` **— change immediately on first login**
- Default subjects (Math, English, Science, etc.)
- Default classes (Form 1A, 1B, 2A, 3A)

Log into Django admin at `/admin/` to add school-specific data, or use the web UI.

---

## Running the server

### Development (testing on the server itself):

```bash
python manage.py runserver 0.0.0.0:8000
```

Open `http://localhost:8000` on the server. Login as `admin` / `ChangeMe123!`.

### Production (using gunicorn + nginx):

```bash
pip install gunicorn

# Test gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

Create a systemd service so it auto-starts on boot:

```bash
sudo nano /etc/systemd/system/sms.service
```

```ini
[Unit]
Description=SMS Gunicorn Daemon
After=network.target postgresql.service

[Service]
User=YOUR_USERNAME
Group=www-data
WorkingDirectory=/opt/sms/sms_project
EnvironmentFile=/opt/sms/sms_project/.env
ExecStart=/opt/sms/sms_project/venv/bin/gunicorn \
    --workers 4 \
    --bind unix:/opt/sms/sms_project/sms.sock \
    config.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable sms
sudo systemctl start sms
sudo systemctl status sms
```

Configure nginx (`/etc/nginx/sites-available/sms`):

```nginx
server {
    listen 80;
    server_name 192.168.1.100;  # your server's LAN IP
    client_max_body_size 25M;

    location /static/ {
        alias /opt/sms/sms_project/staticfiles/;
    }
    location /media/ {
        alias /opt/sms/sms_project/media/;
    }
    location / {
        proxy_pass http://unix:/opt/sms/sms_project/sms.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/sms /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Connecting other machines on the LAN

You want teachers, finance, the headmaster, etc. on their own laptops to reach the server.

### 1. Set the server's IP static

On the server:
```bash
ip addr show   # find the LAN interface, e.g. enp3s0 with 192.168.1.100
```

Either configure your router to reserve that IP for the server's MAC, or set it static via netplan (Ubuntu).

### 2. Open the firewall

```bash
sudo ufw allow from 192.168.1.0/24 to any port 80
sudo ufw allow from 192.168.1.0/24 to any port 8000  # if running dev server
sudo ufw enable
```

### 3. From any teacher's laptop on the same Wi-Fi/LAN:

Open a browser, go to `http://192.168.1.100` (your server's IP). That's it.

### 4. (Optional) Give the server a name

On Ubuntu server: `sudo hostnamectl set-hostname school-server`

On Windows clients, edit `C:\Windows\System32\drivers\etc\hosts` and add:
```
192.168.1.100  school-server
```

Now teachers can use `http://school-server` instead of the IP.

### Network segmentation (recommended)

If your router supports VLANs / guest networks, put teachers on a separate subnet from the server infrastructure:

- `192.168.1.0/24` — IT Admin, Finance, Headmaster
- `192.168.2.0/24` — Teachers (read/write the app only)
- `192.168.3.0/24` — Server itself

Configure firewall rules on the router to deny teacher VLAN from reaching anything except port 80 on the server.

---

## Testing on your own laptop

While developing, you can simulate the school network from your own laptop:

### Make your laptop the "server":

```bash
python manage.py runserver 0.0.0.0:8000
```

The `0.0.0.0` tells Django to listen on every network interface, not just localhost.

### Find your laptop's LAN IP:

```bash
# Linux/Mac:
ip addr show | grep "inet "
# Windows:
ipconfig
```

You'll see something like `192.168.0.42`.

### Connect a second machine (phone, tablet, another laptop):

Make sure both devices are on the same Wi-Fi network. From the second device's browser:

```
http://192.168.0.42:8000
```

You should see the login page. Log in with `admin` / `ChangeMe123!`.

### Test multi-user scenarios:

- Open your laptop's browser, log in as IT Admin
- On phone/another machine, log in as a teacher (create the account first)
- Submit an exam result as the teacher
- See the notification on the IT Admin's screen
- Approve payments as Finance from one device, IT Admin from another

---

## Automated backups and cloud log sync

### Set up cron jobs:

```bash
crontab -e
```

Add:
```cron
# Daily DB backup at 2 AM
0 2 * * * cd /opt/sms/sms_project && /opt/sms/sms_project/venv/bin/python scripts/backup_db.py >> logs/backup.log 2>&1

# Hourly cloud log sync (only uploads if internet detected)
0 * * * * cd /opt/sms/sms_project && /opt/sms/sms_project/venv/bin/python scripts/cloud_sync.py >> logs/cloud_sync.log 2>&1
```

### Cloud log sync setup:

The `cloud_sync.py` script checks for internet, then POSTs unsynced audit logs to an endpoint you control.

Edit `.env`:
```
CLOUD_SYNC_ENABLED=True
CLOUD_SYNC_URL=https://your-cloud-endpoint/api/sms-logs
CLOUD_SYNC_API_KEY=your-api-key
```

You'll need to build the cloud-side receiver separately (could be a simple Flask/Django endpoint on a small VPS, or an S3 upload script — adapt `cloud_sync.py` accordingly).

---

## Production deployment notes

- **Always set `DEBUG=False` in production.** Django will refuse to serve when DEBUG is off and `ALLOWED_HOSTS` is empty.
- **Change `SECRET_KEY`** to a long random value. Never commit `.env`.
- **Change the default `admin` password on first login.**
- **HTTPS** is recommended even on a LAN. Use `certbot` for free certificates if your server has any domain, or generate self-signed certs for internal use.
- **PostgreSQL tuning** for ~50 simultaneous teachers: bump `shared_buffers = 512MB`, `work_mem = 16MB`, `effective_cache_size = 2GB` in `/etc/postgresql/*/main/postgresql.conf`.

---

## Maintenance checklist

| When | What |
|---|---|
| Daily (automated) | DB backup runs at 2 AM via cron |
| Hourly (automated) | Cloud sync of audit logs |
| Weekly | Check `logs/backup.log` and `logs/cloud_sync.log` for errors |
| Weekly | Review audit log for anomalies (failed logins, off-hours access) |
| Monthly | Verify a backup restore actually works: `gunzip < backups/sms_backup_*.sql.gz | psql -d test_restore_db` |
| Monthly | Run `apt update && apt upgrade` on the server |
| Per term | Review session-renewal patterns. If too many requests, raise `TEACHER_SESSION_MINUTES` |
| Per year | Archive old audit logs (anything cloud-synced over a year old) |

---

## Quick troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `relation "users_user" does not exist` | Run migrations: `python manage.py migrate` |
| Can't reach server from teacher's laptop | Firewall blocking port 80; check `sudo ufw status` |
| Sessions logging users out instantly | Server clock wrong; sync with `sudo timedatectl set-ntp on` |
| Static files (CSS) not loading in production | Run `python manage.py collectstatic` |
| Payment not reflecting in student balance | Only `APPROVED` payments count; check status in payment detail |
| Teachers see "No teacher profile linked" | Their User record has role but no Teacher profile. Use "Add Staff" to create both together |

---

## Project structure

```
sms_project/
├── apps/                       # All Django apps
│   ├── users/                  # 7-role user model, sessions, downloads
│   ├── students/               # Student profiles, fees
│   ├── teachers/               # Teacher profiles
│   ├── classes/                # SchoolClass and Subject models
│   ├── exams/                  # Exam workflow
│   ├── payments/               # Payment ledger with co-approval
│   ├── audit/                  # Audit log
│   ├── notifications/          # In-app notifications
│   └── messaging/              # Internal messages
├── config/                     # Django settings & root URLs
├── middleware/                 # Session timeout, audit context
├── scripts/                    # Cloud sync, backup, seed
├── templates/                  # All HTML templates
├── static/css/                 # Stylesheet
├── media/                      # User uploads (receipts, notes, profile pics)
├── logs/                       # Application logs
├── backups/                    # DB and media backups
├── .env.example
├── manage.py
├── requirements.txt
└── README.md
```

---

## Architecture decisions baked in

1. **PostgreSQL over SQLite** — Concurrent grade entry needs row-level locks SQLite can't provide.
2. **Finance → IT Admin co-approval** — Two-step approval before payment hits the ledger.
3. **Immutable approved payments** — Once approved, only reversals allowed. Original entry preserved for audit.
4. **Audit on every mutation** — `log_action()` called from every view that modifies data.
5. **Teacher session 120 min** — Long enough for an exam-entry session, short enough to limit unattended-device risk.
6. **Hourly cloud sync, not real-time** — Lower overhead, still gives off-site copy of logs within an hour.
7. **No teacher downloads by default** — Per spec: prevents grade data leaving the system. IT Admin grants time-limited download permissions when needed.
8. **No offline grade entry** — All edits require a live session. Avoids conflict-resolution complexity.

---

## Where to go from here

Once this is running in the school and stable for a term or two, the natural next features are:

- **PDF report card generation** (use `reportlab` or `WeasyPrint` to render full report cards with all signatures)
- **SMS notifications to parents** when payment is received or grades are finalized (use an SMS gateway like Hubtel, Africa's Talking, or Twilio)
- **Parent portal** — read-only access for parents to see their own child's results and fee balance
- **Backup failover system** — the second/third backup tier from the original spec, once you have multiple machines available

These were all in your original ask but deliberately deferred to keep this MVP shippable.
