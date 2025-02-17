import aiosqlite
import asyncio
import logging
import os
from datetime import datetime
from config import DB_PATH

logger = logging.getLogger(__name__)

# Создаем директорию для базы данных, если её нет
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Глобальное подключение к базе данных
db = None

async def init_db():
    """Инициализация базы данных"""
    global db
    
    # Создаем подключение к базе данных
    db = await aiosqlite.connect(DB_PATH)
    
    async with db.cursor() as cur:
        # Создаем таблицу пользователей
        await cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            thinking_mode INTEGER DEFAULT 0,
            selected_model TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        logger.info("Users table created/verified")
        
        # Создаем таблицу чатов
        await cur.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            is_active INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        ''')
        logger.info("Chats table created/verified")
        
        # Создаем таблицу сообщений чата
        await cur.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id)
        )
        ''')
        logger.info("Chat messages table created/verified")
        
        await db.commit()
        logger.info("All tables created successfully")


async def create_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """Создает нового пользователя"""
    async with db.cursor() as cur:
        # Проверяем, существует ли пользователь
        await cur.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        existing_user = await cur.fetchone()
        
        if not existing_user:
            # Создаем нового пользователя
            await cur.execute(
                '''
                INSERT INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
                ''',
                (user_id, username, first_name, last_name)
            )
            
            # Создаем чат по умолчанию для нового пользователя
            await cur.execute(
                '''
                INSERT INTO chats (user_id, name, is_active)
                VALUES (?, ?, 1)
                ''',
                (user_id, "Чат по умолчанию")
            )
            
            await db.commit()
            logger.info(f"Created new user: {user_id}")
        else:
            logger.info(f"User already exists: {user_id}")


async def get_thinking_mode(user_id: int) -> bool:
    """Получает статус режима размышления пользователя"""
    async with db.execute(
        'SELECT thinking_mode FROM users WHERE user_id = ?',
        (user_id,)
    ) as cur:
        result = await cur.fetchone()
        return bool(result[0]) if result else False


async def set_thinking_mode(user_id: int, enabled: bool):
    """Устанавливает режим размышления пользователя"""
    async with db.cursor() as cur:
        await cur.execute(
            'UPDATE users SET thinking_mode = ? WHERE user_id = ?',
            (int(enabled), user_id)
        )
        await db.commit()


async def get_user_model(user_id: int) -> str:
    """Получает выбранную модель пользователя"""
    async with db.execute(
        'SELECT selected_model FROM users WHERE user_id = ?',
        (user_id,)
    ) as cursor:
        result = await cursor.fetchone()
        return result[0] if result else None


async def update_user_model(user_id: int, model: str):
    """Обновляет выбранную модель пользователя"""
    async with db.cursor() as cur:
        await cur.execute(
            'UPDATE users SET selected_model = ? WHERE user_id = ?',
            (model, user_id)
        )
        await db.commit()


async def create_default_chat(user_id: int) -> int:
    """Создает чат по умолчанию для пользователя"""
    async with db.cursor() as cur:
        # Проверяем, есть ли уже активный чат
        cursor = await db.execute(
            'SELECT chat_id FROM chats WHERE user_id = ? AND is_active = 1',
            (user_id,)
        )
        active_chat = await cursor.fetchone()
        
        if active_chat:
            return active_chat[0]
        
        # Создаем чат по умолчанию
        cursor = await cur.execute(
            'INSERT INTO chats (user_id, name, is_active) VALUES (?, ?, 1)',
            (user_id, "Чат по умолчанию")
        )
        await db.commit()
        return cursor.lastrowid


async def get_user_chats(user_id: int) -> list:
    """Получает список чатов пользователя"""
    async with db.execute(
        '''
        SELECT chat_id, name, is_active, created_at 
        FROM chats 
        WHERE user_id = ?
        ORDER BY created_at DESC
        ''',
        (user_id,)
    ) as cursor:
        chats = await cursor.fetchall()
        return [
            {
                'id': chat[0],
                'name': chat[1],
                'is_active': bool(chat[2]),
                'created_at': chat[3]
            }
            for chat in chats
        ]


async def get_active_chat(user_id: int) -> dict:
    """Получает активный чат пользователя"""
    async with db.execute(
        '''
        SELECT chat_id, name, created_at 
        FROM chats 
        WHERE user_id = ? AND is_active = 1
        ''',
        (user_id,)
    ) as cursor:
        chat = await cursor.fetchone()
        if not chat:
            # Если активного чата нет, создаем новый
            chat_id = await create_default_chat(user_id)
            cursor = await db.execute(
                'SELECT chat_id, name, created_at FROM chats WHERE chat_id = ?',
                (chat_id,)
            )
            chat = await cursor.fetchone()
            
        return {
            'id': chat[0],
            'name': chat[1],
            'created_at': chat[2]
        }


