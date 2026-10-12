def test_register_hides_password(client):
    response = client.post("/register", json={"username": "alice", "password": "password123"})
    assert response.status_code == 201
    assert response.json() == {"id": 1, "username": "alice", "role": "user"}


def test_register_duplicate_username_returns_409(client):
    body = {"username": "alice", "password": "password123"}
    client.post("/register", json=body)
    assert client.post("/register", json=body).status_code == 409


def test_register_short_password_returns_422(client):
    response = client.post("/register", json={"username": "alice", "password": "abc"})
    assert response.status_code == 422


def test_login_wrong_password_returns_401(client):
    client.post("/register", json={"username": "alice", "password": "password123"})
    response = client.post("/login", data={"username": "alice", "password": "wrong-password"})
    assert response.status_code == 401


def test_me_requires_token(client):
    assert client.get("/me").status_code == 401


def test_me_returns_current_user(client, login):
    headers = login("alice")
    assert client.get("/me", headers=headers).json()["username"] == "alice"


def test_users_list_is_admin_only(client, login, make_admin):
    headers = login("alice")
    assert client.get("/users", headers=headers).status_code == 403
    make_admin("alice")
    assert client.get("/users", headers=headers).status_code == 200
