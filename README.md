# Steps App

A simple Flask-based web application for tracking and comparing daily step counts between two users.

The application uses:

* Flask
* SQLite
* Gunicorn
* Nginx (optional, for production)
* Progressive Web App (PWA) support

---

# Features

- 🏃 Daily step tracking for two competitors
- 📅 Log steps for any day and edit previous entries
- 🏆 Automatic daily winner determination
- 📈 Overall leaderboard based on cumulative steps
- 🎯 Daily goal enforcement (11,000 step cap)
- 📊 Progress dashboard and performance summaries
- 📚 Complete historical activity archive
- 📱 Progressive Web App (PWA) support
- 🔌 Offline-first experience with automatic synchronization
- 💾 Lightweight SQLite database
- 🔄 JSON API for integrations and synchronization

---

# Requirements

Before starting, make sure the following software is installed:

* Python 3.14+ (or compatible Python 3 version)
* Git

Check your installation:

```bash
python3 --version
git --version
```

---

# Installation

## 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/steps-app.git
cd steps-app
```

Replace `YOUR_USERNAME` with the actual GitHub username.

---

## 2. Create a virtual environment

Create an isolated Python environment:

```bash
python3 -m venv venv
```

Activate it:

### Linux / Ubuntu / macOS

```bash
source venv/bin/activate
```

### Windows (PowerShell)

```powershell
venv\Scripts\Activate.ps1
```

You should now see `(venv)` at the beginning of your terminal prompt.

---

## 3. Install dependencies

Upgrade pip:

```bash
pip install --upgrade pip
```

Install project dependencies:

```bash
pip install -r requirements.txt
```

---

## 4. Create environment variables

Create a `.env` file:

```bash
nano .env
```

Add:

```env
SECRET_KEY=change-me-to-a-random-secret-string
```

Save the file.

---

## 5. Start the application

Run:

```bash
python app.py
```

You should see something similar to:

```text
* Running on http://127.0.0.1:5000
```

---

## 6. Open the application

Open your browser and visit:

```text
http://127.0.0.1:5000
```

The application should now be running.

---

# Database

The application automatically creates the SQLite database on first startup.

Database file:

```text
steps_app.db
```

No manual database setup is required.

---

# Running with Gunicorn

For a more production-like setup:

```bash
gunicorn -w 2 -b 127.0.0.1:8000 app:app
```

Open:

```text
http://127.0.0.1:8000
```

---

# Production Deployment (Ubuntu + Nginx)

This section assumes:

* Ubuntu Server
* Nginx installed
* Application located in:

```text
/home/USERNAME/steps-app
```

---

## Start Gunicorn with a Unix Socket

Activate the virtual environment:

```bash
source venv/bin/activate
```

Run:

```bash
gunicorn \
  -w 2 \
  --bind unix:/home/USERNAME/steps-app/steps-app.sock \
  app:app
```

---

## Nginx Configuration

Create:

```bash
sudo nano /etc/nginx/sites-available/steps_app
```

Add:

```nginx
server {
    listen 80;

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/USERNAME/steps-app/steps-app.sock;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/steps_app /etc/nginx/sites-enabled/
```

Test configuration:

```bash
sudo nginx -t
```

Restart Nginx:

```bash
sudo systemctl restart nginx
```

---

# Updating the Application

Pull the latest version from GitHub:

```bash
git pull origin main
```

Restart the service:

```bash
sudo systemctl restart steps-app
```

---

# Project Structure

```text
steps-app/
├── app.py
├── requirements.txt
├── .env
├── steps_app.db
├── static/
├── templates/
├── venv/
└── README.md
```

---

# Files That Should NOT Be Committed

The following files should be excluded using `.gitignore`:

```text
venv/
__pycache__/
*.pyc
.env
steps_app.db
```

---

# Future Improvements

Possible future enhancements:

* Docker deployment
* GitHub Actions CI/CD
* PostgreSQL support
* HTTPS with Let's Encrypt
* Automated backups

---

# License

This project is provided for educational and personal use.