async def create_chat(user_id: int, name: str) -> int:
    """Создает новый чат"""
    async with db.cursor() as cur:
        # Деактивируем текущий активный чат
        await cur.execute(
            'UPDATE chats SET is_active = 0 WHERE user_id = ? AND is_active = 1',
            (user_id,)
        )
        
        # Создаем новый активный чат
        cursor = await cur.execute(
            'INSERT INTO chats (user_id, name, is_active) VALUES (?, ?, 1)',
            (user_id, name)
        )
        await db.commit()
        return cursor.lastrowid


async def update_chat(chat_id: int, name: str = None, is_active: bool = None):
    """Обновляет параметры чата"""
    async with db.cursor() as cur:
        if is_active is not None and is_active:
            # Если делаем чат активным, деактивируем остальные
            user_cursor = await db.execute(
                'SELECT user_id FROM chats WHERE chat_id = ?',
                (chat_id,)
            )
            user = await user_cursor.fetchone()
            if user:
                await cur.execute(
                    'UPDATE chats SET is_active = 0 WHERE user_id = ?',
                    (user[0],)
                )
        
        # Обновляем параметры чата
        updates = []
        params = []
        if name is not None:
            updates.append('name = ?')
            params.append(name)
        if is_active is not None:
            updates.append('is_active = ?')
            params.append(int(is_active))
            
        if updates:
            query = f'UPDATE chats SET {", ".join(updates)} WHERE chat_id = ?'
            params.append(chat_id)
            await cur.execute(query, params)
            await db.commit()


async def delete_chat(chat_id: int):
    """Удаляет чат"""
    async with db.cursor() as cur:
        try:
            # Проверяем, был ли чат активным и получаем user_id
            cursor = await db.execute(
                'SELECT user_id, is_active FROM chats WHERE chat_id = ?',
                (chat_id,)
            )
            chat_info = await cursor.fetchone()
            
            if not chat_info:
                logger.warning(f"Attempted to delete non-existent chat: {chat_id}")
                return
                
            user_id, was_active = chat_info
            
            # Удаляем сообщения чата
            await cur.execute(
                'DELETE FROM chat_messages WHERE chat_id = ?',
                (chat_id,)
            )
            
            # Удаляем сам чат
            await cur.execute(
                'DELETE FROM chats WHERE chat_id = ?',
                (chat_id,)
            )
            
            # Если удаленный чат был активным, делаем активным другой чат
            if was_active:
                # Находим самый новый чат пользователя
                cursor = await db.execute(
                    '''
                    SELECT chat_id FROM chats 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT 1
                    ''',
                    (user_id,)
                )
                newest_chat = await cursor.fetchone()
                
                if newest_chat:
                    # Делаем этот чат активным
                    await cur.execute(
                        'UPDATE chats SET is_active = 1 WHERE chat_id = ?',
                        (newest_chat[0],)
                    )
                else:
                    # Если чатов не осталось, создаем новый дефолтный
                    await cur.execute(
                        '''
                        INSERT INTO chats (user_id, name, is_active)
                        VALUES (?, ?, 1)
                        ''',
                        (user_id, "Чат по умолчанию")
                    )
            
            await db.commit()
            logger.info(f"Chat {chat_id} deleted successfully")
            
        except Exception as e:
            logger.error(f"Error deleting chat {chat_id}: {e}")
            raise


async def clear_chat_history(chat_id: int):
    """Очищает историю сообщений чата"""
    async with db.cursor() as cur:
        await cur.execute('DELETE FROM chat_messages WHERE chat_id = ?', (chat_id,))
        await db.commit()


async def add_chat_message(chat_id: int, role: str, content: str):
    """Добавляет сообщение в историю чата"""
    async with db.cursor() as cur:
        await cur.execute(
            'INSERT INTO chat_messages (chat_id, role, content) VALUES (?, ?, ?)',
            (chat_id, role, content)
        )
        await db.commit()


async def get_chat_history(chat_id: int, limit: int = 10) -> list:
    """Получает историю сообщений чата"""
    async with db.execute(
        '''
        SELECT role, content, created_at 
        FROM chat_messages 
        WHERE chat_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        ''',
        (chat_id, limit)
    ) as cursor:
        messages = await cursor.fetchall()
        return [
            {
                'role': msg[0],
                'content': msg[1],
                'created_at': msg[2]
            }
            for msg in messages
        ]
