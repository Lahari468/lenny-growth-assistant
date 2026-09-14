"""
Shared fixtures for database tests.

Tests run against `TEST_DATABASE_URL` (a separate database from the one the
app uses for local development) so they can never touch real data. The
schema is created directly from the ORM models (`Base.metadata.create_all`)
rather than by running Alembic migrations, since these tests exercise model
behavior, not migration behavior — the migration itself is verified
separately (see README).

Every test runs inside a transaction that is rolled back afterward, so
tests are isolated from each other without needing to recreate the schema
per test.

Requires PostgreSQL with the pgvector extension enabled on
TEST_DATABASE_URL. If pgvector is missing, table creation will fail with a
clear error naming the `vector` type — see README for exact setup steps.
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Base


@pytest.fixture(scope="session")
def engine():
    settings = get_settings()
    test_engine = create_engine(settings.test_database_url)

    Base.metadata.create_all(test_engine)
    yield test_engine
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture()
def db_session(engine) -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    # create_savepoint mode: if a test calls session.rollback() itself
    # (e.g. after asserting an IntegrityError), SQLAlchemy rolls back to a
    # SAVEPOINT instead of ending our outer transaction, so the fixture can
    # still cleanly roll everything back afterward.
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
