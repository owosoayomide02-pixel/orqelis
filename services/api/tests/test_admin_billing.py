from tests.conftest import register


async def test_admin_overview_does_not_require_customer_login(client):
    login = await client.post("/api/v1/admin/login", json={"email": "founder@example.com", "password": "founderpass1"})
    assert login.status_code == 200
    body = login.json()
    assert body["display_name"]
    assert body["email"] == "founder@example.com"
    overview = await client.get("/api/v1/admin/overview")
    assert overview.status_code == 200
    payload = overview.json()
    assert "organizations" in payload
    assert "note" in payload
    assert payload["viewer"]["display_name"]
    assert "revenue" in payload
    assert "mrr_cents" in payload["revenue"]
    assert "transactions" in payload
    assert "organizations_detail" in payload
    assert "recent_users" in payload
    me = await client.get("/api/v1/admin/me")
    assert me.status_code == 200
    assert me.json()["display_name"]


async def test_development_subscription_activate(client):
    await register(client, "bill@example.com")
    plans = await client.get("/api/v1/subscription/plans")
    assert plans.status_code == 200
    codes = {item["code"] for item in plans.json()}
    assert "personal" in codes
    activated = await client.post("/api/v1/subscription/activate", json={"plan_code": "personal"})
    assert activated.status_code == 200
    assert activated.json()["status"] == "active"
