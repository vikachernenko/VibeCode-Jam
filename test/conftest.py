import pytest
from httpx import AsyncClient
from main import app
from database import Base, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI
from asgi_lifespan import LifespanManager  # <-- важно

# Тестовая БД в памяти
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

# Переопределяем зависимость get_db


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
async def client():
    app.dependency_overrides[get_db] = override_get_db
    async with LifespanManager(app):  # Поднимаем приложение
        async with AsyncClient(app=app, base_url="http://testserver") as ac:
            yield ac
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def create_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
