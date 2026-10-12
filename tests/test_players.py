def test_empty_player_list_is_200(client):
    response = client.get("/players")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}


def test_create_player_requires_login(client):
    assert client.post("/player", json={"name": "Virat", "team": "RCB"}).status_code == 401


def test_create_player_sets_owner(client, login):
    response = client.post(
        "/player", json={"name": "Virat", "team": "RCB"}, headers=login("alice")
    )
    assert response.status_code == 201
    assert response.json()["owner_id"] == 1


def test_only_owner_can_update(client, login):
    alice, bob = login("alice"), login("bob")
    player_id = client.post(
        "/player", json={"name": "Virat", "team": "RCB"}, headers=alice
    ).json()["id"]
    body = {"name": "Virat K", "team": "RCB"}
    assert client.put(f"/player/{player_id}", json=body, headers=bob).status_code == 403
    assert client.put(f"/player/{player_id}", json=body, headers=alice).status_code == 200


def test_admin_can_delete_any_player(client, login, make_admin):
    alice, boss = login("alice"), login("boss")
    make_admin("boss")
    player_id = client.post(
        "/player", json={"name": "Virat", "team": "RCB"}, headers=alice
    ).json()["id"]
    assert client.delete(f"/player/{player_id}", headers=boss).status_code == 204
    assert client.get(f"/player/{player_id}").status_code == 404


def test_player_pagination(client, login):
    headers = login("alice")
    for i in range(5):
        client.post("/player", json={"name": f"P{i}", "team": "T"}, headers=headers)
    page = client.get("/players", params={"limit": 2, "offset": 2}).json()
    assert page["total"] == 5
    assert [p["name"] for p in page["items"]] == ["P2", "P3"]


def test_pagination_limit_is_capped(client):
    assert client.get("/players", params={"limit": 1000}).status_code == 422
