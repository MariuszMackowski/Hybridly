from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models_registry  # noqa: F401  (registers all models on Base.metadata)
from app.config import get_settings
from app.db import Base, get_db
from app.main import create_app


@pytest.fixture(scope="session")
def test_engine():
    """Engine bound to the test database with a freshly created schema."""
    url = get_settings().test_database_url
    assert url, "TEST_DATABASE_URL must be set"
    engine = create_engine(url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine) -> Iterator[Session]:
    """Session inside an outer transaction that is rolled back after each test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """API client whose requests share the test's database session."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
