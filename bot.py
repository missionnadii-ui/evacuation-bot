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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('BOT_TOKEN', '')

# ===== СТАНИ =====
(
    MAIN_MENU,
    # Евакуйовані
    EV_DATE, EV_LAST_NAME, EV_FIRST_NAME, EV_PATRONYMIC,
    EV_GENDER, EV_DOB, EV_PASSPORT, EV_PHONE,
    EV_SETTLEMENT, EV_DISABILITY, EV_CONFIRM,
    # Путьовий лист
    TR_CAR, TR_DRIVER, TR_DATE, TR_TIME_OUT, TR_TIME_IN,
    TR_ROUTE, TR_ODO_START, TR_ODO_END, TR_FUEL, TR_NOTES, TR_CONFIRM
) = range(23)

CARS = ["🔵 VW T5 Синій (МІС ВУ82)", "⬜ VW T5 Білий"]
DRIVERS = ["Савченко Влад", "Ткаченко Олег"]

# ===== GOOGLE SHEETS =====
def get_sheet(sheet_name='Sheet1'):
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
        spreadsheet = client.open_by_key(os.environ.get('GOOGLE_SHEET_ID', ''))
        try:
            return spreadsheet.worksheet(sheet_name)
        except:
            return spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
    except Exception as e:
        logger.error(f"Помилка Google Sheets: {e}")
        return None

