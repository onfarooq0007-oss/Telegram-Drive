# ==========================================
# TELEGRAM DRIVE BOT - REQUIREMENTS & INSTALL
# ==========================================

# 1. Install Python
# Recommended: Python 3.10 or 3.11

# Check python version
python --version

# or
python3 --version


# ==========================================
# 2. Create Project Folder
# ==========================================

mkdir telegram-drive-bot
cd telegram-drive-bot


# ==========================================
# 3. Create Virtual Environment (Recommended)
# ==========================================

# Windows
python -m venv venv

# Linux / Ubuntu / VPS / Termux
python3 -m venv venv


# Activate venv

# Windows
venv\Scripts\activate

# Linux / Ubuntu
source venv/bin/activate


# ==========================================
# 4. Install Required Packages
# ==========================================

pip install python-telegram-bot==20.7 Flask==3.0.2


# ==========================================
# 5. Create requirements.txt
# ==========================================

echo python-telegram-bot==20.7 > requirements.txt
echo Flask==3.0.2 >> requirements.txt


# OR manually create file:
# requirements.txt

python-telegram-bot==20.7
Flask==3.0.2


# ==========================================
# 6. Install from requirements.txt
# ==========================================

pip install -r requirements.txt


# ==========================================
# 7. Put Your Bot Code
# ==========================================

# Save file as:
telegram_drive_bot_pro_ultra.py


# ==========================================
# 8. Edit Config in Python File
# ==========================================

BOT_TOKEN = "YOUR_BOT_TOKEN"
CHANNEL_ID = -100xxxxxxxxxx
BASE_URL = "http://YOUR_IP:5000"


# ==========================================
# 9. Run Bot
# ==========================================

python telegram_drive_bot_pro_ultra.py


# ==========================================
# 10. Open Web UI
# ==========================================

http://localhost:5000


# ==========================================
# VPS DEPLOY (Ubuntu)
# ==========================================

sudo apt update
sudo apt install python3 python3-pip python3-venv -y

mkdir drivebot
cd drivebot

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

python telegram_drive_bot_pro_ultra.py


# ==========================================
# OPTIONAL PRO PACKAGES
# ==========================================

pip install gunicorn waitress uvicorn


# ==========================================
# FOR VIDEO THUMBNAILS / CONVERT
# ==========================================

sudo apt install ffmpeg -y


# ==========================================
# COMMON ERRORS FIX
# ==========================================

# If telegram error:
pip install --upgrade python-telegram-bot

# If flask error:
pip install --upgrade Flask

# If port busy:
Change 5000 to 8000


# ==========================================
# FINAL REQUIRED FILES
# ==========================================

telegram_drive_bot_pro_ultra.py
requirements.txt
drive_pro.db   (auto create)


# ==========================================
# BEST HOSTING
# ==========================================

Railway
Render
VPS Ubuntu
Local PC
Termux Android


# ==========================================
# IF YOU WANT NEXT LEVEL:
# ==========================================

# I can give you:

# FULL AUTO INSTALLER
# ONE CLICK VPS DEPLOY
# NGINX DOMAIN SETUP
# HTTPS SSL
# GOOGLE DRIVE UI FRONTEND
# ADMIN PANEL
# APK APP
