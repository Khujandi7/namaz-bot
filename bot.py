import logging
import requests
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

import os
TELEGRAM_TOKEN = os.environ.get 8310040854:AAErjFHScAPPQfS78OELoGkAuVm3rkTpWQM 
```

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Получаем время намаза с API ───
def get_prayer_times(lat, lon):
    url = f"http://api.aladhan.com/v1/timings?latitude={lat}&longitude={lon}&method=3"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data["code"] == 200:
            return data["data"]
        return None
    except:
        return None

# ─── Исламская дата ───
def get_hijri_date(lat, lon):
    data = get_prayer_times(lat, lon)
    if data:
        hijri = data["date"]["hijri"]
        return f"{hijri['day']} {hijri['month']['en']} {hijri['year']} AH"
    return ""

# ─── Красивое форматирование ───
def format_prayer_message(data, city_name=""):
    timings = data["timings"]
    hijri = data["date"]["hijri"]
    gregorian = data["date"]["gregorian"]
    
    hijri_str = f"{hijri['day']} {hijri['month']['en']} {hijri['year']} AH"
    date_str = gregorian["date"]
    
    # Определяем Рамадан
    ramadan_note = ""
    if hijri['month']['number'] == 9:
        ramadan_note = "🌙 Рамадан Мубарак!\n\n"
    
    message = f"""🕌 *Время намаза*
{'🏙 ' + city_name if city_name else '📍 Ваше местоположение'}
📅 {date_str}
☪️ {hijri_str}

{ramadan_note}🌅 *Фаджр (Сухур):*  `{timings['Fajr']}`
🌄 *Восход:*         `{timings['Sunrise']}`
☀️ *Зухр:*          `{timings['Dhuhr']}`
🌤 *Аср:*           `{timings['Asr']}`
🌇 *Магриб (Ифтар):* `{timings['Maghrib']}`
🌙 *Иша:*           `{timings['Isha']}`

⏰ *Полночь:*       `{timings['Midnight']}`"""
    
    return message

# ─── Вычисляем следующий намаз ───
def get_next_prayer(timings):
    prayer_order = [
        ("Фаджр", timings["Fajr"]),
        ("Восход", timings["Sunrise"]),
        ("Зухр", timings["Dhuhr"]),
        ("Аср", timings["Asr"]),
        ("Магриб", timings["Maghrib"]),
        ("Иша", timings["Isha"]),
    ]
    
    now = datetime.now()
    for name, time_str in prayer_order:
        h, m = map(int, time_str.split(":"))
        prayer_time = now.replace(hour=h, minute=m, second=0)
        if prayer_time > now:
            diff = prayer_time - now
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            if hours > 0:
                return f"⏳ *{name}* — через {hours} ч. {minutes} мин."
            else:
                return f"⏳ *{name}* — через {minutes} мин."
    return "🌙 Все намазы на сегодня выполнены. Барака Аллаху фикум!"

# ─── Главное меню ───
def get_main_menu():
    keyboard = [
        [KeyboardButton("📍 Отправить местоположение", request_location=True)],
        [KeyboardButton("ℹ️ Информация"), KeyboardButton("🧭 Кибла")],
        [KeyboardButton("📅 Сегодня"), KeyboardButton("📆 Завтра")],
        [KeyboardButton("❓ Задать вопрос"), KeyboardButton("⚙️ Настройки")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ════════════════════════════════════
# 📨 ОБРАБОТЧИКИ КОМАНД
# ════════════════════════════════════

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    
    welcome_text = f"""Ас-саляму алейкум, {user_name}! 🕌

Добро пожаловать в бот *Время Намаза*.

Я помогу Вам:
- 🕐 Узнать точное время намаза
- 🌙 Следить за Рамаданом
- 🧭 Найти направление Киблы
- ⏰ Получать напоминания

Пожалуйста, нажмите кнопку *"📍 Отправить местоположение"* для получения времени намаза в Вашем городе."""
    
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )

# Геолокация
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location = update.message.location
    lat = location.latitude
    lon = location.longitude
    
    # Сохраняем координаты пользователя
    context.user_data["lat"] = lat
    context.user_data["lon"] = lon
    
    await update.message.reply_text("🔄 Получаю время намаза для Вашего местоположения...")
    
    data = get_prayer_times(lat, lon)
    
    if data:
        message = format_prayer_message(data)
        next_prayer = get_next_prayer(data["timings"])
        
        full_message = message + f"\n\n{next_prayer}"
        
        # Кнопки под сообщением
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔔 Включить напоминания", callback_data="enable_reminders")],
            [InlineKeyboardButton("🧭 Кибла", callback_data="qibla"),
             InlineKeyboardButton("📆 Завтра", callback_data="tomorrow")]
        ])
        
        await update.message.reply_text(
            full_message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            "❌ Не удалось получить данные. Пожалуйста, попробуйте ещё раз.",
            reply_markup=get_main_menu()
        )

# Кибла
async def handle_qibla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lat = context.user_data.get("lat")
    lon = context.user_data.get("lon")
    
    if not lat:
        await update.message.reply_text(
            "📍 Пожалуйста, сначала отправьте Ваше местоположение.",
            reply_markup=get_main_menu()
        )
        return
    
    try:
        url = f"https://api.aladhan.com/v1/qibla/{lat}/{lon}"
        response = requests.get(url)
        data = response.json()
        direction = round(data["data"]["direction"], 1)
        
        # Стрелка по направлению
        arrows = ["⬆️","↗️","➡️","↘️","⬇️","↙️","⬅️","↖️"]
        arrow = arrows[int((direction + 22.5) / 45) % 8]
        
        await update.message.reply_text(
            f"""🧭 *Направление Киблы*

{arrow} *{direction}°* от севера

Поверните устройство так, чтобы верхняя часть указывала в сторону {direction}° — это и есть направление на Мекку.""",
            parse_mode="Markdown"
        )
    except:
        await update.message.reply_text("❌ Ошибка при определении Киблы.")

# Информация
async def handle_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """ℹ️ *О боте*

Этот бот предоставляет точное время намаза по Вашему местоположению.

*Метод расчёта:* Muslim World League (метод 3)

*Данные:* API AlAdhan.com

*Функции:*
- Время 5 намазов + восход
- Исламская дата
- Время сухура и ифтара в Рамадан
- Направление Киблы
- Следующий намаз

Да примет Аллах Ваши молитвы! 🤲""",
        parse_mode="Markdown"
    )

# Вопросы (базовые ответы без ИИ)
async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["waiting_question"] = True
    await update.message.reply_text(
        "❓ Задайте Ваш вопрос, и я постараюсь помочь Вам.\n\n_Напишите вопрос в следующем сообщении:_",
        parse_mode="Markdown"
    )

# Обработчик текста
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "ℹ️ Информация":
        await handle_info(update, context)
    elif text == "🧭 Кибла":
        await handle_qibla(update, context)
    elif text == "❓ Задать вопрос":
        await handle_question(update, context)
    elif text == "📅 Сегодня":
        lat = context.user_data.get("lat")
        lon = context.user_data.get("lon")
        if lat:
            await handle_location_by_coords(update, context, lat, lon)
        else:
            await update.message.reply_text("📍 Сначала отправьте местоположение.")
    elif context.user_data.get("waiting_question"):
        context.user_data["waiting_question"] = False
        # Базовые ответы на частые вопросы
        response = get_basic_answer(text)
        await update.message.reply_text(response, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            "Пожалуйста, воспользуйтесь меню или отправьте своё местоположение. 🕌",
            reply_markup=get_main_menu()
        )

# Вспомогательная функция
async def handle_location_by_coords(update, context, lat, lon):
    data = get_prayer_times(lat, lon)
    if data:
        message = format_prayer_message(data)
        next_prayer = get_next_prayer(data["timings"])
        await update.message.reply_text(
            message + f"\n\n{next_prayer}",
            parse_mode="Markdown"
        )

# Базовые ответы на вопросы
def get_basic_answer(question):
    q = question.lower()
    if "рамадан" in q or "рамазан" in q:
        return "🌙 *Рамадан* — священный месяц поста в Исламе. Пост начинается с рассвета (Фаджр/Сухур) и заканчивается на закате (Магриб/Ифтар)."
    elif "кибла" in q:
        return "🧭 *Кибла* — направление на Каабу в Мекке. Используйте кнопку 'Кибла' в меню для определения направления."
    elif "фаджр" in q:
        return "🌅 *Фаджр* — утренний намаз, который совершается на рассвете. В Рамадан это также время Сухура (предрассветного приёма пищи)."
    elif "ифтар" in q or "сухур" in q:
        return "🍽 *Сухур* — приём пищи до рассвета (до Фаджра).\n*Ифтар* — разговение на закате (время Магриба)."
    else:
        return f"Джазакумуллаху хайран за Ваш вопрос! 🤲\n\nДля получения точного ответа рекомендую обратиться к местному имаму или авторитетному исламскому источнику."

# Callback кнопки
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "enable_reminders":
        await query.message.reply_text(
            "🔔 *Напоминания*\n\nФункция напоминаний будет добавлена в следующем обновлении!\n\nСледите за обновлениями. 🕌",
            parse_mode="Markdown"
        )
    elif query.data == "qibla":
        await handle_qibla(query, context)
    elif query.data == "tomorrow":
        await query.message.reply_text("📆 Функция 'Завтра' скоро будет добавлена!")

# ════════════════════════════════════
# 🚀 ЗАПУСК БОТА
# ════════════════════════════════════
def main():
    print("🕌 Бот Время Намаза запускается...")
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("✅ Бот запущен! Нажми Ctrl+C для остановки.")
    app.run_polling()

if __name__ == "__main__":

    main()

