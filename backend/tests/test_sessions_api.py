import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import sessions as sessions_api
from app.agents.pi import PiError, PiResult
from app.db.models import Message
from app.db.session import get_db
from app.main import app
from app.providers.base import ChatResponse, ProviderError
from app.rag.answerer import INSUFFICIENT_CONTEXT_MESSAGE
from app.services.session_chat import process_message


class FakeRetriever:
    def __init__(self, chunks):
        self.chunks = chunks
        self.queries = []
        self.options = []

    def retrieve(self, query, db, **kwargs):
        self.queries.append(query)
        self.options.append(kwargs)
        return self.chunks


class FakeProvider:
    def __init__(self, text="Grounded answer [S1]", error=None):
        self.text = text
        self.error = error
        self.prompts = []

    def generate(self, system_prompt, user_prompt):
        self.prompts.append((system_prompt, user_prompt))
        if self.error:
            raise self.error
        return ChatResponse(text=self.text, provider="fake", model="fake-model")


def chunk():
    return SimpleNamespace(
        document_id=uuid.uuid4(), chunk_id=uuid.uuid4(), title="Episode", source_url=None,
        chunk_index=0, score=0.9, source_file=None, speakers=[], paragraph_start=None,
        paragraph_end=None, content="Grounded transcript material.",
    )


@pytest.fixture()
def client(db_session, monkeypatch):
    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(sessions_api, "_build_retriever", lambda: FakeRetriever([]))
    monkeypatch.setattr(sessions_api, "_build_chat_provider", lambda: FakeProvider())
    monkeypatch.setattr(sessions_api, "_build_pi_bridge", lambda: None)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_post_and_get_sessions(client):
    created = client.post("/api/sessions", json={"user_name": "Ada", "title": "Growth"})
    assert created.status_code == 201
    assert created.json()["user_name"] == "Ada"

    listing = client.get("/api/sessions")
    assert listing.status_code == 200
    assert [row["id"] for row in listing.json()] == [created.json()["id"]]


def test_get_session_includes_messages_and_missing_is_404(client):
    created = client.post("/api/sessions", json={}).json()
    response = client.get("/api/sessions/%s" % created["id"])
    assert response.status_code == 200
    assert response.json()["messages"] == []
    assert client.get("/api/sessions/%s" % uuid.uuid4()).status_code == 404


def test_post_message_persists_user_and_grounded_assistant(client, db_session):
    session_id = client.post("/api/sessions", json={}).json()["id"]
    response = client.post("/api/sessions/%s/messages" % session_id, json={"content": "What did guests say?"})
    assert response.status_code == 201
    assert response.json()["assistant_message"]["content"] == INSUFFICIENT_CONTEXT_MESSAGE
    messages = db_session.query(Message).filter_by(session_id=uuid.UUID(session_id)).all()
    assert [(message.role, message.provider) for message in messages] == [("user", None), ("assistant", "none")]


def test_follow_up_uses_persisted_session_context(db_session):
    # Reuse application creation to satisfy the non-null user foreign key.
    from app.services.session_chat import create_session
    session = create_session(db_session, "Ada", None, "ollama")
    provider = FakeProvider()
    retriever = FakeRetriever([])
    process_message(db_session, session.id, "First question", retriever, provider)

    class CapturingPi:
        prompt = ""
        def run(self, prompt):
            self.prompt = prompt
            return PiResult('{"operation":"grounded_answer","top_k":1}', "test", "test-model")

    pi = CapturingPi()
    process_message(db_session, session.id, "Follow up", retriever, provider, pi_bridge=pi)
    assert "First question" in pi.prompt
    assert "Follow up" in pi.prompt


def test_follow_up_retrieval_resolves_retention_reference_from_persisted_context(db_session):
    from app.services.session_chat import create_session

    session = create_session(db_session, "Ada", None, "ollama")
    retriever = FakeRetriever([chunk()])
    provider = FakeProvider(text="Retention is a key product-growth lesson [S1].")
    first_question = "What are the most important lessons about product growth?"
    follow_up = "Can you explain the retention point in more detail?"

    process_message(db_session, session.id, first_question, retriever, provider)
    follow_up_outcome = process_message(
        db_session, session.id, follow_up, retriever, provider
    )

    retrieval_query = retriever.queries[-1]
    assert follow_up in retrieval_query
    assert first_question in retrieval_query
    assert "Retention is a key product-growth lesson" in retrieval_query
    # The answerer still receives the original follow-up, not the expanded
    # retrieval query or prior assistant prose.
    assert provider.prompts[-1][1] == follow_up
    assert "Retention is a key product-growth lesson" not in provider.prompts[-1][0]
    assert follow_up_outcome.grounded_answer.text != INSUFFICIENT_CONTEXT_MESSAGE


def test_history_can_resolve_retrieval_intent_but_never_becomes_answer_evidence(db_session):
    from app.services.session_chat import create_session

    session = create_session(db_session, "Ada", None, "ollama")
    unsupported_history_fact = "Revenue doubled because of a secret moonshot program."
    db_session.add_all(
        [
            Message(session_id=session.id, role="user", content="What happened?"),
            Message(session_id=session.id, role="assistant", content=unsupported_history_fact),
        ]
    )
    db_session.commit()
    retriever = FakeRetriever([])
    provider = FakeProvider()

    outcome = process_message(
        db_session, session.id, "Why did that happen?", retriever, provider
    )

    assert unsupported_history_fact in retriever.queries[-1]
    assert outcome.grounded_answer.text == INSUFFICIENT_CONTEXT_MESSAGE
    assert provider.prompts == []


def test_pi_plan_controls_bounded_retrieval_and_failure_falls_back(db_session):
    from app.services.session_chat import create_session
    session = create_session(db_session, "Ada", None, "ollama")
    retriever = FakeRetriever([])

    class PlanningPi:
        def run(self, prompt):
            return PiResult('{"operation":"grounded_answer","top_k":2}', "test", "test-model")

    process_message(db_session, session.id, "Question", retriever, FakeProvider(), pi_bridge=PlanningPi(), top_k=5)
    assert retriever.options[-1]["top_k"] == 2

    class UnavailablePi:
        def run(self, prompt):
            raise PiError("unavailable")

    process_message(db_session, session.id, "Retry", retriever, FakeProvider(), pi_bridge=UnavailablePi(), top_k=4)
    assert retriever.options[-1]["top_k"] == 4


def test_empty_retrieval_skips_provider_and_provider_failure_propagates(db_session):
    from app.services.session_chat import create_session
    session = create_session(db_session, "Ada", None, "ollama")
    empty_provider = FakeProvider()
    outcome = process_message(db_session, session.id, "Unsupported", FakeRetriever([]), empty_provider)
    assert outcome.grounded_answer.retrieval_count == 0
    assert empty_provider.prompts == []

    with pytest.raises(ProviderError):
        process_message(db_session, session.id, "Supported", FakeRetriever([chunk()]), FakeProvider(error=ProviderError("down")))


def test_grounded_assistant_persists_provider_and_model(db_session):
    from app.services.session_chat import create_session
    session = create_session(db_session, "Ada", None, "ollama")
    outcome = process_message(
        db_session, session.id, "Supported", FakeRetriever([chunk()]), FakeProvider()
    )
    stored = db_session.get(Message, outcome.assistant_message.id)
    assert stored.provider == "fake"
    assert stored.model == "fake-model"
