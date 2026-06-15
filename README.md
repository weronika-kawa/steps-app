# 🏃 Steps App

A simple Flask-based web application for tracking and comparing daily step counts between two users.

Built with:

* Flask
* SQLite
* Gunicorn
* Nginx (optional, production deployment)
* Progressive Web App (PWA) support

---

# 📊 Features

* 🏃 Daily step tracking for two competitors
* 📅 Add and edit step entries for any day
* 🏆 Automatic daily winner calculation
* 📈 Overall leaderboard based on cumulative steps
* 🎯 Daily goal enforcement (11,000 step cap)
* 📊 Progress dashboard with performance summaries
* 📚 Full historical activity archive
* 📱 Progressive Web App (PWA) support
* 🔌 Offline-first experience with sync capability
* 💾 Lightweight SQLite database
* 🔄 JSON API for integrations and synchronization

---

# ⚙️ Requirements

Before starting, ensure:

* Python 3.14+ (or compatible Python 3 version)
* Git

Check installation:

```bash
python3 --version
git --version
```

---

# 📦 Installation

## 1. Clone repository

```bash
git clone https://github.com/weronika-kawa/steps-app.git
cd steps-app
```

---

## 2. Create virtual environment

```bash
python3 -m venv venv
```

Activate:

### Linux / macOS / Ubuntu

```bash
source venv/bin/activate
```

### Windows (PowerShell)

```powershell
venv\Scripts\Activate.ps1
```

---

## 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4. Environment variables

Create `.env`:

```bash
nano .env
```

Add:

```env
SECRET_KEY=change-me-to-a-random-secret-string
```

---

## 5. Run app

```bash
python app.py
```

App runs at:

```
http://127.0.0.1:5000
```

---

# 🗄️ Database

SQLite database is created automatically on first run.

File:

```
steps_app.db
```

---

# 🚀 Production (Gunicorn)

```bash
gunicorn -w 2 -b 127.0.0.1:8000 app:app
```

---

# 🌐 Deployment (Ubuntu + Nginx)

## Gunicorn (socket mode)

```bash
gunicorn \
  -w 2 \
  --bind unix:/home/USERNAME/steps-app/steps-app.sock \
  app:app
```

---

## Nginx config

```nginx
server {
    listen 80;

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/USERNAME/steps-app/steps-app.sock;
    }
}
```

---

# 🔄 Update app

```bash
git pull origin main
sudo systemctl restart steps-app
```

---

# 📁 Project structure

```
steps-app/
├── app.py
├── requirements.txt
├── .env
├── steps_app.db
├── steps_app.sock
├── deploy.sh
├── static/
├── templates/
├── venv/
└── README.md
```

---

# 🚫 .gitignore

```
venv/
__pycache__/
*.pyc
.env
steps_app.db
steps-app.sock
```

---

# 🚀 Deployment workflow

## Local

```bash
git add .
git commit -m "Update feature"
git push origin main
```

## Server

```bash
git pull origin main
sudo systemctl restart steps-app
```

---

# 🔮 Future improvements

* Docker support
* GitHub Actions CI/CD
* PostgreSQL migration
* HTTPS via Let’s Encrypt
* Automated backups

---

# 📄 License

For educational and personal use.

---
