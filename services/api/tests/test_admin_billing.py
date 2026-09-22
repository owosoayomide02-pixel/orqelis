from tests.conftest import register


async def test_admin_overview_does_not_require_customer_login(client):
    login = await client.post("/api/v1/admin/login", json={"email": "founder@example.com", "password": "founderpass1"})
    assert login.status_code == 200
    overview = await client.get("/api/v1/admin/overview")
    assert overview.status_code == 200
    body = overview.json()
    assert "organizations" in body
    assert "note" in body


async def test_development_subscription_activate(client):
    await register(client, "bill@example.com")
    plans = await client.get("/api/v1/subscription/plans")
    assert plans.status_code == 200
    codes = {item["code"] for item in plans.json()}
    assert "personal" in codes
    activated = await client.post("/api/v1/subscription/activate", json={"plan_code": "personal"})
    assert activated.status_code == 200
    assert activated.json()["status"] == "active"
