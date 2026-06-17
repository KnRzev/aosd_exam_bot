import asyncio
import logging
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import get_ticket, get_random_tickets
from database import get_ticket, get_random_tickets

# ⚠️ ТВОЙ ТОКЕН ОТ @BotFather
BOT_TOKEN = "8955256805:AAExlc9_l0nQS42EkjI5B_c95qNJfZt8eY8"

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Состояния FSM для режима "Активное вспоминание" ---
class RecallStates(StatesGroup):
    waiting_for_answer = State()

class CodeReviewStates(StatesGroup):
    waiting_for_bug = State()

# --- Клавиатуры ---
def get_main_menu():
    """Создает главное меню с инлайн-кнопками."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Режим чтения (по номеру)", callback_data="mode_read")],
        [InlineKeyboardButton(text="🎲 Рандом-экзамен (2 билета)", callback_data="mode_random")],
        [InlineKeyboardButton(text="🧠 Активное вспоминание", callback_data="mode_recall")],
        [InlineKeyboardButton(text="💻 Код-ревью", callback_data="mode_code")] # Пока заглушка
    ])
    return keyboard

# --- Вспомогательная функция для генерации пропусков ---
def generate_cloze(theory: str, keywords: str) -> str:
    """Заменяет ключевые слова в теории на ***"""
    if not keywords:
        return theory
    
    # Разбиваем строку keywords на список слов
    words = [w.strip() for w in keywords.split(',')]
    cloze_text = theory
    
    for word in words:
        # Заменяем слово на ***, игнорируя регистр
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        cloze_text = pattern.sub('***', cloze_text)
    
    return cloze_text

# --- Обработчики команд и сообщений ---

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    # Сбрасываем состояние FSM, если пользователь нажал /start в середине режима
    await state.clear()
    
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
        await message.answer(f"❌ Билет №{ticket_id} не найден. Проверь номер и попробуй снова (доступны билеты с 1 по 64).")
        return

    # Формируем красивое сообщение с HTML-разметкой для подсветки кода
    response_text = (
        f"🎫 <b>Билет №{ticket['id']}</b>\n"
        f"📌 <b>Тема:</b> {ticket['title']}\n\n"
        f"📚 <b>Теория:</b>\n{ticket['theory']}\n\n"
    )
    
    if ticket['code']:
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
        short_theory = t['theory'][:150] + "..." if len(t['theory']) > 150 else t['theory']
        response_text += f"🎫 <b>Билет №{t['id']}:</b> {t['title']}\n"
        response_text += f"📚 {short_theory}\n\n"
    
    response_text += "💡 <i>Хочешь увидеть полный ответ с кодом на конкретный билет? Просто напиши его номер (например, 9) прямо в чат!</i>"
    
    await callback.message.edit_text(response_text, parse_mode="HTML", reply_markup=get_main_menu())

# --- Режим "Активное вспоминание" ---

@dp.callback_query(F.data == "mode_recall")
async def process_mode_recall(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик нажатия на кнопку 'Активное вспоминание'"""
    await callback.answer("🧠 Генерирую билет с пропусками...")
    
    # Получаем случайный билет
    tickets = await get_random_tickets(1)
    if not tickets:
        await callback.message.edit_text("❌ В базе данных пока нет билетов.")
        return
    
    ticket = tickets[0]
    theory = ticket['theory']
    keywords = ticket['keywords']
    
    # Генерируем текст с пропусками
    cloze_text = generate_cloze(theory, keywords)
    
    # Сохраняем данные билета в FSM, чтобы потом проверить ответ
    await state.update_data(ticket_id=ticket['id'], keywords=keywords)
    
    # Отправляем пользователю билет с пропусками
    await callback.message.edit_text(
        f"🧠 <b>Режим 'Активное вспоминание'</b>\n\n"
        f"🎫 <b>Билет №{ticket['id']}</b>: {ticket['title']}\n\n"
        f"{cloze_text}\n\n"
        f"💡 <i>Вспомни пропущенные слова и напиши их через запятую (например: слово1, слово2).</i>\n"
        f"Чтобы выйти, напиши /start.",
        parse_mode="HTML"
    )
    
    # Устанавливаем состояние "ждем ответа"
    await state.set_state(RecallStates.waiting_for_answer)

