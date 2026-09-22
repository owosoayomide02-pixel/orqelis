async def test_register_requires_terms(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "a@example.com",
            "password": "correcthorse",
            "accept_terms": False,
            "acknowledge_privacy": True,
        },
    )
    assert response.status_code == 400


async def test_register_and_me(client):
    from tests.conftest import register

    data = await register(client, "owner@example.com")
    assert data["email"] == "owner@example.com"
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "owner@example.com"
    assert me.json()["organizations"]


async def test_login_lockout_and_wrong_password(client):
    from tests.conftest import register

    await register(client, "lock@example.com")
    await client.post("/api/v1/auth/logout")
    for _ in range(3):
        bad = await client.post("/api/v1/auth/login", json={"email": "lock@example.com", "password": "wrongpass"})
        assert bad.status_code == 401
    good = await client.post("/api/v1/auth/login", json={"email": "lock@example.com", "password": "correcthorse"})
    assert good.status_code == 200
