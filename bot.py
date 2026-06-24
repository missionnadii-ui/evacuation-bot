import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from datetime import datetime

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("BOT_TOKEN not set!")

CARS = ["🔵 VW T5 Синій (МІС ВУ82)", "⬜ VW T5 Білий"]
DRIVERS = ["Савченко Влад", "Ткаченко Олег"]

# Стани
(
    MAIN_MENU,
    EV_DATE, EV_LAST, EV_FIRST, EV_PAT,
    EV_GENDER, EV_DOB, EV_PASS, EV_PHONE,
    EV_PLACE, EV_DIS, EV_OK,
    TR_CAR, TR_DRV, TR_DATE, TR_OUT, TR_IN,
    TR_ROUTE, TR_ODO1, TR_ODO2, TR_FUEL, TR_NOTE, TR_OK
) = range(23)

def menu_kb():
    return ReplyKeyboardMarkup([
        [KeyboardButton("➕ Додати евакуйованого")],
        [KeyboardButton("🚐 Путьовий лист")],
        [KeyboardButton("📊 Статистика")],
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕊️ *Місія Подих Надії*\n\nОберіть дію:",
        reply_markup=menu_kb(),
        parse_mode='Markdown'
    )
    return MAIN_MENU

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "евакуйованого" in text:
        await update.message.reply_text("📅 Дата евакуації (ДД.ММ.РРРР):")
        return EV_DATE
    elif "Путьовий" in text:
        kb = ReplyKeyboardMarkup([[KeyboardButton(c)] for c in CARS], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("🚐 Оберіть авто:", reply_markup=kb)
        return TR_CAR
    elif "Статистика" in text:
        if 'evacuees' not in context.bot_data:
            context.bot_data['evacuees'] = []
        if 'trips' not in context.bot_data:
            context.bot_data['trips'] = []
        ev = len(context.bot_data['evacuees'])
        tr = len(context.bot_data['trips'])
        await update.message.reply_text(
            f"📊 *Статистика:*\n\n👥 Евакуйованих: *{ev}*\n🚐 Рейсів: *{tr}*",
            parse_mode='Markdown', reply_markup=menu_kb()
        )
        return MAIN_MENU
    return MAIN_MENU

# ===== ЕВАКУЙОВАНІ =====
async def ev_date(u, c):
    c.user_data['date'] = u.message.text
    await u.message.reply_text("👤 Прізвище:")
    return EV_LAST

async def ev_last(u, c):
    c.user_data['last'] = u.message.text
    await u.message.reply_text("👤 Ім'я:")
    return EV_FIRST

async def ev_first(u, c):
    c.user_data['first'] = u.message.text
    await u.message.reply_text("👤 По батькові:")
    return EV_PAT

async def ev_pat(u, c):
    c.user_data['pat'] = u.message.text
    kb = ReplyKeyboardMarkup([[KeyboardButton("👩 Жінка"), KeyboardButton("👨 Чоловік")]], resize_keyboard=True, one_time_keyboard=True)
    await u.message.reply_text("⚥ Стать:", reply_markup=kb)
    return EV_GENDER

async def ev_gender(u, c):
    c.user_data['gender'] = 'Ж' if 'Жінка' in u.message.text else 'Ч'
    await u.message.reply_text("🎂 Дата народження (ДД.ММ.РРРР):")
    return EV_DOB

async def ev_dob(u, c):
    c.user_data['dob'] = u.message.text
    await u.message.reply_text("🪪 Паспорт (або: немає / згорів):")
    return EV_PASS

async def ev_pass(u, c):
    c.user_data['passport'] = u.message.text
    await u.message.reply_text("📱 Телефон (або: немає):")
    return EV_PHONE

async def ev_phone(u, c):
    c.user_data['phone'] = u.message.text
    await u.message.reply_text("🏘️ Населений пункт:")
    return EV_PLACE

async def ev_place(u, c):
    c.user_data['place'] = u.message.text
    kb = ReplyKeyboardMarkup([[KeyboardButton("✅ Так"), KeyboardButton("❌ Ні")]], resize_keyboard=True, one_time_keyboard=True)
    await u.message.reply_text("♿ Інвалідність?", reply_markup=kb)
    return EV_DIS

async def ev_dis(u, c):
    c.user_data['dis'] = 'Так' if '✅' in u.message.text else 'Ні'
    d = c.user_data
    text = (
        f"📋 *Перевірте:*\n\n"
        f"📅 {d.get('date')}\n"
        f"👤 {d.get('last')} {d.get('first')} {d.get('pat')}\n"
        f"⚥ {d.get('gender')} | 🎂 {d.get('dob')}\n"
        f"🪪 {d.get('passport')} | 📱 {d.get('phone')}\n"
        f"🏘️ {d.get('place')} | ♿ {d.get('dis')}\n\n"
        f"Зберегти?"
    )
    kb = ReplyKeyboardMarkup([[KeyboardButton("✅ Зберегти"), KeyboardButton("❌ Скасувати")]], resize_keyboard=True, one_time_keyboard=True)
    await u.message.reply_text(text, reply_markup=kb, parse_mode='Markdown')
    return EV_OK

async def ev_ok(u, c):
    if '✅' in u.message.text:
        if 'evacuees' not in c.bot_data:
            c.bot_data['evacuees'] = []
        c.bot_data['evacuees'].append(dict(c.user_data))
        await u.message.reply_text("✅ *Збережено!*", parse_mode='Markdown', reply_markup=menu_kb())
    else:
        await u.message.reply_text("❌ Скасовано.", reply_markup=menu_kb())
    c.user_data.clear()
    return MAIN_MENU

# ===== ПУТЬОВИЙ ЛИСТ =====
async def tr_car(u, c):
    c.user_data['car'] = u.message.text
    kb = ReplyKeyboardMarkup([[KeyboardButton(d)] for d in DRIVERS], resize_keyboard=True, one_time_keyboard=True)
    await u.message.reply_text("👤 Водій:", reply_markup=kb)
    return TR_DRV

async def tr_drv(u, c):
    c.user_data['driver'] = u.message.text
    await u.message.reply_text("📅 Дата рейсу (ДД.ММ.РРРР):")
    return TR_DATE

async def tr_date(u, c):
    c.user_data['tr_date'] = u.message.text
    await u.message.reply_text("⏰ Час виїзду (наприклад: 08:30):")
    return TR_OUT

async def tr_out(u, c):
    c.user_data['out'] = u.message.text
    await u.message.reply_text("⏰ Час повернення:")
    return TR_IN

async def tr_in(u, c):
    c.user_data['tin'] = u.message.text
    await u.message.reply_text("📍 Маршрут:")
    return TR_ROUTE

async def tr_route(u, c):
    c.user_data['route'] = u.message.text
    await u.message.reply_text("🔢 Спідометр на виїзді (км):")
    return TR_ODO1

async def tr_odo1(u, c):
    c.user_data['odo1'] = u.message.text
    await u.message.reply_text("🔢 Спідометр на поверненні (км):")
    return TR_ODO2

async def tr_odo2(u, c):
    c.user_data['odo2'] = u.message.text
    try:
        c.user_data['km'] = int(u.message.text) - int(c.user_data['odo1'])
    except:
        c.user_data['km'] = 0
    await u.message.reply_text("⛽ Заправка (літрів, або: 0):")
    return TR_FUEL

async def tr_fuel(u, c):
    c.user_data['fuel'] = u.message.text
    await u.message.reply_text("📝 Примітки (або: немає):")
    return TR_NOTE

async def tr_note(u, c):
    c.user_data['note'] = u.message.text
    d = c.user_data
    text = (
        f"🚐 *Перевірте рейс:*\n\n"
        f"🚗 {d.get('car')}\n"
        f"👤 {d.get('driver')}\n"
        f"📅 {d.get('tr_date')} | ⏰ {d.get('out')}–{d.get('tin')}\n"
        f"📍 {d.get('route')}\n"
        f"🛣️ Пробіг: *{d.get('km')} км*\n"
        f"⛽ Заправка: {d.get('fuel')} л\n"
        f"📝 {d.get('note')}\n\nЗберегти?"
    )
    kb = ReplyKeyboardMarkup([[KeyboardButton("✅ Зберегти"), KeyboardButton("❌ Скасувати")]], resize_keyboard=True, one_time_keyboard=True)
    await u.message.reply_text(text, reply_markup=kb, parse_mode='Markdown')
    return TR_OK

async def tr_ok(u, c):
    if '✅' in u.message.text:
        if 'trips' not in c.bot_data:
            c.bot_data['trips'] = []
        c.bot_data['trips'].append(dict(c.user_data))
        d = c.user_data
        await u.message.reply_text(
            f"✅ *Рейс збережено!*\n🛣️ Пробіг: {d.get('km')} км",
            parse_mode='Markdown', reply_markup=menu_kb()
        )
    else:
        await u.message.reply_text("❌ Скасовано.", reply_markup=menu_kb())
    c.user_data.clear()
    return MAIN_MENU

def main():
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu)
        ],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu)],
            EV_DATE: [MessageHandler(filters.TEXT, ev_date)],
            EV_LAST: [MessageHandler(filters.TEXT, ev_last)],
            EV_FIRST: [MessageHandler(filters.TEXT, ev_first)],
            EV_PAT: [MessageHandler(filters.TEXT, ev_pat)],
            EV_GENDER: [MessageHandler(filters.TEXT, ev_gender)],
            EV_DOB: [MessageHandler(filters.TEXT, ev_dob)],
            EV_PASS: [MessageHandler(filters.TEXT, ev_pass)],
            EV_PHONE: [MessageHandler(filters.TEXT, ev_phone)],
            EV_PLACE: [MessageHandler(filters.TEXT, ev_place)],
            EV_DIS: [MessageHandler(filters.TEXT, ev_dis)],
            EV_OK: [MessageHandler(filters.TEXT, ev_ok)],
            TR_CAR: [MessageHandler(filters.TEXT, tr_car)],
            TR_DRV: [MessageHandler(filters.TEXT, tr_drv)],
            TR_DATE: [MessageHandler(filters.TEXT, tr_date)],
            TR_OUT: [MessageHandler(filters.TEXT, tr_out)],
            TR_IN: [MessageHandler(filters.TEXT, tr_in)],
            TR_ROUTE: [MessageHandler(filters.TEXT, tr_route)],
            TR_ODO1: [MessageHandler(filters.TEXT, tr_odo1)],
            TR_ODO2: [MessageHandler(filters.TEXT, tr_odo2)],
            TR_FUEL: [MessageHandler(filters.TEXT, tr_fuel)],
            TR_NOTE: [MessageHandler(filters.TEXT, tr_note)],
            TR_OK: [MessageHandler(filters.TEXT, tr_ok)],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    app.add_handler(conv)
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
