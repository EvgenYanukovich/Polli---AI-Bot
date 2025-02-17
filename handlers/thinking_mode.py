import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from database import db
from config import THINKING_MODE_PROMPT, DEFAULT_TEXT_MODEL

logger = logging.getLogger(__name__)

# Создаем роутер
router = Router()

# Сохраняем сервис AI как атрибут роутера
_ai_service = None

def register_handlers(dp, ai_service):
    """Регистрация обработчиков режима размышления"""
    global _ai_service
    _ai_service = ai_service
    
    logger.info("Registering thinking mode handlers")
    
    # Регистрируем команду /think
    router.message.register(toggle_thinking_mode, Command("think"))
    logger.info("Registered /think command handler")
    
    # Регистрируем обработчик callback'ов режима размышления
    router.callback_query.register(
        process_thinking_callback,
        F.data.startswith("thinking_mode_")
    )
    logger.info("Registered thinking mode callback handler")
    
    # Регистрируем обработчик сообщений
    # Исключаем все известные команды
    router.message.register(
        handle_message,
        F.text,
        ~Command(commands=["start", "help", "think", "model"])
    )
    logger.info("Registered message handler")
    
    # Добавляем роутер в диспетчер
    dp.include_router(router)
    logger.info("All thinking mode handlers registered successfully")


async def toggle_thinking_mode(message: Message):
    """Обработчик команды /think"""
    try:
        user_id = message.from_user.id
        current_mode = await db.get_thinking_mode(user_id)
        new_mode = not current_mode
        
        await db.set_thinking_mode(user_id, new_mode)
        
        if new_mode:
            response = "🤔 Режим размышления включен. Теперь я буду подробно объяснять ход своих мыслей."
        else:
            response = "✨ Режим размышления выключен. Вернулся к обычному режиму общения."
            
        await message.reply(response)
        logger.info(f"Thinking mode {'enabled' if new_mode else 'disabled'} for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error toggling thinking mode: {e}")
        await message.reply("Произошла ошибка при изменении режима. Попробуйте позже.")


async def process_thinking_callback(callback: CallbackQuery):
    """Обработчик callback'ов режима размышления"""
    try:
        action = callback.data.split('_')[2]
        if action == "toggle":
            user_id = callback.from_user.id
            current_mode = await db.get_thinking_mode(user_id)
            new_mode = not current_mode
            
            await db.set_thinking_mode(user_id, new_mode)
            
            await callback.message.edit_text(
                f"{'🤔 Режим размышления включен' if new_mode else '✨ Режим размышления выключен'}"
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error processing thinking mode callback: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)


async def handle_message(message: Message, state: FSMContext):
    """Обработчик всех текстовых сообщений"""
    try:
        # Проверяем, не ожидаем ли мы ввода имени чата
        current_state = await state.get_state()
        if current_state is not None:
            # Если есть активное состояние, пропускаем сообщение
            return
            
        # Получаем настройки пользователя
        user_id = message.from_user.id
        thinking_mode = await db.get_thinking_mode(user_id)
        selected_model = await db.get_user_model(user_id) or DEFAULT_TEXT_MODEL
        
        # Получаем активный чат
        chat = await db.get_active_chat(user_id)
        
        # Сохраняем сообщение пользователя
        await db.add_chat_message(chat['id'], "user", message.text)
        
        # Получаем историю чата
        history = await db.get_chat_history(chat['id'])
        
        # Формируем сообщения для AI
        messages = []
        
        # Добавляем системный промпт для режима размышления
        if thinking_mode:
            messages.append({
                "role": "system",
                "content": THINKING_MODE_PROMPT
            })
        
        # Добавляем историю чата
        for msg in reversed(history):  # Разворачиваем историю в хронологическом порядке
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Получаем ответ от AI
        response = await _ai_service.generate_response(
            messages,
            model=selected_model
        )
        
        # Сохраняем ответ в историю
        await db.add_chat_message(chat['id'], "assistant", response)
        
        # Отправляем ответ пользователю
        await message.reply(response)
        logger.info(f"Response sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await message.reply(
            "Извините, произошла ошибка при обработке вашего сообщения. "
            "Попробуйте позже или обратитесь к администратору."
        )
