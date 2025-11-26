from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class InterviewSession(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, unique=True, index=True)
    interview_type = Column(String)  # "short" или "long"
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="theory_progress") # theory_progress, theory_done, algo_progress, completed

    final_score = Column(Float, default=0.0)

    # === ГЕНЕРАЦИЯ КОЛОНОК ===
    # Мы генерируем поля явно, чтобы соответствовать требованию: "одному вопросу соответствует одна оценка"
    # Q1 - Q25: Теория
    # Q26 - Q27: Задачи

    # Мета-поле для хранения истории вопросов, чтобы LLM не повторялась
    # Формат JSON string: ["Question 1?", "Question 2?"]
    question_history = Column(Text, default="[]")

# Динамическое добавление атрибутов в класс (Question text, Answer text, Score)
# q{i}_text - сам вопрос
# q{i}_answer - ответ пользователя
# q{i}_score - оценка 1-5
# q{i}_feedback - комментарий нейросети (для Q26/27 проверка стиля и AI)

for i in range(1, 28):
    setattr(InterviewSession, f"q{i}_text", Column(Text, nullable=True))
    setattr(InterviewSession, f"q{i}_answer", Column(Text, nullable=True))
    setattr(InterviewSession, f"q{i}_score", Column(Integer, default=0)) # 1-5

    # Для задач добавляем поле проверки на ИИ
    if i >= 26:
        setattr(InterviewSession, f"q{i}_ai_probability", Column(Float, default=0.0))
        setattr(InterviewSession, f"q{i}_style_comment", Column(Text, nullable=True))

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()