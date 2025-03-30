import sqlite3
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

# Токен бота
TOKEN = ""

# Флаг для отслеживания состояния
awaiting_admin_id = {}
awaiting_remove_admin_id = {}

# Функция для старта
def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    keyboard = [['Понедельник', 'Вторник', 'Среда'], ['Четверг', 'Пятница']]
    
    conn = sqlite3.connect("schedule.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM admins WHERE id = ?", (user.id,))
    admin = cursor.fetchone()
    conn.close()

    if admin:
        keyboard.append(["Админская панель"])  # Исправлено
    
    update.message.reply_text(
        f"Привет, {user.first_name}! Выбери день недели, чтобы получить расписание.",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )

# Функция получения расписания
def get_schedule(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id in awaiting_admin_id:
        add_admin(update, context)
        return
    elif user_id in awaiting_remove_admin_id:
        remove_admin(update, context)
        return
    
    day = update.message.text
    if day == 'Админская панель':
        admin_panel(update, context)  # Добавлен вызов админской панели
        return

    conn = sqlite3.connect("schedule.db")
    cursor = conn.cursor()
    cursor.execute("SELECT lesson_number, time, subject, teacher FROM lessons WHERE day = ? ORDER BY lesson_number", (day,))
    lessons = cursor.fetchall()
    conn.close()

    response = f"📅 Расписание на {day}:\n" if lessons else "❌ Расписание на этот день не найдено."
    for num, time, subject, teacher in lessons:
        response += f"📖 {num}-й урок ({time})\n   {subject} - {teacher}\n\n"

    update.message.reply_text(response)

# Админская панель
def admin_panel(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
    
    conn = sqlite3.connect("schedule.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM admins WHERE id = ?", (user_id,))
    admin = cursor.fetchone()
    conn.close()
    
    if admin:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Добавить админа", callback_data="add_admin")],
            [InlineKeyboardButton("Удалить админа", callback_data="remove_admin")]
        ])
        
        if update.message:
            update.message.reply_text("📋 Админская панель:", reply_markup=keyboard)
        else:
            update.callback_query.edit_message_text("📋 Админская панель:", reply_markup=keyboard)  # Исправлено
    else:
        update.message.reply_text("❌ У вас нет доступа к админской панели.")

# Добавление админа
def request_admin_id(update: Update, context: CallbackContext) -> None:
    user_id = update.callback_query.from_user.id
    awaiting_admin_id[user_id] = True
    update.callback_query.message.reply_text("Введите ID пользователя, которого хотите добавить в админы.")

# Удаление админа
def request_remove_admin_id(update: Update, context: CallbackContext) -> None:
    user_id = update.callback_query.from_user.id
    awaiting_remove_admin_id[user_id] = True
    update.callback_query.message.reply_text("Введите ID пользователя, которого хотите удалить из админов.")

# Функция добавления админа
def add_admin(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    new_admin_id = update.message.text
    
    try:
        new_admin_id = int(new_admin_id)
        conn = sqlite3.connect("schedule.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO admins (id) VALUES (?)", (new_admin_id,))
        conn.commit()
        conn.close()
        update.message.reply_text(f"✅ Пользователь {new_admin_id} добавлен в админы!")
    except ValueError:
        update.message.reply_text("❌ Некорректный ID. Введите число.")
    finally:
        awaiting_admin_id.pop(user_id, None)

# Функция удаления админа
def remove_admin(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    admin_id_to_remove = update.message.text
    
    try:
        admin_id_to_remove = int(admin_id_to_remove)
        conn = sqlite3.connect("schedule.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM admins WHERE id = ?", (admin_id_to_remove,))
        conn.commit()
        conn.close()
        update.message.reply_text(f"✅ Пользователь {admin_id_to_remove} удалён из админов!")
    except ValueError:
        update.message.reply_text("❌ Некорректный ID. Введите число.")
    finally:
        awaiting_remove_admin_id.pop(user_id, None)

# Запуск бота
def main() -> None:
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, get_schedule))
    dp.add_handler(CallbackQueryHandler(request_admin_id, pattern="^add_admin$"))
    dp.add_handler(CallbackQueryHandler(request_remove_admin_id, pattern="^remove_admin$"))
    
    print("Бот запущен...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
