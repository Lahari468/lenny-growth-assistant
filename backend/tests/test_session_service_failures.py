import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.services.session_chat import PersistenceError, create_session


class FailingDatabase:
    def add(self, item):
        pass

    def commit(self):
        raise SQLAlchemyError("database unavailable")

    def rollback(self):
        self.rolled_back = True


def test_create_session_maps_database_failure_without_details():
    database = FailingDatabase()
    with pytest.raises(PersistenceError, match="Unable to create session"):
        create_session(database, "Ada", None, "ollama")
    assert database.rolled_back is True
