import asyncio
import logging
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import get_ticket, get_random_tickets

# ⚠️ ТВОЙ ТОКЕН ОТ @BotFather
BOT_TOKEN = "8955256805:AAExlc9_l0nQS42EkjI5B_c95qNJfZt8eY8"

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Состояния FSM ---
class RecallStates(StatesGroup):
    waiting_for_answer = State()

# --- Клавиатуры ---
def get_main_menu():
    """Создает главное меню с инлайн-кнопками."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Случайный билет (полный ответ)", callback_data="random_ticket_full")],
        [InlineKeyboardButton(text="📖 Режим чтения (по номеру)", callback_data="mode_read")],
        [InlineKeyboardButton(text="🎯 Экзамен с подсказками", callback_data="mode_random_hints")],
        [InlineKeyboardButton(text="🎯 Экзамен без подсказок", callback_data="mode_random_no_hints")],
        [InlineKeyboardButton(text="🧠 Активное вспоминание", callback_data="mode_recall")]
    ])
    return keyboard

# --- Вспомогательная функция для генерации пропусков ---
def generate_cloze(theory: str, keywords: str) -> str:
    """Заменяет ключевые слова в теории на ***"""
    if not keywords:
        return theory
    
    words = [w.strip() for w in keywords.split(',')]
    cloze_text = theory
    
    for word in words:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        cloze_text = pattern.sub('***', cloze_text)
        
    return cloze_text

# --- Обработчики команд и сообщений ---

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()
    welcome_text = (
        "👋 ЗДАРОВА! Я твой интерактивный помощник для подготовки к экзамену Зайки.\n\n"
        "Выбери режим подготовки:"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu())

MAX_TICKETS = 64 

def build_ticket_response(ticket):
    """Формирует красивый текст билета"""
    response_text = (
        f"🎫 <b>Билет №{ticket['id']}</b>\n"
        f"📌 <b>Тема:</b> {ticket['title']}\n\n"
        f"📚 <b>Теория:</b>\n{ticket['theory']}\n\n"
    )
    if ticket['code']:
        response_text += f"💻 <b>Код на Си:</b>\n<pre><code class='language-c'>{ticket['code']}</code></pre>\n\n"
    return response_text

def get_ticket_keyboard(ticket_id):
    """Создает клавиатуру с кнопками навигации"""
    nav_buttons = []
    if ticket_id > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Предыдущий", callback_data=f"prev_ticket:{ticket_id}"))
    if ticket_id < MAX_TICKETS:
        nav_buttons.append(InlineKeyboardButton(text="Следующий ▶️", callback_data=f"next_ticket:{ticket_id}"))
    
    rows = [nav_buttons] if nav_buttons else []
    rows.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_start")])
    
    return InlineKeyboardMarkup(inline_keyboard=rows)

@dp.callback_query(F.data == "mode_read")
async def process_mode_read(callback: types.CallbackQuery):
    """Обработчик нажатия на кнопку 'Режим чтения'"""
    await callback.message.edit_text(
        "📖 <b>Режим чтения</b>\n\n"
        "Введите номер билета (например, <code>6</code>, <code>7</code> или <code>64</code>), и я выдам полный ответ с теорией и кодом (Если он нужен).",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(F.text.regexp(r"^\d+$")) 
async def process_ticket_number(message: Message):
    """Обработчик ввода номера билета"""
    ticket_id = int(message.text)
    ticket = await get_ticket(ticket_id)
    
    if not ticket:
        await message.answer(f"❌ Билет №{ticket_id} не найден. Иди нахуй")
        return

    response_text = build_ticket_response(ticket)
    response_text += "<i>Напиши /start, чтобы получить 2 у Бортаковского.</i>"
    
    keyboard = get_ticket_keyboard(ticket_id)
    await message.answer(response_text, parse_mode="HTML", reply_markup=keyboard)

# --- Режимы Рандом-экзамена ---

@dp.callback_query(F.data == "mode_random_hints")
async def process_mode_random_hints(callback: types.CallbackQuery):
    """Обработчик режима 'Экзамен с подсказками'"""
    await callback.answer("🎯 Генерирую экзамен с подсказками...")
    tickets = await get_random_tickets(2)
    if not tickets:
        await callback.message.edit_text("❌ Пошёл нахуй")
        return

    response_text = "🎯 <b>Экзамен с подсказками (2 билета):</b>\n\n"
    for t in tickets:
        # Берем до 3 ключевых слов для подсказки
        hints = t['keywords'].split(',')[:3] if t['keywords'] else []
        hints_str = ", ".join([h.strip() for h in hints])
        
        response_text += f"🎫 <b>Билет №{t['id']}:</b> {t['title']}\n"
        response_text += f"💡 <i>Подсказка:</i> {hints_str}\n\n"
    
    response_text += "💡 <i>Вспомни теорию и напиши номер билета, чтобы увидеть полный ответ!</i>"
    
    await callback.message.edit_text(response_text, parse_mode="HTML", reply_markup=get_main_menu())

@dp.callback_query(F.data == "mode_random_no_hints")
async def process_mode_random_no_hints(callback: types.CallbackQuery):
    """Обработчик режима 'Экзамен без подсказок'"""
    await callback.answer("🎯 Генерирую экзамен без подсказок...")
    tickets = await get_random_tickets(2)
    if not tickets:
        await callback.message.edit_text("❌ Пошёл нахуй")
        return

    response_text = "🎯 <b>Экзамен без подсказок (2 билета):</b>\n\n"
    for t in tickets:
        response_text += f"🎫 <b>Билет №{t['id']}:</b> {t['title']}\n\n"
    
    response_text += "💡 <i>Попробуй вспомнить ответ целиком! Напиши номер билета, чтобы проверить себя.</i>"
    
    await callback.message.edit_text(response_text, parse_mode="HTML", reply_markup=get_main_menu())

# --- Режим "Активное вспоминание" ---

@dp.callback_query(F.data == "mode_recall")
async def process_mode_recall(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик нажатия на кнопку 'Активное вспоминание'"""
    await callback.answer("🧠 Активное вспоминание...")
    tickets = await get_random_tickets(1)
    if not tickets:
        await callback.message.edit_text("❌ Иди в зад.")
        return

    ticket = tickets[0]
    theory = ticket['theory']
    keywords = ticket['keywords']

    cloze_text = generate_cloze(theory, keywords)

    await state.update_data(ticket_id=ticket['id'], keywords=keywords)

    await callback.message.edit_text(
        f"🧠 <b>Режим 'Активное вспоминание'</b>\n\n"
        f"🎫 <b>Билет №{ticket['id']}</b>: {ticket['title']}\n\n"
        f"{cloze_text}\n\n"
        f"💡 <i>Вспомни пропущенные слова и напиши их через запятую (например: Тимур, Зайка).</i>\n"
        f"<i>Напиши /start, чтобы получить 2 у Бортаковского.</i>",
        parse_mode="HTML"
    )

    await state.set_state(RecallStates.waiting_for_answer)