# ===== ГОЛОВНЕ МЕНЮ =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("➕ Додати евакуйованого")],
        [KeyboardButton("🚐 Путьовий лист")],
        [KeyboardButton("📊 Статистика")],
        [KeyboardButton("ℹ️ Допомога")]
    ]
    await update.message.reply_text(
        "🕊️ *Місія Подих Надії*\n\nОберіть дію:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode='Markdown'
    )
    return MAIN_MENU

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "➕ Додати евакуйованого":
        await update.message.reply_text("📅 Введіть дату евакуації (ДД.ММ.РРРР):")
        return EV_DATE
    elif text == "🚐 Путьовий лист":
        keyboard = [[KeyboardButton(c)] for c in CARS]
        await update.message.reply_text(
            "🚐 Оберіть автомобіль:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        )
        return TR_CAR
    elif text == "📊 Статистика":
        await show_stats(update, context)
        return MAIN_MENU
    elif text == "ℹ️ Допомога":
        await update.message.reply_text(
            "📋 *Як користуватися:*\n\n"
            "➕ *Додати евакуйованого* — реєстрація людини\n"
            "🚐 *Путьовий лист* — облік рейсу машини\n"
            "📊 *Статистика* — зведені дані\n\n"
            "Всі дані зберігаються в Google Sheets.",
            parse_mode='Markdown'
        )
        return MAIN_MENU
    return MAIN_MENU

# ===== СТАТИСТИКА =====
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sheet = get_sheet('Sheet1')
        trips_sheet = get_sheet('Путьові листи')

        today = datetime.now().strftime('%d.%m.%Y')
        stats_text = f"📊 *Статистика на {today}*\n\n"

        if sheet:
            records = sheet.get_all_records()
            today_ev = [r for r in records if str(r.get('Date', '')) == today]
            women = sum(1 for r in records if r.get('Gender') == 'F')
            men = sum(1 for r in records if r.get('Gender') in ['M', 'М'])
            disabled = sum(1 for r in records if str(r.get('Person with disability', '')).lower() == 'yes')
            stats_text += (
                f"👥 *Евакуйовані:*\n"
                f"  Сьогодні: *{len(today_ev)}* осіб\n"
                f"  Всього в базі: *{len(records)}* осіб\n"
                f"  👩 Жінок: *{women}* | 👨 Чоловіків: *{men}*\n"
                f"  ♿ З інвалідністю: *{disabled}*\n\n"
            )

        if trips_sheet:
            trips = trips_sheet.get_all_records()
            today_trips = [t for t in trips if str(t.get('Дата', '')) == today]
            total_km = sum(int(str(t.get('Пробіг км', 0)).replace('км','').strip() or 0) for t in trips if t.get('Пробіг км'))
            total_fuel = sum(float(str(t.get('Заправка літрів', 0)).replace('л','').strip() or 0) for t in trips if t.get('Заправка літрів'))
            stats_text += (
                f"🚐 *Рейси:*\n"
                f"  Сьогодні: *{len(today_trips)}* рейсів\n"
                f"  Всього рейсів: *{len(trips)}*\n"
                f"  🛣️ Загальний пробіг: *{total_km} км*\n"
                f"  ⛽ Заправлено разом: *{total_fuel:.0f} л*"
            )

        await update.message.reply_text(stats_text, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Помилка: {e}")

# ===== ЕВАКУЙОВАНІ =====
async def ev_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['date'] = update.message.text
    await update.message.reply_text("👤 Прізвище:")
    return EV_LAST_NAME

async def ev_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['last_name'] = update.message.text
    await update.message.reply_text("👤 Ім'я:")
    return EV_FIRST_NAME

async def ev_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['first_name'] = update.message.text
    await update.message.reply_text("👤 По батькові:")
    return EV_PATRONYMIC

async def ev_patronymic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['patronymic'] = update.message.text
    keyboard = [[KeyboardButton("👩 Жінка"), KeyboardButton("👨 Чоловік")]]
    await update.message.reply_text(
        "⚥ Стать:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return EV_GENDER

async def ev_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gender'] = 'F' if 'Жінка' in update.message.text else 'M'
    await update.message.reply_text("🎂 Дата народження (ДД.ММ.РРРР):")
    return EV_DOB

async def ev_dob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['dob'] = update.message.text
    await update.message.reply_text("🪪 Серія та номер паспорта (або: немає / згорів):")
    return EV_PASSPORT

async def ev_passport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['passport'] = update.message.text
    await update.message.reply_text("📱 Номер телефону (або: немає):")
    return EV_PHONE

async def ev_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("🏘️ Населений пункт (звідки евакуйований):")
    return EV_SETTLEMENT

async def ev_settlement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['settlement'] = update.message.text
    keyboard = [[KeyboardButton("✅ Так"), KeyboardButton("❌ Ні")]]
    await update.message.reply_text(
        "♿ Особа з інвалідністю?",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return EV_DISABILITY

async def ev_disability(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['disability'] = 'yes' if '✅' in update.message.text else 'no'
    d = context.user_data
    summary = (
        f"📋 *Перевірте дані:*\n\n"
        f"📅 Дата: {d.get('date')}\n"
        f"👤 ПІБ: {d.get('last_name')} {d.get('first_name')} {d.get('patronymic')}\n"
        f"⚥ Стать: {'👩 Жінка' if d.get('gender')=='F' else '👨 Чоловік'}\n"
        f"🎂 Дата народження: {d.get('dob')}\n"
        f"🪪 Паспорт: {d.get('passport')}\n"
        f"📱 Телефон: {d.get('phone')}\n"
        f"🏘️ Населений пункт: {d.get('settlement')}\n"
        f"♿ Інвалідність: {'✅ Так' if d.get('disability')=='yes' else '❌ Ні'}\n\n"
        f"Все вірно?"
    )
    keyboard = [[KeyboardButton("✅ Зберегти"), KeyboardButton("❌ Скасувати")]]
    await update.message.reply_text(
        summary,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
        parse_mode='Markdown'
    )
    return EV_CONFIRM

async def ev_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if '✅' in update.message.text:
        try:
            sheet = get_sheet('Sheet1')
            if sheet:
                d = context.user_data
                sheet.append_row([
                    'yes', d.get('date'), 'Evacuation',
                    d.get('last_name'), d.get('first_name'), d.get('patronymic'),
                    '', d.get('passport'), d.get('gender'), d.get('disability'),
                    d.get('dob'), '', d.get('phone'), d.get('settlement'),
                    'Kramatorsk', 'Kramatorsk', 'Donetsk'
                ])
                await update.message.reply_text("✅ *Збережено в базу!*", parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Помилка підключення до бази.")
        except Exception as e:
            await update.message.reply_text(f"❌ Помилка: {e}")
    else:
        await update.message.reply_text("❌ Скасовано.")
    context.user_data.clear()
    return await start(update, context)

# ===== ПУТЬОВИЙ ЛИСТ =====
async def tr_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['car'] = update.message.text
    keyboard = [[KeyboardButton(d)] for d in DRIVERS]
    await update.message.reply_text(
        "👤 Оберіть водія:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return TR_DRIVER

async def tr_driver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['driver'] = update.message.text
    await update.message.reply_text("📅 Дата рейсу (ДД.ММ.РРРР):")
    return TR_DATE

async def tr_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['tr_date'] = update.message.text
    await update.message.reply_text("⏰ Час виїзду (наприклад: 08:30):")
    return TR_TIME_OUT

async def tr_time_out(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['time_out'] = update.message.text
    await update.message.reply_text("⏰ Час повернення (наприклад: 15:45):")
    return TR_TIME_IN

async def tr_time_in(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['time_in'] = update.message.text
    await update.message.reply_text("📍 Маршрут (наприклад: Слов'янськ — Дружківка):")
    return TR_ROUTE

async def tr_route(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['route'] = update.message.text
    await update.message.reply_text("🔢 Показники спідометра на виїзді (км):")
    return TR_ODO_START

async def tr_odo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['odo_start'] = update.message.text
    await update.message.reply_text("🔢 Показники спідометра на поверненні (км):")
    return TR_ODO_END

async def tr_odo_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['odo_end'] = update.message.text
    try:
        km = int(context.user_data['odo_end']) - int(context.user_data['odo_start'])
        context.user_data['km'] = km
    except:
        context.user_data['km'] = 0
    await update.message.reply_text("⛽ Заправка (літрів, або: 0 якщо не заправляли):")
    return TR_FUEL

async def tr_fuel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['fuel'] = update.message.text
    await update.message.reply_text("📝 Примітки (або: немає):")
    return TR_NOTES

async def tr_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['notes'] = update.message.text
    d = context.user_data
    summary = (
        f"🚐 *Перевірте путьовий лист:*\n\n"
        f"🚗 Авто: {d.get('car')}\n"
        f"👤 Водій: {d.get('driver')}\n"
        f"📅 Дата: {d.get('tr_date')}\n"
        f"⏰ Виїзд: {d.get('time_out')} → Повернення: {d.get('time_in')}\n"
        f"📍 Маршрут: {d.get('route')}\n"
        f"🔢 Спідометр: {d.get('odo_start')} → {d.get('odo_end')}\n"
        f"🛣️ Пробіг: *{d.get('km')} км*\n"
        f"⛽ Заправка: {d.get('fuel')} л\n"
        f"📝 Примітки: {d.get('notes')}\n\n"
        f"Все вірно?"
    )
    keyboard = [[KeyboardButton("✅ Зберегти"), KeyboardButton("❌ Скасувати")]]
    await update.message.reply_text(
        summary,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
        parse_mode='Markdown'
    )
    return TR_CONFIRM

async def tr_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if '✅' in update.message.text:
        try:
            sheet = get_sheet('Путьові листи')
            if sheet:
                # Перевіряємо заголовки
                try:
                    sheet.row_values(1)
                except:
                    sheet.append_row([
                        'Авто', 'Водій', 'Дата', 'Час виїзду', 'Час повернення',
                        'Маршрут', 'Спідометр початок', 'Спідометр кінець',
                        'Пробіг км', 'Заправка літрів', 'Примітки'
                    ])
                d = context.user_data
                sheet.append_row([
                    d.get('car'), d.get('driver'), d.get('tr_date'),
                    d.get('time_out'), d.get('time_in'), d.get('route'),
                    d.get('odo_start'), d.get('odo_end'), d.get('km'),
                    d.get('fuel'), d.get('notes')
                ])
                await update.message.reply_text(
                    f"✅ *Путьовий лист збережено!*\n🛣️ Пробіг: {d.get('km')} км",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Помилка підключення до бази.")
        except Exception as e:
            await update.message.reply_text(f"❌ Помилка: {e}")
    else:
        await update.message.reply_text("❌ Скасовано.")
    context.user_data.clear()
    return await start(update, context)

# ===== ЗАПУСК =====
def main():
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu)
        ],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu)],
            # Евакуйовані
            EV_DATE: [MessageHandler(filters.TEXT, ev_date)],
            EV_LAST_NAME: [MessageHandler(filters.TEXT, ev_last_name)],
            EV_FIRST_NAME: [MessageHandler(filters.TEXT, ev_first_name)],
            EV_PATRONYMIC: [MessageHandler(filters.TEXT, ev_patronymic)],
            EV_GENDER: [MessageHandler(filters.TEXT, ev_gender)],
            EV_DOB: [MessageHandler(filters.TEXT, ev_dob)],
            EV_PASSPORT: [MessageHandler(filters.TEXT, ev_passport)],
            EV_PHONE: [MessageHandler(filters.TEXT, ev_phone)],
            EV_SETTLEMENT: [MessageHandler(filters.TEXT, ev_settlement)],
            EV_DISABILITY: [MessageHandler(filters.TEXT, ev_disability)],
            EV_CONFIRM: [MessageHandler(filters.TEXT, ev_confirm)],
            # Путьовий лист
            TR_CAR: [MessageHandler(filters.TEXT, tr_car)],
            TR_DRIVER: [MessageHandler(filters.TEXT, tr_driver)],
            TR_DATE: [MessageHandler(filters.TEXT, tr_date)],
            TR_TIME_OUT: [MessageHandler(filters.TEXT, tr_time_out)],
            TR_TIME_IN: [MessageHandler(filters.TEXT, tr_time_in)],
            TR_ROUTE: [MessageHandler(filters.TEXT, tr_route)],
            TR_ODO_START: [MessageHandler(filters.TEXT, tr_odo_start)],
            TR_ODO_END: [MessageHandler(filters.TEXT, tr_odo_end)],
            TR_FUEL: [MessageHandler(filters.TEXT, tr_fuel)],
            TR_NOTES: [MessageHandler(filters.TEXT, tr_notes)],
            TR_CONFIRM: [MessageHandler(filters.TEXT, tr_confirm)],
        },
        fallbacks=[CommandHandler('cancel', start)],
    )

    app.add_handler(conv)
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
