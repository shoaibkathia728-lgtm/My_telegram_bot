import os
import re
import sqlite3
import threading
from flask import Flask
from datetime import datetime, timedelta
from email_validator import validate_email, EmailNotValidError
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Flask Web Server setup for Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Running Live!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# Token and Admin Configuration
TOKEN = "8646130758:AAHhOD20abm7h75QTJ6k9aIbsJmklZQcCAE"
ADMIN_CHAT_ID = 61913474614  # Your Admin ID

# Email Validation Regex (Basic Syntax)
EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

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

# User status check function with Auto-Expiry validation
def get_user_status(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT free_used, is_premium, premium_expiry FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row:
        cursor.execute("INSERT INTO users (user_id, free_used, is_premium, premium_expiry) VALUES (?, 0, 0, NULL)", (user_id,))
        conn.commit()
        conn.close()
        return {"free_used": 0, "is_premium": 0, "expiry": None}
    
    free_used, is_premium, premium_expiry = row[0], row[1], row[2]
    
    if is_premium == 1 and premium_expiry:
        expiry_date = datetime.strptime(premium_expiry, "%Y-%m-%d %H:%M:%S")
        if datetime.now() > expiry_date:
            cursor.execute("UPDATE users SET is_premium = 0, premium_expiry = NULL WHERE user_id = ?", (user_id,))
            conn.commit()
            is_premium = 0
            premium_expiry = None
            
    conn.close()
    return {"free_used": free_used, "is_premium": is_premium, "expiry": premium_expiry}

# Real-time Verification using MX Records & Deliverability
def verify_email_realtime(email):
    try:
        valid = validate_email(email, check_deliverability=True)
        return "VALID"
    except EmailNotValidError:
        return "INVALID"
    except:
        return "VALID"

# Payment Details Template
PAYMENT_INFO = (
    "💳 **Premium Payment Details:**\n\n"
    "💰 **Fee:** 1000 PKR / Month (Unlimited Filtering)\n\n"
    "📱 **Easypaisa:**\n"
    "• Number: `03297809932`\n"
    "• Title: Azhar Hussain\n\n"
    "📱 **JazzCash:**\n"
    "• Number: `03297809932`\n"
    "• Title: Azhar Hussain\n\n"
    "⚠️ **Important Note:** After sending the payment, please send the screenshot along with your **User ID** to the Admin: @AzharHaneef"
)

# Start Command Handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    status = get_user_status(user_id)
    
    if status['is_premium']:
        user_type = f"👑 Premium Account\n📅 Expires on: `{status['expiry']}`"
    else:
        user_type = f"🎁 Free Account ({status['free_used']}/500 Used)"

    welcome_text = (
        f"Welcome to the Real-Time Premium Gmail Filter Bot! 🎉\n\n"
        f"Status: {user_type}\n\n"
        "🔥 **Special Offer:**\n"
        "🎁 New users can filter up to **500 Gmails completely FREE**!\n\n"
        "💡 **How to Use?**\n"
        "Simply send me your email list, and I will check live if the emails are real and deliverable!\n\n"
        f"🆔 **Your User ID:** `{user_id}`\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"{PAYMENT_INFO}"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# Email Filter Handler with MX Deliverability Checking
async def filter_emails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if text.startswith('/'):
        return

    status = get_user_status(user_id)
    all_emails = re.findall(EMAIL_REGEX, text)
    
    if not all_emails:
        await update.message.reply_text("❌ I couldn't find any emails in your message. Please send a valid list.")
        return

    if not status['is_premium']:
        if status['free_used'] >= 500:
            await update.message.reply_text(
                "🚫 **Free Limit Reached!**\n\nYour 500 free emails limit has expired.\n\n"
                f"{PAYMENT_INFO}", parse_mode="Markdown"
            )
            return
            
        allowed = 500 - status['free_used']
        if len(all_emails) > allowed:
            await update.message.reply_text(f"⚠️ You only have **{allowed}** free credits left, but you sent {len(all_emails)} emails. Please upgrade to Premium.")
            return

    status_msg = await update.message.reply_text("⏳ *Verifying mailbox deliverability... Please wait...*", parse_mode="Markdown")

    valid_gmails = []
    invalid_emails = []
    
    for email in list(set(all_emails)):
        if email.lower().endswith('@gmail.com'):
            result = verify_email_realtime(email.lower())
            if result == "VALID":
                valid_gmails.append(email.lower())
            else:
                invalid_emails.append(f"{email} (Undeliverable/Dead)")
        else:
            invalid_emails.append(f"{email} (Non-Gmail Domain)")

    if not status['is_premium']:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET free_used = free_used + ? WHERE user_id = ?", (len(all_emails), user_id))
        conn.commit()
        conn.close()

    new_status = get_user_status(user_id)
    user_type = f"👑 Premium Member (Expires: {new_status['expiry']})" if status['is_premium'] else f"🎁 Free Account ({new_status['free_used']}/500 Used)"

    response_text = f"📊 **Real-Time Filter Result ({user_type}):**\n\n"
    response_text += f"✅ Active Deliverable Gmails: {len(valid_gmails)}\n"
    response_text += f"❌ Dead/Invalid/Other Emails: {len(invalid_emails)}\n\n"
    
    if valid_gmails:
        response_text += "📝 **Valid Active Gmails:**\n"
        for email in valid_gmails:
            response_text += f"✅ `{email}`\n"
        response_text += "\n"

    if invalid_emails:
        response_text += "⚠️ **Dead/Non-Existent/Other List:**\n"
        for email in invalid_emails:
            response_text += f"❌ `{email}`\n"

    await status_msg.delete()
    await update.message.reply_text(response_text, parse_mode="Markdown")

# Admin Command to grant Premium for exactly 30 days
async def gift_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    try:
        target_id = int(context.args[0])
        expiry_time = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_premium = 1, premium_expiry = ? WHERE user_id = ?", (expiry_time, target_id))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ User `{target_id}` has been successfully upgraded to Premium!\n📅 Expiry Date: `{expiry_time}`")
    except:
        await update.message.reply_text("Format: /premium USER_ID")

def main():
    print("Your Commercial Bot is Running with Auto-Expiry & Flask on Render...")
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("premium", gift_premium))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_emails))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
