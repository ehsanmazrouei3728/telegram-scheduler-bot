import os
import json
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

TOKEN = os.getenv("BOT_TOKEN")
DATA_FILE = "schedules.json"


def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "users": {},
            "schedules": []
        }

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "users": {},
            "schedules": []
        }


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id

    data = load_data()

    data["users"][str(user.id)] = {
        "chat_id": chat_id,
        "username": user.username or ""
    }

    save_data(data)

    await update.message.reply_text(
        "سلام 👋\n\n"
        "شناسه شما ثبت شد ✅\n\n"
        "برای ساخت زمان‌بندی از این فرمت استفاده کن:\n\n"
        "/schedule ساعت تعداد_روز پیام\n\n"
        "مثال:\n"
        "/schedule 18:30 7 سلام، وقت بخیر!\n\n"
        "یعنی هر روز ساعت 18:30 به مدت 7 روز پیام ارسال شود.\n\n"
        "برای دیدن زمان‌بندی‌ها:\n"
        "/list\n\n"
        "برای حذف همه زمان‌بندی‌ها:\n"
        "/clear"
    )


async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text(
            "❌ فرمت اشتباه است.\n\n"
            "مثال:\n"
            "/schedule 18:30 7 سلام، وقت بخیر!"
        )
        return

    time_text = context.args[0]
    days_text = context.args[1]
    message = " ".join(context.args[2:])

    try:
        datetime.strptime(time_text, "%H:%M")
        days = int(days_text)

        if days < 1:
            raise ValueError

    except ValueError:
        await update.message.reply_text(
            "❌ ساعت باید مثل 18:30 باشد و تعداد روز باید عدد مثبت باشد."
        )
        return

    data = load_data()

    user_id = str(update.effective_user.id)

    if user_id not in data["users"]:
        await update.message.reply_text(
            "❌ ابتدا /start را بزن."
        )
        return

    schedule_data = {
        "id": len(data["schedules"]) + 1,
        "user_id": user_id,
        "chat_id": update.effective_chat.id,
        "time": time_text,
        "days_left": days,
        "message": message,
        "last_sent": ""
    }

    data["schedules"].append(schedule_data)
    save_data(data)

    await update.message.reply_text(
        f"✅ زمان‌بندی ساخته شد.\n\n"
        f"⏰ ساعت: {time_text}\n"
        f"📅 تعداد روز: {days}\n"
        f"💬 پیام: {message}"
    )


async def list_schedules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()

    user_id = str(update.effective_user.id)

    user_schedules = [
        s for s in data["schedules"]
        if s["user_id"] == user_id
    ]

    if not user_schedules:
        await update.message.reply_text(
            "📭 هیچ زمان‌بندی‌ای نداری."
        )
        return

    text = "📋 زمان‌بندی‌های شما:\n\n"

    for s in user_schedules:
        text += (
            f"🆔 {s['id']}\n"
            f"⏰ ساعت: {s['time']}\n"
            f"📅 روز باقی‌مانده: {s['days_left']}\n"
            f"💬 پیام: {s['message']}\n\n"
        )

    await update.message.reply_text(text)


async def clear_schedules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()

    user_id = str(update.effective_user.id)

    data["schedules"] = [
        s for s in data["schedules"]
        if s["user_id"] != user_id
    ]

    save_data(data)

    await update.message.reply_text(
        "🗑 تمام زمان‌بندی‌های شما حذف شدند."
    )


async def send_scheduled_messages(context: ContextTypes.DEFAULT_TYPE):
    data = load_data()

    now = datetime.now()
    current_time = now.strftime("%H:%M")
    today = now.strftime("%Y-%m-%d")

    changed = False

    for schedule in data["schedules"][:]:

        # جلوگیری از ارسال چندباره در یک روز
        if schedule.get("last_sent") == today:
            continue

        if schedule["time"] != current_time:
            continue

        try:
            await context.bot.send_message(
                chat_id=schedule["chat_id"],
                text=schedule["message"]
            )

            schedule["last_sent"] = today
            schedule["days_left"] -= 1

            changed = True

            print(
                f"Message sent to {schedule['chat_id']} "
                f"at {current_time}"
            )

            if schedule["days_left"] <= 0:
                data["schedules"].remove(schedule)

        except Exception as e:
            print(
                f"Error sending message to "
                f"{schedule['chat_id']}: {e}"
            )

    if changed:
        save_data(data)


def main():
    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable is not set."
        )

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("schedule", schedule)
    )

    app.add_handler(
        CommandHandler("list", list_schedules)
    )

    app.add_handler(
        CommandHandler("clear", clear_schedules)
    )

    # بررسی هر 30 ثانیه
    app.job_queue.run_repeating(
        send_scheduled_messages,
        interval=30,
        first=5
    )

    print("Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()


