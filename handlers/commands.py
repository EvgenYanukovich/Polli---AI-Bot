import logging
from aiogram import Router, Bot
from aiogram.types import Message, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import db
from config import DEFAULT_TEXT_MODEL

logger = logging.getLogger(__name__)

router = Router()

def get_commands() -> list[BotCommand]:
    """Возвращает список команд бота для меню"""
    return [
        BotCommand(command="start", description="Начать диалог с ботом"),
        BotCommand(command="help", description="Показать справку"),
        BotCommand(command="think", description="Включить/выключить режим размышления"),
        BotCommand(command="model", description="Выбрать модель для общения"),
        BotCommand(command="chats", description="Управление чатами")
    ]

def register_handlers(dp, ai_service):
    """Регистрация базовых обработчиков команд"""
    logger.info("Registering basic command handlers")
    
    # Регистрируем команды
    router.message.register(cmd_start, Command("start"))
    router.message.register(cmd_help, Command("help"))
    router.message.register(cmd_model, Command("model"))
    
    # Регистрируем обработчик callback'ов для выбора модели
    router.callback_query.register(
        process_model_callback,
        lambda c: c.data and c.data.startswith("model_")
    )
    
    # Сохраняем сервис AI как атрибут роутера
    router.ai_service = ai_service
    
    # Добавляем роутер в диспетчер
    dp.include_router(router)
    logger.info("Basic command handlers registered successfully")


async def cmd_start(message: Message):
    """
    Обработчик команды /start
    Создает запись о пользователе в базе данных
    """
    try:
        user = message.from_user
        # Создаем пользователя (это также создаст дефолтный чат)
        await db.create_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        response = f"""
Привет, {user.first_name}! 👋

Я - умный ассистент, готовый помочь тебе с различными задачами.

Доступные команды:
/help - показать справку
/think - включить/выключить режим размышления
/model - выбрать модель для общения
/chats - управление чатами

Просто напиши мне сообщение, и я постараюсь помочь!
        """
        
        await message.reply(response)
        logger.info(f"New user started bot: {user.id}")
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.reply("Произошла ошибка при запуске бота. Попробуйте позже.")


async def cmd_help(message: Message):
    """Обработчик команды /help"""
    try:
        help_text = """
🤖 Я - умный ассистент с искусственным интеллектом.

Команды:
/start - начать диалог
/help - показать это сообщение
/think - включить/выключить режим размышления
/model - выбрать модель для общения
/chats - управление чатами и историей

В обычном режиме я просто отвечаю на ваши сообщения.
В режиме размышления я подробно объясняю ход своих мыслей.

Вы можете создавать разные чаты для разных тем и переключаться между ними.
Каждый чат хранит свою историю сообщений.

Просто напишите мне сообщение, и я постараюсь помочь!
        """
        
        await message.reply(help_text)
        logger.info(f"Help shown to user: {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await message.reply("Произошла ошибка при показе справки. Попробуйте позже.")


async def cmd_model(message: Message):
    """Обработчик команды /model"""
    try:
        # Получаем список доступных моделей
        ai_service = router.ai_service
        text_models = ai_service.text_models
        
        if not text_models:
            # Если список моделей пуст, пробуем получить его
            text_models = await ai_service.get_models()
        
        if not text_models:
            # Если все равно не удалось получить модели, используем базовые
            text_models = [
                "gpt-4",
                "gpt-4o",
                "claude",
                "deepseek-chat",
                "llama-3.3-70b",
                "mistral-nemo",
                "qwen-2.5-72b"
            ]
        
        # Получаем текущую модель пользователя
        user_id = message.from_user.id
        current_model = await db.get_user_model(user_id) or DEFAULT_TEXT_MODEL
        
        # Создаем клавиатуру с моделями
        builder = InlineKeyboardBuilder()
        for model in text_models:
            # Добавляем отметку к текущей модели
            text = f"✅ {model}" if model == current_model else model
            builder.button(text=text, callback_data=f"model_{model}")
        
        # Располагаем кнопки в два столбца
        builder.adjust(2)
        
        await message.reply(
            "Выберите модель для общения:\n"
            "✅ - текущая активная модель",
            reply_markup=builder.as_markup()
        )
        logger.info(f"Model selection shown to user: {user_id}")
        
    except Exception as e:
        logger.error(f"Error in model command: {e}")
        await message.reply("Произошла ошибка при получении списка моделей. Попробуйте позже.")


async def process_model_callback(callback: CallbackQuery):
    """Обработчик callback'ов выбора модели"""
    try:
        # Получаем выбранную модель из callback data
        model = callback.data.split('_')[1]
        user_id = callback.from_user.id
        
        # Обновляем модель в базе данных
        await db.update_user_model(user_id, model)
        
        # Обновляем сообщение с выбором модели
        text_models = router.ai_service.text_models or [
            "gpt-4",
            "gpt-4o",
            "gpt-4o-mini",
            "claude",
            "deepseek-chat",
            "deepseek-r1",
            "llama-3.3-70b",
            "mistral-nemo",
            "qwen-2.5-72b",
            "qwen-2.5-coder-32b",
            "gemini-2.0-flash-thinking",
            "gemini-2.0-flash"
        ]
        
        # Создаем обновленную клавиатуру
        builder = InlineKeyboardBuilder()
        for m in text_models:
            text = f"✅ {m}" if m == model else m
            builder.button(text=text, callback_data=f"model_{m}")
        builder.adjust(2)
        
        await callback.message.edit_text(
            "Выберите модель для общения:\n"
            "✅ - текущая активная модель",
            reply_markup=builder.as_markup()
        )
        
        # Отправляем уведомление о смене модели
        await callback.answer(f"Модель изменена на {model}")
        logger.info(f"Model changed to {model} for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing model callback: {e}")
        await callback.answer("Произошла ошибка при смене модели. Попробуйте позже.", show_alert=True)
