import aiosqlite
import os

DB_PATH = "database.db"

async def init_db():
    """Инициализирует базу данных и создает таблицы, если их нет."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                theory TEXT NOT NULL,
                code TEXT,
                keywords TEXT,
                code_error_desc TEXT
            )
        ''')
        await db.commit()

async def get_ticket(ticket_id: int):
    """Получает полный билет по его номеру."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,))
        return await cursor.fetchone()

async def get_random_tickets(count: int = 2):
    """Получает случайные билеты для режима 'Рандом-экзамен'."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM tickets ORDER BY RANDOM() LIMIT ?', (count,))
        return await cursor.fetchall()

async def check_db_empty():
    """Проверяет, есть ли данные в базе."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT COUNT(*) FROM tickets')
        result = await cursor.fetchone()
        return result[0] == 0

async def get_random_ticket_with_code():
    """Получает случайный билет, у которого есть и код, и описание ошибки."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            'SELECT * FROM tickets WHERE code IS NOT NULL AND code_error_desc IS NOT NULL ORDER BY RANDOM() LIMIT 1'
        )
        return await cursor.fetchone()