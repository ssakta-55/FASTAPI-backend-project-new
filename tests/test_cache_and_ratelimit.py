import fakeredis
import redis

from app import cache as cache_module
from app.cache import MemoryBackend, RedisBackend
from app.config import settings


def finished_match(client, headers, home, away, home_score, away_score):
    match_id = client.post(
        "/matches", json={"home_team": home, "away_team": away}, headers=headers
    ).json()["id"]
    set_score(client, headers, match_id, home_score, away_score)
    return match_id


def set_score(client, headers, match_id, home_score, away_score):
    return client.patch(
        f"/matches/{match_id}/score",
        json={"home_score": home_score, "away_score": away_score, "status": "finished"},
        headers=headers,
    )


def advance_time(monkeypatch, seconds):
    real = cache_module.time.monotonic
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: real() + seconds)


# ---------- leaderboard caching ----------
def test_second_leaderboard_call_is_a_cache_hit(client, login):
    finished_match(client, login("alice"), "A", "B", 2, 1)
    first = client.get("/leaderboard")
    second = client.get("/leaderboard")
    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"
    assert first.json() == second.json()


def test_score_update_clears_the_cache(client, login):
    headers = login("alice")
    match_id = finished_match(client, headers, "A", "B", 2, 1)
    assert client.get("/leaderboard").json()[0]["points"] == 3

    set_score(client, headers, match_id, 0, 0)  # now a draw
    after = client.get("/leaderboard")
    assert after.headers["X-Cache"] == "MISS"
    assert after.json()[0]["points"] == 1


def test_deleting_a_match_clears_the_cache(client, login):
    headers = login("alice")
    match_id = finished_match(client, headers, "A", "B", 2, 1)
    client.get("/leaderboard")
    client.delete(f"/matches/{match_id}", headers=headers)
    after = client.get("/leaderboard")
    assert after.headers["X-Cache"] == "MISS"
    assert after.json() == []


def test_cache_entry_expires_after_ttl(client, login, monkeypatch):
    finished_match(client, login("alice"), "A", "B", 2, 1)
    client.get("/leaderboard")
    advance_time(monkeypatch, settings.cache_ttl_seconds + 1)
    assert client.get("/leaderboard").headers["X-Cache"] == "MISS"


# ---------- rate limiting ----------
def test_login_is_rate_limited(client, monkeypatch):
    monkeypatch.setattr(settings, "login_rate_limit", 3)
    client.post("/register", json={"username": "alice", "password": "password123"})
    wrong = {"username": "alice", "password": "wrong-password"}
    codes = [client.post("/login", data=wrong).status_code for _ in range(5)]
    assert codes == [401, 401, 401, 429, 429]
    assert int(client.post("/login", data=wrong).headers["Retry-After"]) >= 1


def test_login_allowed_again_after_window(client, monkeypatch):
    monkeypatch.setattr(settings, "login_rate_limit", 1)
    client.post("/register", json={"username": "alice", "password": "password123"})
    wrong = {"username": "alice", "password": "wrong-password"}
    client.post("/login", data=wrong)
    assert client.post("/login", data=wrong).status_code == 429
    advance_time(monkeypatch, settings.rate_limit_window_seconds + 1)
    assert client.post("/login", data=wrong).status_code == 401


def test_register_is_rate_limited(client, monkeypatch):
    monkeypatch.setattr(settings, "register_rate_limit", 2)
    codes = [
        client.post("/register", json={"username": f"user{i}", "password": "password123"}).status_code
        for i in range(3)
    ]
    assert codes == [201, 201, 429]


def test_write_limit_is_per_user(client, login, monkeypatch):
    monkeypatch.setattr(settings, "write_rate_limit", 2)
    alice, bob = login("alice"), login("bob")
    body = {"name": "P", "team": "T"}
    codes = [client.post("/player", json=body, headers=alice).status_code for _ in range(3)]
    assert codes == [201, 201, 429]
    assert client.post("/player", json=body, headers=bob).status_code == 201


def test_reads_are_not_rate_limited(client, monkeypatch):
    monkeypatch.setattr(settings, "write_rate_limit", 1)
    assert all(client.get("/players").status_code == 200 for _ in range(5))


# ---------- the two backends ----------
def test_memory_backend_value_expires(monkeypatch):
    backend = MemoryBackend()
    backend.set("k", "v", ttl=10)
    assert backend.get("k") == "v"
    advance_time(monkeypatch, 11)
    assert backend.get("k") is None


def test_memory_backend_counter_resets_after_window(monkeypatch):
    backend = MemoryBackend()
    assert backend.incr_window("c", 60)[0] == 1
    assert backend.incr_window("c", 60)[0] == 2
    advance_time(monkeypatch, 61)
    assert backend.incr_window("c", 60)[0] == 1


def make_redis_backend():
    return RedisBackend(fakeredis.FakeRedis(decode_responses=True))


def test_redis_backend_get_set_delete():
    backend = make_redis_backend()
    assert backend.get("k") is None
    backend.set("k", "v", ttl=30)
    assert backend.get("k") == "v"
    backend.delete("k")
    assert backend.get("k") is None


def test_redis_backend_counter_has_expiry():
    backend = make_redis_backend()
    counts = [backend.incr_window("c", 60)[0] for _ in range(3)]
    assert counts == [1, 2, 3]
    seconds_left = backend.incr_window("c", 60)[1]
    assert 1 <= seconds_left <= 60


class BrokenClient:
    """Pretends Redis is down."""

    def get(self, *args, **kwargs):
        raise redis.ConnectionError("down")

    set = delete = pipeline = get


def test_redis_backend_survives_redis_outage():
    backend = RedisBackend(BrokenClient())
    assert backend.get("k") is None  # behaves like a cache miss
    backend.set("k", "v", ttl=30)  # must not raise
    backend.delete("k")  # must not raise
    assert backend.incr_window("c", 60)[0] == 0  # fail open: request is allowed
