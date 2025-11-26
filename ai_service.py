import os
import json
from openai import OpenAI
from gtts import gTTS
import speech_recognition as sr
from config import settings

client = OpenAI(
    base_url=settings.LLM_API_BASE,
    api_key=settings.LLM_API_KEY
)

class AIService:
    @staticmethod
    def text_to_speech(text: str, session_id: int, q_num: int) -> str:
        """Синтез речи (Q -> Audio)"""
        tts = gTTS(text=text, lang='ru')
        filename = f"q_{session_id}_{q_num}.mp3"
        filepath = os.path.join(settings.AUDIO_OUTPUT_DIR, filename)
        tts.save(filepath)
        return f"/static/questions/{filename}"

    @staticmethod
    def speech_to_text(audio_path: str) -> str:
        """Транскрибация (Audio -> Text)"""
        recognizer = sr.Recognizer()
        # Для .mp3 или .webm может потребоваться конвертация через pydub в .wav
        # Здесь подразумевается, что фронтенд шлет .wav
        try:
            with sr.AudioFile(audio_path) as source:
                audio_data = recognizer.record(source)
                # Используем Google как заглушку, в идеале - локальный Whisper
                text = recognizer.recognize_google(audio_data, language="ru-RU")
                return text
        except Exception as e:
            print(f"STT Error: {e}")
            return "Не удалось разобрать ответ (ошибка аудио)."

    @staticmethod
    def generate_theory_question(context_history: list, topic="Python Backend Developer") -> str:
        """LLM: qwen3-32b-awq генерирует вопрос"""
        prompt = f"""
        Ты интервьюер на техническом собеседовании. Тема: {topic}.
        Задай ОДИН короткий теоретический вопрос.
        Предыдущие вопросы: {', '.join(context_history)}.
        Не повторяйся. Вопрос должен требовать устного ответа.
        Верни только текст вопроса.
        """
        response = client.chat.completions.create(
            model=settings.MODEL_CHAT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()

    @staticmethod
    def analyze_theory_answer(question: str, answer: str) -> dict:
        """LLM: qwen3-32b-awq оценивает ответ 1-5"""
        prompt = f"""
        Вопрос: {question}
        Ответ кандидата (расшифровка голоса): "{answer}"
        
        Оцени правильность ответа от 1 до 5 целым числом.
        Верни JSON: {{"score": int, "comment": "string"}}
        """
        response = client.chat.completions.create(
            model=settings.MODEL_CHAT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"} # Если API поддерживает
        )
        # Обработка ответа (парсинг JSON)
        content = response.choices[0].message.content
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1]
            return json.loads(content)
        except:
            return {"score": 1, "comment": "Ошибка анализа ответа"}

    @staticmethod
    def generate_algo_task(difficulty: str) -> str:
        """LLM: qwen3-coder-30b-a3b-instruct-fp8 генерирует задачу"""
        level_desc = "начального уровня (arrays, strings)" if difficulty == "easy" else "сложного уровня (trees, graphs, dp)"
        prompt = f"""
        Сгенерируй одну задачу на Python {level_desc}.
        Выведи:
        1. Условие задачи.
        2. Примеры входных и выходных данных.
        
        Не пиши решение!
        """
        response = client.chat.completions.create(
            model=settings.MODEL_CODER,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content

    @staticmethod
    def review_code(task_text: str, user_code: str) -> dict:
        """
        LLM: qwen3-coder-30b-a3b-instruct-fp8 проверяет код.
        Проверяем: Правильность, Стиль, AI-Written probability.
        """
        prompt = f"""
        Задача: {task_text}
        
        Решение кандидата:
        ```python
        {user_code}
        ```
        
        Выполни Code Review.
        1. Оцени правильность и работоспособность (1-5).
        2. Оцени стиль кода (variable naming, pep8).
        3. Оцени вероятность того, что этот код написал AI (0.0 - 1.0), основываясь на комментариях и шаблонности.
        
        Верни JSON: 
        {{
            "score": int, 
            "is_correct": bool,
            "style_comment": "str", 
            "ai_probability": float,
            "explanation": "str"
        }}
        """
        response = client.chat.completions.create(
            model=settings.MODEL_CODER,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        content = response.choices[0].message.content
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            return json.loads(content)
        except:
            return {"score": 1, "style_comment": "Error", "ai_probability": 0.0}

ai_handler = AIService()