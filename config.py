import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    LLM_API_BASE = os.getenv("LLM_API_BASE", "http://localhost:8000/v1")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "dummy")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./interview.db")

    # Модели из вашего ТЗ
    MODEL_CHAT = "qwen3-32b-awq"
    MODEL_CODER = "qwen3-coder-30b-a3b-instruct-fp8"
    EMBEDDING_MODEL = "bge-m3"

    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "static/uploads")
    AUDIO_OUTPUT_DIR = os.getenv("AUDIO_OUTPUT_DIR", "static/questions")

settings = Settings()

# Создаем папки при старте
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.AUDIO_OUTPUT_DIR, exist_ok=True)