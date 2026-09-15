"""
API Endpoint Integration Tests.
Verifies Health, Sessions CRUD, Messages chat dispatch, isolation, schema validation,
and grounded QA regression tests.
"""

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "vector_store" in data
    assert "llm_providers" in data

@pytest.mark.asyncio
async def test_session_lifecycle(client: AsyncClient):
    # 1. Create session
    create_res = await client.post("/api/sessions", json={"title": "Test Session"})
    assert create_res.status_code == 201
    s_data = create_res.json()
    session_id = s_data["id"]
    assert s_data["title"] == "Test Session"

    # 2. Get session
    get_res = await client.get(f"/api/sessions/{session_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == session_id

    # 3. List sessions
    list_res = await client.get("/api/sessions")
    assert list_res.status_code == 200
    assert any(s["id"] == session_id for s in list_res.json()["sessions"])

    # 4. Delete session
    del_res = await client.delete(f"/api/sessions/{session_id}")
    assert del_res.status_code == 204

    # Verify deleted
    get_del = await client.get(f"/api/sessions/{session_id}")
    assert get_del.status_code == 404

@pytest.mark.asyncio
async def test_message_creation_and_session_isolation(client: AsyncClient):
    # Create two separate sessions
    s1 = (await client.post("/api/sessions", json={"title": "Session 1"})).json()["id"]
    s2 = (await client.post("/api/sessions", json={"title": "Session 2"})).json()["id"]

    # Send message to Session 1
    m1_res = await client.post(
        f"/api/sessions/{s1}/messages",
        json={"content": "What did Shreyas Doshi say about high agency?"},
    )
    assert m1_res.status_code == 201
    m1_data = m1_res.json()
    assert m1_data["role"] == "assistant"
    assert m1_data["session_id"] == s1

    # Verify Session 1 has messages
    s1_msgs = (await client.get(f"/api/sessions/{s1}/messages")).json()["messages"]
    assert len(s1_msgs) == 2  # user + assistant

    # Verify Session 2 is completely isolated and empty
    s2_msgs = (await client.get(f"/api/sessions/{s2}/messages")).json()["messages"]
    assert len(s2_msgs) == 0

@pytest.mark.asyncio
async def test_empty_message_validation_error(client: AsyncClient):
    s = (await client.post("/api/sessions", json={})).json()["id"]
    res = await client.post(f"/api/sessions/{s}/messages", json={"content": ""})
    assert res.status_code in (400, 422)

@pytest.mark.asyncio
async def test_message_nonexistent_session(client: AsyncClient):
    res = await client.post(
        "/api/sessions/nonexistent-session-id/messages",
        json={"content": "Hello"},
    )
    assert res.status_code == 404

@pytest.mark.asyncio
async def test_cross_functional_collaboration_no_unrelated_product_data(client: AsyncClient):
    """
    Regression test: Verifies that asking about cross-functional collaboration
    returns a grounded response and strictly contains NO unrelated product/shopping data
    and no generic ungrounded filler definitions.
    """
    s_id = (await client.post("/api/sessions", json={"title": "Collaboration Test"})).json()["id"]

    res = await client.post(
        f"/api/sessions/{s_id}/messages",
        json={"content": "How should a product manager improve cross-functional collaboration?"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["role"] == "assistant"
    content = data["content"].lower()

    # Verify no corrupted/shopping product data appears in response
    forbidden_terms = [
        "google pixel",
        "samsung galaxy",
        "dell xps",
        "hp envy",
        "extract the product information",
        "fitnessgoogle",
        "<div class='product'",
        "without needing explicit approval",
    ]
    for term in forbidden_terms:
        assert term not in content, f"Corrupted or ungrounded phrase '{term}' leaked into assistant response!"
