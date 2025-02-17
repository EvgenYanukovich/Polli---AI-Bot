from typing import List
import asyncio
from .blackbox_api import query_text

class ThinkingProcess:
    def __init__(self, model: str, iterations: int = 7):
        self.model = model
        self.iterations = iterations
        self.conversation_history: List[str] = []

    async def process_query(self, initial_query: str) -> str:
        """
        Обрабатывает запрос через несколько итераций "размышления"
        и возвращает структурированный ответ.
        """
        # Сохраняем начальный запрос
        self.conversation_history = [initial_query]
        current_response = initial_query

        # Выполняем итерации размышления
        for _ in range(self.iterations):
            prompt = (
                "Улучши этот ответ, добавь больше деталей и задай уточняющие вопросы:\n\n"
                f"{current_response}"
            )
            
            current_response = await query_text(prompt, self.model)
            self.conversation_history.append(current_response)

        # Формируем финальный запрос для структурирования
        final_prompt = (
            "На основе следующего диалога составь один структурированный и подробный ответ. "
            "Используй маркированные списки где это уместно, раздели информацию на логические блоки "
            "и убери все повторения:\n\n"
            f"Начальный запрос: {initial_query}\n\n"
            f"Процесс размышления:\n{'-' * 40}\n"
            + '\n'.join(f"Итерация {i+1}:\n{resp}\n{'-' * 40}" 
                       for i, resp in enumerate(self.conversation_history[1:]))
        )

        # Получаем и возвращаем структурированный ответ
        structured_response = await query_text(final_prompt, self.model)
        return structured_response

    def clear_history(self):
        """Очищает историю размышлений"""
        self.conversation_history.clear()