@dp.message(RecallStates.waiting_for_answer)
async def process_recall_answer(message: Message, state: FSMContext):
    """Обработчик ответа пользователя с умной проверкой"""
    data = await state.get_data()
    keywords_str = data.get('keywords', '')
    ticket_id = data.get('ticket_id')
    
    correct_words = [w.strip().lower() for w in keywords_str.split(',') if w.strip()]
    user_text = message.text.lower()

    found_words = []
    missing_words = []

    for word in correct_words:
        if word in user_text:
            found_words.append(word)
        else:
            missing_words.append(word)
            
    if not missing_words: 
        result_text = f"🎉 <b>Отлично!</b> Ты вспомнил все ключевые термины для билета №{ticket_id}!\n\n"
    elif found_words:
        result_text = f"👍 <b>Хорошая попытка!</b> Ты вспомнил: <i>{', '.join(found_words)}</i>.\n"
        result_text += f"Но забыл: <b>{', '.join(missing_words)}</b>.\n\n"
    else:
        result_text = f"❌ <b>Не совсем.</b> Вот какие слова нужно было вспомнить:\n"
        result_text += f"<b>{', '.join(correct_words)}</b>\n\n"
        
    result_text += "Анекдот №948569: Одну девочку в школе все звали Крокодил. Но не потому что она была некрасивая, а потому что однажды она затащила в воду оленя и сожрала его."

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Еще один билет", callback_data="mode_recall")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_start")]
    ])

    await message.answer(result_text, parse_mode="HTML", reply_markup=keyboard)
    await state.clear()

@dp.callback_query(F.data == "to_start")
async def process_to_start(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню по кнопке"""
    await state.clear()
    await callback.message.edit_text(
        "Главное меню",
        reply_markup=get_main_menu()
    )
    await callback.answer()

# --- Случайный билет ---

@dp.callback_query(F.data == "random_ticket_full")
async def process_random_ticket_full(callback: types.CallbackQuery):
    """Показывает полный случайный билет"""
    await callback.answer("🎲 Случайный билет...")
    tickets = await get_random_tickets(1)
    if not tickets:
        await callback.message.edit_text("❌ Иди нахуй.")
        return
    
    ticket = tickets[0]
    response_text = build_ticket_response(ticket)
    response_text += "<i>Нажми кнопку ниже, чтобы сгенерировать еще один.</i>"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Еще один случайный билет", callback_data="random_ticket_full")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_start")]
    ])

    await callback.message.edit_text(response_text, parse_mode="HTML", reply_markup=keyboard)

# --- Навигация по билетам ---

@dp.callback_query(F.data.startswith("prev_ticket:"))
async def process_prev_ticket(callback: types.CallbackQuery):
    """Обработчик кнопки 'Предыдущий билет'"""
    current_id = int(callback.data.split(":")[1])
    new_id = current_id - 1
    ticket = await get_ticket(new_id)
    if ticket:
        response_text = build_ticket_response(ticket)
        keyboard = get_ticket_keyboard(new_id)
        await callback.message.edit_text(response_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("next_ticket:"))
async def process_next_ticket(callback: types.CallbackQuery):
    """Обработчик кнопки 'Следующий билет'"""
    current_id = int(callback.data.split(":")[1])
    new_id = current_id + 1
    ticket = await get_ticket(new_id)
    if ticket:
        response_text = build_ticket_response(ticket)
        keyboard = get_ticket_keyboard(new_id)
        await callback.message.edit_text(response_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

# --- Запуск ---
async def main():
    print("🚀 Бот успешно запущен! Нажми Ctrl+C в терминале для остановки.")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())