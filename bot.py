import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import sqlite3
from datetime import datetime

# Logging yoqish
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Token
TOKEN = '8309242539:AAGlGmfFE8hqzbq37lbj09sau6XJIwjNIhY'

# Ma'lumotlar bazasini yaratish
def init_db():
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS records
                 (user_id TEXT, type TEXT, amount REAL, desc TEXT, datetime TEXT, category TEXT)''')
    conn.commit()
    conn.close()

# Ma'lumotlarni yuklash
def load_data(user_id):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("SELECT type, amount, desc, datetime, category FROM records WHERE user_id = ?", (str(user_id),))
    records = c.fetchall()
    conn.close()
    data = {'expenses': [], 'income': []}
    for r in records:
        record = {'amount': r[2], 'desc': r[3], 'datetime': r[4], 'category': r[5]}
        if r[1] == 'expense':
            data['expenses'].append(record)
        else:
            data['income'].append(record)
    return data

# Ma'lumotlarni saqlash
def save_data(user_id, type_, amount, desc, datetime, category):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("INSERT INTO records (user_id, type, amount, desc, datetime, category) VALUES (?, ?, ?, ?, ?, ?)",
              (str(user_id), type_, amount, desc, datetime, category))
    conn.commit()
    conn.close()

# Asosiy menyu tugmalarini ko'rsatish
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    keyboard = [
        [InlineKeyboardButton("💸 Chiqim qo'shish", callback_data='add_expense')],
        [InlineKeyboardButton("💰 Kirim qo'shish", callback_data='add_income')],
        [InlineKeyboardButton("📊 Balans ko'rish", callback_data='balance')],
        [InlineKeyboardButton("📈 Statistika", callback_data='stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(text + "\n\nYana nima qilamiz? 😊", reply_markup=reply_markup)
    else:
        await update.message.reply_text(text + "\n\nYana nima qilamiz? 😊", reply_markup=reply_markup)

# /start buyrug'i
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    init_db()  # Bazani ishga tushirish
    await show_main_menu(update, context, 'Salom! Men kirim va chiqim hisobini yuritaman. Keling, boshlaymiz! 🚀')

# Chiqim kategoriyalari
def get_expense_categories():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍽️ Ovqat", callback_data='cat_ovqat')],
        [InlineKeyboardButton("🚗 Transport", callback_data='cat_transport')],
        [InlineKeyboardButton("🏠 Uy", callback_data='cat_uy')],
        [InlineKeyboardButton("❓ Boshqa", callback_data='cat_boshqa')]
    ])

# Kirim kategoriyalari
def get_income_categories():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💼 Ish haqi", callback_data='cat_ish_haqi')],
        [InlineKeyboardButton("🛒 Sotuv", callback_data='cat_sotuv')],
        [InlineKeyboardButton("📈 Investitsiya", callback_data='cat_invest')],
        [InlineKeyboardButton("❓ Boshqa", callback_data='cat_boshqa_inc')]
    ])

# Tugma bosilganda
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'add_expense':
        await query.edit_message_text('Chiqim kategoriyasini tanlang:', reply_markup=get_expense_categories())
        context.user_data['mode'] = 'expense'
    elif query.data == 'add_income':
        await query.edit_message_text('Kirim kategoriyasini tanlang:', reply_markup=get_income_categories())
        context.user_data['mode'] = 'income'
    elif query.data.startswith('cat_'):
        category = query.data.replace('cat_', '').replace('_inc', '')
        context.user_data['category'] = category
        await query.edit_message_text(f"{category.capitalize()} uchun miqdorni yuboring (masalan: 100 tavsif)")
    elif query.data == 'balance':
        user_data = load_data(query.from_user.id)
        total_exp = sum(item['amount'] for item in user_data['expenses'])
        total_inc = sum(item['amount'] for item in user_data['income'])
        balance = total_inc - total_exp
        balance_text = f"📊 Balans: {balance} so'm\n💰 Kirim: {total_inc} so'm\n💸 Chiqim: {total_exp} so'm\n\n"
        all_records = sorted(user_data['expenses'] + user_data['income'], key=lambda x: x['datetime'], reverse=True)[:5]
        if all_records:
            balance_text += "So'nggi yozuvlar:\n"
            for record in all_records:
                type_text = "Chiqim" if record in user_data['expenses'] else "Kirim"
                balance_text += f"{record['datetime']} - {type_text}: {record['amount']} so'm ({record['desc']}, {record['category'].capitalize()})\n"
        await show_main_menu(update, context, balance_text)
    elif query.data == 'stats':
        user_data = load_data(query.from_user.id)
        today = datetime.now().strftime('%Y-%m-%d')
        today_exp = sum(item['amount'] for item in user_data['expenses'] if item['datetime'].startswith(today))
        today_inc = sum(item['amount'] for item in user_data['income'] if item['datetime'].startswith(today))
        stats_text = f"📈 Bugungi statistika:\nChiqim: {today_exp} so'm\nKirim: {today_inc} so'm\n\nSo'nggi yozuvlar (vaqt bilan):\n"
        all_records = sorted(user_data['expenses'] + user_data['income'], key=lambda x: x['datetime'], reverse=True)[:10]
        if not all_records:
            stats_text += "Hozircha yozuvlar yo'q."
        else:
            for record in all_records:
                type_text = "Chiqim" if record in user_data['expenses'] else "Kirim"
                stats_text += f"{record['datetime']} - {type_text}: {record['amount']} so'm ({record['desc']}, {record['category'].capitalize()})\n"
        await show_main_menu(update, context, stats_text)

# Matn xabarlarini qayta ishlash
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'mode' in context.user_data and 'category' in context.user_data:
        text = update.message.text
        user_id = update.effective_user.id
        try:
            amount_desc = text.split(' ', 1)
            amount = float(amount_desc[0].replace('+', ''))
            desc = amount_desc[1] if len(amount_desc) > 1 else 'Noma\'lum'
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            category = context.user_data['category']
            save_data(user_id, context.user_data['mode'], amount, desc, now, category)
            success_text = f"✅ Qo'shildi! {context.user_data['mode'].capitalize()} uchun {amount} so'm ({desc}, {category.capitalize()}) - {now}"
            await update.message.reply_sticker(sticker='CAACAgIAAxkBAAIBvGa1aZ6fAAH2AAHAAQIBAAIAAgA')  # Misol ID, o'zgartiring
            await show_main_menu(update, context, success_text)
        except ValueError:
            await update.message.reply_text("❌ Xato! Miqdorni raqam sifatida yuboring (masalan: 100 tavsif).")
        finally:
            del context.user_data['mode']
            del context.user_data['category']

# Asosiy funksiya
def main() -> None:
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == '__main__':
    main()