import logging
import g4f
from g4f.Provider import PollinationsAI

logger = logging.getLogger(__name__)

class PollinationsService:
    """Сервис для работы с PollinationsAI"""
    
    def __init__(self):
        self.text_models = [
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
    
    async def get_models(self):
        """Получить список доступных моделей"""
        return self.text_models
    
    async def generate_response(self, messages: list, model: str = "gpt-4") -> str:
        """
        Генерация ответа от модели
        
        :param messages: Список сообщений в формате [{role: str, content: str}]
        :param model: Название модели для использования
        :return: Ответ от модели
        """
        try:
            # Используем g4f для получения ответа
            response = await g4f.ChatCompletion.create_async(
                model=model,
                messages=messages,
                provider=PollinationsAI
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise
