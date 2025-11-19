import uuid

from fastapi.testclient import TestClient


def _create_control(client: TestClient) -> int:
    name = f"ctl-{uuid.uuid4()}"
    r = client.put("/api/v1/controls", json={"name": name})
    assert r.status_code == 200
    return r.json()["control_id"]


def _create_rule(client: TestClient) -> int:
    name = f"rule-{uuid.uuid4()}"
    r = client.put("/api/v1/rules", json={"name": name})
    assert r.status_code == 200
    return r.json()["rule_id"]


def test_create_control_and_duplicate_name(client: TestClient) -> None:
    # Given: a control name
    name = f"ctl-{uuid.uuid4()}"
    # When: creating control
    r1 = client.put("/api/v1/controls", json={"name": name})
    # Then: 200 with id
    assert r1.status_code == 200
    assert isinstance(r1.json()["control_id"], int)

    # When: creating same name again
    r2 = client.put("/api/v1/controls", json={"name": name})
    # Then: 409
    assert r2.status_code == 409


def test_control_add_rule_and_list(client: TestClient) -> None:
    # Given: a control and a rule
    control_id = _create_control(client)
    rule_id = _create_rule(client)

    # When: associating rule to control
    r = client.post(f"/api/v1/controls/{control_id}/rules/{rule_id}")
    # Then: success
    assert r.status_code == 200
    assert r.json()["success"] is True

    # When: listing control rules
    l = client.get(f"/api/v1/controls/{control_id}/rules")
    # Then: contains rule id
    assert l.status_code == 200
    assert rule_id in l.json()["rule_ids"]


def test_control_add_rule_idempotent(client: TestClient) -> None:
    # Given: a control with an associated rule
    control_id = _create_control(client)
    rule_id = _create_rule(client)
    client.post(f"/api/v1/controls/{control_id}/rules/{rule_id}")

    # When: adding same rule again
    r = client.post(f"/api/v1/controls/{control_id}/rules/{rule_id}")
    # Then: still success
    assert r.status_code == 200
    assert r.json()["success"] is True

    # And list shows once
    l = client.get(f"/api/v1/controls/{control_id}/rules")
    assert l.status_code == 200
    ids = l.json()["rule_ids"]
    assert ids.count(rule_id) == 1


def test_control_remove_rule(client: TestClient) -> None:
    # Given: a control with a rule
    control_id = _create_control(client)
    rule_id = _create_rule(client)
    client.post(f"/api/v1/controls/{control_id}/rules/{rule_id}")

    # When: removing association
    d = client.delete(f"/api/v1/controls/{control_id}/rules/{rule_id}")
    # Then: success
    assert d.status_code == 200
    assert d.json()["success"] is True

    # When: listing
    l = client.get(f"/api/v1/controls/{control_id}/rules")
    # Then: rule not present
    assert l.status_code == 200
    assert rule_id not in l.json()["rule_ids"]


def test_control_rule_assoc_404s(client: TestClient) -> None:
    # Given: ids
    control_id = _create_control(client)
    rule_id = _create_rule(client)

    # When: control missing
    r1 = client.post(f"/api/v1/controls/999999/rules/{rule_id}")
    # Then: 404
    assert r1.status_code == 404

    # When: rule missing
    r2 = client.post(f"/api/v1/controls/{control_id}/rules/999999")
    # Then: 404
    assert r2.status_code == 404

    # When: list on missing control
    r3 = client.get("/api/v1/controls/999999/rules")
    # Then: 404
    assert r3.status_code == 404

    # When: delete with missing both sides
    r4 = client.delete("/api/v1/controls/999999/rules/999999")
    # Then: 404
    assert r4.status_code == 404
