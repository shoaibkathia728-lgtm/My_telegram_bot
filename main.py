import os
import re
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask
import threading

# Flask Web Server setup for Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Running Live!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Email Validation Formula
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@gmail\.com$'
ADMIN_CHAT_ID = 61913474614  # Fully configured with your Admin ID

# Database Setup
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            free_used INTEGER DEFAULT 0,
            is_premium INTEGER DEFAULT 0,
            premium_expiry TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

print("Your Commercial Bot is Running...")

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    # Bot polling logic goes here
  
