import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import db

logger = logging.getLogger(__name__)

router = Router()

class ChatStates(StatesGroup):
    """Состояния для управления чатами"""
    waiting_for_chat_name = State()  # Ожидание имени чата
    waiting_for_chat_rename = State()  # Ожидание нового имени чата


def register_handlers(dp):
    """Регистрация обработчиков команд чата"""
    logger.info("Registering chat command handlers")
    
    # Регистрируем команду /chats
    router.message.register(cmd_chats, Command("chats"))
    
    # Регистрируем обработчики callback'ов
    router.callback_query.register(
        process_chat_list_callback,
        lambda c: c.data and c.data.startswith("chat_list_")
    )
    router.callback_query.register(
        process_chat_action_callback,
        lambda c: c.data and c.data.startswith("chat_action_")
    )
    
    # Регистрируем обработчик ввода имени чата
    router.message.register(
        process_chat_name,
        ChatStates.waiting_for_chat_name
    )
    router.message.register(
        process_chat_rename,
        ChatStates.waiting_for_chat_rename
    )
    
    # Добавляем роутер в диспетчер
    dp.include_router(router)
    logger.info("Chat command handlers registered successfully")


async def show_chat_list_to_chat(chat_id: int, user_id: int, message: Message = None):
    """Показывает список чатов в указанный чат"""
    try:
        # Получаем список чатов пользователя
        chats = await db.get_user_chats(user_id)
        
        # Создаем клавиатуру
        builder = InlineKeyboardBuilder()
        
        # Добавляем кнопки для каждого чата
        for chat in chats:
            # Добавляем отметку к активному чату
            text = f"✅ {chat['name']}" if chat['is_active'] else chat['name']
            builder.button(
                text=text,
                callback_data=f"chat_list_{chat['id']}"
            )
        
        # Добавляем кнопку создания нового чата
        builder.button(
            text="➕ Создать новый чат",
            callback_data="chat_list_new"
        )
        
        # Располагаем кнопки в один столбец
        builder.adjust(1)
        
        # Отправляем сообщение
        text = "Выберите чат для управления:\n✅ - текущий активный чат"
        if message:
            await message.answer(text=text, reply_markup=builder.as_markup())
        else:
            # Для callback query используем bot.send_message
            await message.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=builder.as_markup()
            )
        logger.info(f"Chat list shown to user: {user_id}")
        
    except Exception as e:
        logger.error(f"Error in chats command: {e}")
        error_text = (
            "Произошла ошибка при получении списка чатов. "
            "Попробуйте позже или обратитесь к администратору."
        )
        if message:
            await message.answer(text=error_text)
        else:
            await message.bot.send_message(chat_id=chat_id, text=error_text)


async def show_chat_list(message: Message):
    """Показывает список чатов пользователя"""
    await show_chat_list_to_chat(message.chat.id, message.from_user.id, message)


async def cmd_chats(message: Message):
    """Обработчик команды /chats"""
    await show_chat_list(message)


async def process_chat_list_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора чата из списка"""
    try:
        action = callback.data.split('_')[2]
        user_id = callback.from_user.id
        
        if action == 'new':
            # Запрашиваем имя нового чата
            await state.set_state(ChatStates.waiting_for_chat_name)
            await callback.message.edit_text(
                "Введите название для нового чата:",
                reply_markup=None
            )
        else:
            # Показываем меню управления выбранным чатом
            chat_id = int(action)
            builder = InlineKeyboardBuilder()
            
            # Добавляем кнопки управления
            builder.button(
                text="🔵 Сделать активным",
                callback_data=f"chat_action_activate_{chat_id}"
            )
            builder.button(
                text="✏️ Переименовать",
                callback_data=f"chat_action_rename_{chat_id}"
            )
            builder.button(
                text="🗑️ Очистить историю",
                callback_data=f"chat_action_clear_{chat_id}"
            )
            builder.button(
                text="❌ Удалить чат",
                callback_data=f"chat_action_delete_{chat_id}"
            )
            builder.button(
                text="⬅️ Назад к списку",
                callback_data="chat_action_back"
            )
            
            # Располагаем кнопки в один столбец
            builder.adjust(1)
            
            await callback.message.edit_text(
                "Выберите действие:",
                reply_markup=builder.as_markup()
            )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error processing chat list callback: {e}")
        await callback.answer(
            "Произошла ошибка. Попробуйте позже.",
            show_alert=True
        )


async def process_chat_action_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик действий с чатом"""
    try:
        parts = callback.data.split('_')
        action = parts[2]
        chat = callback.message.chat
        
        if action == 'back':
            # Возвращаемся к списку чатов
            await show_chat_list_to_chat(chat.id, callback.from_user.id, callback.message)
            await callback.answer()
            return
            
        chat_id = int(parts[3])
        
        if action == 'activate':
            # Активируем выбранный чат
            await db.update_chat(chat_id, is_active=True)
            # Отправляем новое сообщение вместо редактирования старого
            await callback.message.delete()  # Удаляем старое сообщение
            await show_chat_list_to_chat(chat.id, callback.from_user.id, callback.message)  # Отправляем новое
            await callback.answer("Чат активирован")
            
        elif action == 'rename':
            # Запрашиваем новое имя чата
            await state.set_state(ChatStates.waiting_for_chat_rename)
            await state.update_data(chat_id=chat_id)
            await callback.message.edit_text(
                "Введите новое название чата:",
                reply_markup=None
            )
            
        elif action == 'clear':
            # Очищаем историю чата
            await db.clear_chat_history(chat_id)
            await callback.answer("История чата очищена")
            # Отправляем новое сообщение
            await callback.message.delete()
            await show_chat_list_to_chat(chat.id, callback.from_user.id, callback.message)
            
        elif action == 'delete':
            # Удаляем чат
            await db.delete_chat(chat_id)
            await callback.answer("Чат удален")
            # Отправляем новое сообщение
            await callback.message.delete()
            await show_chat_list_to_chat(chat.id, callback.from_user.id, callback.message)
            
    except Exception as e:
        logger.error(f"Error processing chat action callback: {e}")
        await callback.answer(
            "Произошла ошибка. Попробуйте позже.",
            show_alert=True
        )


async def process_chat_name(message: Message, state: FSMContext):
    """Обработчик ввода имени нового чата"""
    try:
        # Создаем новый чат
        chat_id = await db.create_chat(message.from_user.id, message.text)
        
        # Сбрасываем состояние
        await state.clear()
        
        # Показываем обновленный список чатов
        await show_chat_list(message)
        
    except Exception as e:
        logger.error(f"Error processing chat name: {e}")
        await message.reply(
            "Произошла ошибка при создании чата. "
            "Попробуйте позже или обратитесь к администратору."
        )


async def process_chat_rename(message: Message, state: FSMContext):
    """Обработчик ввода нового имени чата"""
    try:
        # Получаем ID чата из состояния
        data = await state.get_data()
        chat_id = data.get('chat_id')
        
        if chat_id:
            # Обновляем имя чата
            await db.update_chat(chat_id, name=message.text)
            
            # Сбрасываем состояние
            await state.clear()
            
            # Показываем обновленный список чатов
            await show_chat_list(message)
            
    except Exception as e:
        logger.error(f"Error processing chat rename: {e}")
        await message.reply(
            "Произошла ошибка при переименовании чата. "
            "Попробуйте позже или обратитесь к администратору."
        )
