from sqlalchemy.orm import Session
from database import InterviewSession

def calculate_weighted_score(session_id: int, db: Session):
    """
    Вес теоретических вопросов: 1 балл макс за вопрос.
    Вес задачи 1 (Q26, легкая): 28 баллов.
    Вес задачи 2 (Q27, сложная): 47 баллов.

    В базе оценки хранятся как INT (1-5).
    Нам нужно нормализовать оценку (x/5) и умножить на вес.
    """

    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        return 0.0

    total_points = 0.0

    # 1. Теория (Q1 - Q25)
    # Определяем лимит вопросов в зависимости от типа
    limit = 10 if session.interview_type == "short" else 25

    for i in range(1, limit + 1):
        raw_score = getattr(session, f"q{i}_score") # Оценка от 1 до 5
        # Нормализация: 5 баллов -> 1.0 (полный вес), 1 балл -> 0.2
        weight_score = (raw_score / 5.0) * 1.0
        total_points += weight_score

    # 2. Алгоритмические задачи (только для long)
    if session.interview_type == "long":
        # Задача 1 (Q26) - Вес 28
        raw_score_26 = session.q26_score # 1-5
        score_26 = (raw_score_26 / 5.0) * 28.0
        total_points += score_26

        # Задача 2 (Q27) - Вес 47
        raw_score_27 = session.q27_score # 1-5
        score_27 = (raw_score_27 / 5.0) * 47.0
        total_points += score_27

        # Штрафы за AI (доп. логика) - опционально
        # Если ai_probability > 0.9, можно аннулировать задачу
        if session.q26_ai_probability > 0.8:
            # print("Warning: AI Detected in Task 1")
            pass

    return round(total_points, 2)