@dp.message(RecallStates.waiting_for_answer)
async def process_recall_answer(message: Message, state: FSMContext):
    """Обработчик ответа пользователя с умной проверкой"""
    data = await state.get_data()
    keywords_str = data.get('keywords', '')
    ticket_id = data.get('ticket_id')
    
    # 1. Разбираем эталонные ответы (убираем пробелы по краям, приводим к нижнему регистру)
    correct_words = [w.strip().lower() for w in keywords_str.split(',') if w.strip()]
    user_text = message.text.lower()
    
    # 2. Проверяем, какие слова есть в ответе пользователя, а каких не хватает
    found_words = []
    missing_words = []
    
    for word in correct_words:
        if word in user_text:
            found_words.append(word)
        else:
            missing_words.append(word)
            
    # 3. Формируем красивый ответ бота в зависимости от результата
    if not missing_words:
        result_text = f"🎉 <b>Отлично!</b> Ты вспомнил все ключевые термины для билета №{ticket_id}!\n\n"
    elif found_words:
        result_text = f"👍 <b>Хорошая попытка!</b> Ты вспомнил: <i>{', '.join(found_words)}</i>.\n"
        result_text += f"Но забыл: <b>{', '.join(missing_words)}</b>.\n\n"
    else:
        result_text = f"❌ <b>Не совсем.</b> Вот какие слова нужно было вспомнить:\n"
        result_text += f"<b>{', '.join(correct_words)}</b>\n\n"
        
    result_text += "Попробуем еще один билет или вернемся в меню?"
    
    # 4. Создаем кнопки для дальнейших действий
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Еще один билет", callback_data="mode_recall")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_start")]
    ])
    
    await message.answer(result_text, parse_mode="HTML", reply_markup=keyboard)
    
    # Сбрасываем состояние FSM
    await state.clear()

@dp.callback_query(F.data == "to_start")
async def process_to_start(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню по кнопке"""
    await state.clear()
    await callback.message.edit_text(
        "👋 Возвращаемся в главное меню...",
        reply_markup=get_main_menu()
    )
    await callback.answer()


# --- Режим "Код-ревью" ---

@dp.callback_query(F.data == "mode_code")
async def process_mode_code(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик нажатия на кнопку 'Код-ревью'"""
    await callback.answer("💻 Генерирую задачу на поиск ошибки...")
    
    ticket = await get_random_ticket_with_code()
    if not ticket:
        await callback.message.edit_text("❌ В базе нет билетов с кодом и описанием ошибок.")
        return
    
    # Сохраняем описание ошибки в FSM, чтобы показать его после ответа
    await state.update_data(ticket_id=ticket['id'], error_desc=ticket['code_error_desc'])
    
    text = (
        f"💻 <b>Режим 'Код-ревью'</b>\n\n"
        f"🎫 <b>Билет №{ticket['id']}</b>: {ticket['title']}\n\n"
        f"🐞 <b>Задание:</b> В этом коде на Си студенты чаще всего допускают одну критическую ошибку. "
        f"Попробуй найти её и напиши, в чём она заключается (своими словами).\n\n"
        f"<pre><code class='language-c'>{ticket['code']}</code></pre>\n\n"
        f"💡 <i>Напиши свой вариант ответа. Чтобы выйти, нажми /start.</i>"
    )
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(CodeReviewStates.waiting_for_bug)

@dp.message(CodeReviewStates.waiting_for_bug)
async def process_code_review_answer(message: Message, state: FSMContext):
    """Обработчик ответа пользователя в режиме 'Код-ревью'"""
    data = await state.get_data()
    error_desc = data.get('error_desc')
    ticket_id = data.get('ticket_id')
    
    # Показываем эталонное описание ошибки
    text = (
        f"✅ <b>Твой ответ принят!</b>\n\n"
        f"🔍 <b>В чём заключалась ошибка (Билет №{ticket_id}):</b>\n"
        f"{error_desc}\n\n"
        f"Сравни со своим вариантом! Всё верно?\n"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Еще одна ошибка", callback_data="mode_code")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_start")]
    ])
    
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await state.clear()

# --- Запуск ---
async def main():
    print("🚀 Бот успешно запущен! Нажми Ctrl+C в терминале для остановки.")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())