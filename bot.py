import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# Логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота
TOKEN = os.environ.get('BOT_TOKEN', '')

# Стани розмови
(
    MAIN_MENU,
    GET_DATE,
    GET_LAST_NAME,
    GET_FIRST_NAME,
    GET_PATRONYMIC,
    GET_GENDER,
    GET_DOB,
    GET_PASSPORT,
    GET_PHONE,
    GET_SETTLEMENT,
    GET_DISABILITY,
    CONFIRM
) = range(12)

# Підключення до Google Sheets
def get_sheet():
    try:
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        creds_dict = {
            "type": "service_account",
            "project_id": os.environ.get('GOOGLE_PROJECT_ID', ''),
            "private_key_id": os.environ.get('GOOGLE_PRIVATE_KEY_ID', ''),
            "private_key": os.environ.get('GOOGLE_PRIVATE_KEY', '').replace('\\n', '\n'),
            "client_email": os.environ.get('GOOGLE_CLIENT_EMAIL', ''),
            "client_id": os.environ.get('GOOGLE_CLIENT_ID', ''),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(os.environ.get('GOOGLE_SHEET_ID', '')).sheet1
        return sheet
    except Exception as e:
        logger.error(f"Помилка підключення до Google Sheets: {e}")
        return None

# Головне меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("➕ Додати евакуйованого")],
        [KeyboardButton("📊 Статистика сьогодні")],
        [KeyboardButton("ℹ️ Допомога")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🕊️ *Місія Подих Надії*\n\n"
        "Вітаю! Оберіть дію:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return MAIN_MENU

# Обробка головного меню
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "➕ Додати евакуйованого":
        await update.message.reply_text(
            "📅 Введіть дату евакуації\n"
            "Формат: ДД.ММ.РРРР\n"
            "Наприклад: 24.06.2026"
        )
        return GET_DATE

    elif text == "📊 Статистика сьогодні":
        await show_stats(update, context)
        return MAIN_MENU

    elif text == "ℹ️ Допомога":
        await update.message.reply_text(
            "📋 *Як користуватися ботом:*\n\n"
            "1️⃣ Натисніть '➕ Додати евакуйованого'\n"
            "2️⃣ Введіть дані по кроках\n"
            "3️⃣ Підтвердіть запис\n\n"
            "Дані автоматично зберігаються в базу.",
            parse_mode='Markdown'
        )
        return MAIN_MENU

# Статистика
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sheet = get_sheet()
        if not sheet:
            await update.message.reply_text("❌ Помилка підключення до бази даних.")
            return

        today = datetime.now().strftime('%d.%m.%Y')
        all_records = sheet.get_all_records()

        today_records = [r for r in all_records if str(r.get('Date', '')) == today]
        total = len(all_records)
        today_count = len(today_records)

        women = sum(1 for r in all_records if r.get('Gender') == 'F')
        men = sum(1 for r in all_records if r.get('Gender') in ['M', 'М'])
        disabled = sum(1 for r in all_records if str(r.get('Person with disability', '')).lower() == 'yes')

        await update.message.reply_text(
            f"📊 *Статистика*\n\n"
            f"📅 Сьогодні ({today}): *{today_count}* осіб\n"
            f"📁 Всього в базі: *{total}* осіб\n\n"
            f"👩 Жінок: *{women}*\n"
            f"👨 Чоловіків: *{men}*\n"
            f"♿ З інвалідністю: *{disabled}*",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Помилка: {e}")

# Збір даних — дата
async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['date'] = update.message.text
    await update.message.reply_text("👤 Прізвище:")
    return GET_LAST_NAME

async def get_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['last_name'] = update.message.text
    await update.message.reply_text("👤 Ім'я:")
    return GET_FIRST_NAME

async def get_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['first_name'] = update.message.text
    await update.message.reply_text("👤 По батькові:")
    return GET_PATRONYMIC

async def get_patronymic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['patronymic'] = update.message.text

    keyboard = [[KeyboardButton("👩 Жінка"), KeyboardButton("👨 Чоловік")]]
    await update.message.reply_text(
        "⚥ Стать:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return GET_GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data['gender'] = 'F' if 'Жінка' in text else 'M'
    await update.message.reply_text(
        "🎂 Дата народження:\n"
        "Формат: ДД.ММ.РРРР\n"
        "Наприклад: 15.03.1950"
    )
    return GET_DOB

async def get_dob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['dob'] = update.message.text
    await update.message.reply_text(
        "🪪 Серія та номер паспорта або ID:\n"
        "Наприклад: ВА123456\n"
        "Якщо немає — напишіть: немає"
    )
    return GET_PASSPORT

async def get_passport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['passport'] = update.message.text
    await update.message.reply_text(
        "📱 Номер телефону:\n"
        "Наприклад: 0501234567\n"
        "Якщо немає — напишіть: немає"
    )
    return GET_PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    await update.message.reply_text(
        "🏘️ Населений пункт (звідки евакуйований):\n"
        "Наприклад: Druzhkivka"
    )
    return GET_SETTLEMENT

async def get_settlement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['settlement'] = update.message.text

    keyboard = [[KeyboardButton("✅ Так"), KeyboardButton("❌ Ні")]]
    await update.message.reply_text(
        "♿ Особа з інвалідністю?",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return GET_DISABILITY

async def get_disability(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data['disability'] = 'yes' if '✅' in text else 'no'

    d = context.user_data
    gender_text = '👩 Жінка' if d.get('gender') == 'F' else '👨 Чоловік'
    disability_text = '✅ Так' if d.get('disability') == 'yes' else '❌ Ні'

    summary = (
        f"📋 *Перевірте дані:*\n\n"
        f"📅 Дата: {d.get('date', '')}\n"
        f"👤 ПІБ: {d.get('last_name', '')} {d.get('first_name', '')} {d.get('patronymic', '')}\n"
        f"⚥ Стать: {gender_text}\n"
        f"🎂 Дата народження: {d.get('dob', '')}\n"
        f"🪪 Паспорт: {d.get('passport', '')}\n"
        f"📱 Телефон: {d.get('phone', '')}\n"
        f"🏘️ Населений пункт: {d.get('settlement', '')}\n"
        f"♿ Інвалідність: {disability_text}\n\n"
        f"Все вірно?"
    )

    keyboard = [[KeyboardButton("✅ Зберегти"), KeyboardButton("❌ Скасувати")]]
    await update.message.reply_text(
        summary,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
        parse_mode='Markdown'
    )
    return CONFIRM

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if '✅' in text:
        try:
            sheet = get_sheet()
            if sheet:
                d = context.user_data
                row = [
                    'yes',
                    d.get('date', ''),
                    'Evacuation',
                    d.get('last_name', ''),
                    d.get('first_name', ''),
                    d.get('patronymic', ''),
                    '',
                    d.get('passport', ''),
                    d.get('gender', ''),
                    d.get('disability', 'no'),
                    d.get('dob', ''),
                    '',
                    d.get('phone', ''),
                    d.get('settlement', ''),
                    'Kramatorsk',
                    'Kramatorsk',
                    'Donetsk'
                ]
                sheet.append_row(row)
                await update.message.reply_text(
                    "✅ *Збережено!*\n\nДані записано в базу.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Помилка підключення до бази.")
        except Exception as e:
            await update.message.reply_text(f"❌ Помилка збереження: {e}")
    else:
        await update.message.reply_text("❌ Скасовано. Дані не збережено.")

    context.user_data.clear()
    return await start(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Скасовано.")
    return await start(update, context)

def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu)
        ],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu)],
            GET_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)],
            GET_LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_last_name)],
            GET_FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_first_name)],
            GET_PATRONYMIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_patronymic)],
            GET_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            GET_DOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_dob)],
            GET_PASSPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_passport)],
            GET_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            GET_SETTLEMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_settlement)],
            GET_DISABILITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_disability)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
