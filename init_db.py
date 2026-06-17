import asyncio
import aiosqlite
from database import init_db, check_db_empty
from tickets_data import TICKETS_DATA # Импортируем наши чистые данные

async def populate_db():
    await init_db()
    
    if not await check_db_empty():
        print("База данных уже заполнена. Пропускаем инициализацию.")
        return

    async with aiosqlite.connect("database.db") as db:
        for ticket in TICKETS_DATA:
            await db.execute('''
                INSERT INTO tickets (id, title, theory, code, keywords, code_error_desc)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                ticket["id"],
                ticket["title"],
                ticket["theory"],
                ticket["code"],
                ticket["keywords"],
                ticket["code_error_desc"]
            ))
        await db.commit()
    print(f"✅ Успешно добавлено {len(TICKETS_DATA)} билетов в базу данных!")

if __name__ == "__main__":
    asyncio.run(populate_db())