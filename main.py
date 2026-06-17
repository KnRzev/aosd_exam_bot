import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

from database import get_ticket, get_random_tickets

# ⚠️ ТВОЙ ТОКЕН ОТ @BotFather
BOT_TOKEN = "8955256805:AAExlc9_l0nQS42EkjI5B_c95qNJfZt8eY8"

# Настройка логирования (чтобы видеть в консоли, что бот работает)
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера (БЕЗ ПРОКСИ, чистый код)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Клавиатуры ---
def get_main_menu():
    """Создает главное меню с инлайн-кнопками."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Режим чтения (по номеру)", callback_data="mode_read")],
        [InlineKeyboardButton(text="🎲 Рандом-экзамен (2 билета)", callback_data="mode_random")],
        [InlineKeyboardButton(text="🧠 Активное вспоминание", callback_data="mode_recall")], # Пока заглушка
        [InlineKeyboardButton(text="💻 Код-ревью", callback_data="mode_code")] # Пока заглушка
    ])
    return keyboard

# --- Обработчики команд и сообщений ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    welcome_text = (
        "👋 Привет! Я твой интерактивный помощник для подготовки к экзамену по АОСД.\n\n"
        "Здесь ты найдешь эталонные ответы, код на Си и интерактивные режимы для проверки знаний.\n"
        "Выбери режим подготовки в меню ниже:"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu())

@dp.callback_query(F.data == "mode_read")
async def process_mode_read(callback: types.CallbackQuery):
    """Обработчик нажатия на кнопку 'Режим чтения'"""
    await callback.message.edit_text(
        "📖 <b>Режим чтения</b>\n\n"
        "Введите номер билета (например, <code>9</code>, <code>35</code> или <code>64</code>), и я выдам полный эталонный ответ с теорией и кодом на Си.",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(F.text.regexp(r"^\d+$")) # Ловим сообщения, состоящие только из цифр
async def process_ticket_number(message: Message):
    """Обработчик ввода номера билета"""
    ticket_id = int(message.text)
    ticket = await get_ticket(ticket_id)
    
    if not ticket:
        await message.answer(f"❌ Билет №{ticket_id} не найден. Проверь номер и попробуй снова (доступны: 9, 35, 64).")
        return

    # Формируем красивое сообщение с HTML-разметкой для подсветки кода
    response_text = (
        f"🎫 <b>Билет №{ticket['id']}</b>\n"
        f"📌 <b>Тема:</b> {ticket['title']}\n\n"
        f"📚 <b>Теория:</b>\n{ticket['theory']}\n\n"
    )
    
    if ticket['code']:
        # Telegram поддерживает подсветку синтаксиса через class='language-c' внутри pre/code
        response_text += f"💻 <b>Код на Си:</b>\n<pre><code class='language-c'>{ticket['code']}</code></pre>\n\n"
        
    response_text += "<i>Напиши /start, чтобы вернуться в главное меню.</i>"
    
    await message.answer(response_text, parse_mode="HTML")

@dp.callback_query(F.data == "mode_random")
async def process_mode_random(callback: types.CallbackQuery):
    """Обработчик режима 'Рандом-экзамен'"""
    await callback.answer("🎲 Генерирую случайные билеты...")
    tickets = await get_random_tickets(2)
    
    if not tickets:
        await callback.message.edit_text("❌ В базе данных пока нет билетов.")
        return

    response_text = "🎲 <b>Твой рандом-экзамен (2 билета):</b>\n\n"
    for t in tickets:
        # Показываем тему и начало теории, чтобы не спамить огромным текстом
        short_theory = t['theory'][:150] + "..." if len(t['theory']) > 150 else t['theory']
        response_text += f"🎫 <b>Билет №{t['id']}:</b> {t['title']}\n"
        response_text += f"📚 {short_theory}\n\n"
    
    response_text += "💡 <i>Хочешь увидеть полный ответ с кодом на конкретный билет? Просто напиши его номер (например, 9) прямо в чат!</i>"
    
    await callback.message.edit_text(response_text, parse_mode="HTML", reply_markup=get_main_menu())

# --- Заглушки для будущих режимов ---
@dp.callback_query(F.data.in_(["mode_recall", "mode_code"]))
async def process_coming_soon(callback: types.CallbackQuery):
    """Временный обработчик для еще не реализованных кнопок"""
    await callback.answer("🚧 Этот режим в активной разработке! Скоро будет доступен.", show_alert=True)

# --- Запуск ---
async def main():
    print("🚀 Бот успешно запущен! Нажми Ctrl+C в терминале для остановки.")
    # Игнорируем обновления, которые накопились, пока бот был выключен
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())