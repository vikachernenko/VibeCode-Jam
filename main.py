import os
import shutil
import json
from datetime import datetime, timedelta

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import init_db, get_db, InterviewSession
from ai_service import ai_handler
from grading import calculate_weighted_score
from config import settings

# Инициализация
app = FastAPI(title="InterviewAI")
init_db()

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статические файлы для раздачи аудио вопросов
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.post("/api/interview/start")
def start_session(email: str = Form(...), type: str = Form(...), db: Session = Depends(get_db)):
    """Создает сессию и генерирует 1-й вопрос"""
    if type not in ["short", "long"]:
        raise HTTPException(400, "Invalid type")

    new_session = InterviewSession(user_email=email, interview_type=type)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    # Генерация первого вопроса
    question_text = ai_handler.generate_theory_question([], "Общие вопросы Python")
    audio_url = ai_handler.text_to_speech(question_text, new_session.id, 1)

    # Сохраняем в БД
    new_session.q1_text = question_text
    new_session.question_history = json.dumps([question_text])
    db.commit()

    return {
        "session_id": new_session.id,
        "q_num": 1,
        "text": question_text,
        "audio": audio_url,
        "mode": "theory"
    }

@app.post("/api/interview/theory/answer")
async def submit_audio_answer(
        session_id: int = Form(...),
        q_num: int = Form(...),
        file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """
    Принимает аудио (Blob).
    1. STT
    2. Анализ ответа LLM -> Score
    3. Запись в q{i} поля
    4. Генерация следующего вопроса ИЛИ переход к задачам
    """
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")

    # Сохранение файла
    filename = f"ans_{session_id}_{q_num}.wav"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 1. STT
    user_text = ai_handler.speech_to_text(filepath)
    setattr(session, f"q{q_num}_answer", user_text)

    # 2. Оценка
    question_text = getattr(session, f"q{q_num}_text")
    analysis = ai_handler.analyze_theory_answer(question_text, user_text)
    setattr(session, f"q{q_num}_score", analysis.get('score', 1))

    db.commit()

    # Проверка тайминга для LONG собеседования (если > 30 минут)
    elapsed = datetime.utcnow() - session.created_at
    if session.interview_type == "long" and elapsed > timedelta(minutes=30):
        # Принудительный переход к кодингу
        return _start_algo_phase(session, db)

    # Определение следующего шага
    limit = 10 if session.interview_type == "short" else 25
    next_q = q_num + 1

    # Если лимит вопросов исчерпан
    if next_q > limit:
        if session.interview_type == "short":
            session.status = "completed"
            session.final_score = calculate_weighted_score(session.id, db)
            db.commit()
            return {"status": "completed", "final_score": session.final_score}
        else:
            # Переход к задачам
            return _start_algo_phase(session, db)

    # Генерация следующего вопроса
    history = json.loads(session.question_history)
    new_q_text = ai_handler.generate_theory_question(history)
    history.append(new_q_text)

    session.question_history = json.dumps(history)
    setattr(session, f"q{next_q}_text", new_q_text)

    audio_url = ai_handler.text_to_speech(new_q_text, session_id, next_q)
    db.commit()

    return {
        "status": "next_theory",
        "q_num": next_q,
        "text": new_q_text,
        "audio": audio_url
    }

def _start_algo_phase(session, db):
    """Вспомогательная функция перехода к алго"""
    session.status = "algo_progress"

    # Генерируем Q26 (Easy)
    task_text = ai_handler.generate_algo_task("easy")
    session.q26_text = task_text
    db.commit()

    return {
        "status": "algo_start",
        "q_num": 26,
        "task_text": task_text,
        "difficulty": "Easy"
    }

@app.post("/api/interview/code/submit")
def submit_code_answer(
        session_id: int = Form(...),
        q_num: int = Form(...), # 26 или 27
        code: str = Form(...),
        db: Session = Depends(get_db)
):
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()

    # Записываем ответ
    setattr(session, f"q{q_num}_answer", code)

    # Оценка кода
    task_text = getattr(session, f"q{q_num}_text")
    review = ai_handler.review_code(task_text, code)

    setattr(session, f"q{q_num}_score", review.get('score', 1))
    setattr(session, f"q{q_num}_ai_probability", review.get('ai_probability', 0.0))
    setattr(session, f"q{q_num}_style_comment", review.get('style_comment', ''))

    db.commit()

    # Логика перехода между задачами
    if q_num == 26:
        # Переход ко 2-й задаче (Hard)
        task_hard = ai_handler.generate_algo_task("hard")
        session.q27_text = task_hard
        db.commit()
        return {
            "status": "next_algo",
            "q_num": 27,
            "task_text": task_hard,
            "difficulty": "Hard"
        }

    elif q_num == 27:
        # Финиш
        session.status = "completed"
        final_points = calculate_weighted_score(session.id, db)
        session.final_score = final_points
        db.commit()
        return {
            "status": "completed",
            "final_score": final_points
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)