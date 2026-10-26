import asyncio
import urllib.error

import pytest
from starlette.websockets import WebSocketDisconnect

from app import tasks
from app.config import settings
from app.realtime import ConnectionManager, manager
from app.tasks import NotificationError


def create_match(client, headers, home="A", away="B"):
    response = client.post("/matches", json={"home_team": home, "away_team": away}, headers=headers)
    return response.json()["id"]


def set_score(client, headers, match_id, home_score, away_score, status="finished"):
    return client.patch(
        f"/matches/{match_id}/score",
        json={"home_score": home_score, "away_score": away_score, "status": status},
        headers=headers,
    )


@pytest.fixture()
def queued(monkeypatch):
    """Records which match ids were queued, without running the job."""
    calls = []
    monkeypatch.setattr(tasks.send_match_finished_notification, "delay", calls.append)
    return calls


# ---------- when is a job queued? ----------
def test_finishing_a_match_queues_one_notification(client, login, queued):
    headers = login("alice")
    match_id = create_match(client, headers)
    set_score(client, headers, match_id, 2, 1)
    assert queued == [match_id]


def test_editing_a_finished_match_does_not_queue_again(client, login, queued):
    headers = login("alice")
    match_id = create_match(client, headers)
    set_score(client, headers, match_id, 2, 1)
    set_score(client, headers, match_id, 3, 1)
    assert queued == [match_id]


def test_live_score_does_not_queue_a_notification(client, login, queued):
    headers = login("alice")
    match_id = create_match(client, headers)
    set_score(client, headers, match_id, 1, 0, status="live")
    assert queued == []


def test_broken_queue_does_not_break_the_api(client, login, monkeypatch):
    def broker_down(match_id):
        raise ConnectionError("broker is down")

    monkeypatch.setattr(tasks.send_match_finished_notification, "delay", broker_down)
    headers = login("alice")
    match_id = create_match(client, headers)
    assert set_score(client, headers, match_id, 2, 1).status_code == 200


# ---------- the job itself ----------
def test_job_sends_the_match_details(client, login, monkeypatch):
    sent = []
    monkeypatch.setattr(tasks, "deliver_notification", sent.append)
    headers = login("alice")
    match_id = create_match(client, headers, "Mumbai", "Pune")
    set_score(client, headers, match_id, 3, 2)  # finishing the match runs the job (eager mode)
    assert sent == [
        {
            "event": "match_finished",
            "match_id": match_id,
            "home_team": "Mumbai",
            "away_team": "Pune",
            "home_score": 3,
            "away_score": 2,
        }
    ]


def test_job_for_a_deleted_match_does_nothing(client, monkeypatch):
    sent = []
    monkeypatch.setattr(tasks, "deliver_notification", sent.append)
    result = tasks.send_match_finished_notification.apply(args=[999])
    assert result.result == "match not found"
    assert sent == []


def make_flaky_delivery(monkeypatch, failures):
    attempts = []

    def deliver(payload):
        attempts.append(payload)
        if len(attempts) <= failures:
            raise NotificationError("receiver is down")

    monkeypatch.setattr(tasks, "deliver_notification", deliver)
    return attempts


def test_job_retries_and_then_succeeds(client, login, monkeypatch):
    attempts = make_flaky_delivery(monkeypatch, failures=2)
    headers = login("alice")
    match_id = create_match(client, headers)
    result = tasks.send_match_finished_notification.apply(args=[match_id])
    assert result.state == "SUCCESS"
    assert len(attempts) == 3  # 2 failures + 1 success


def test_job_gives_up_after_max_retries(client, login, monkeypatch):
    attempts = make_flaky_delivery(monkeypatch, failures=100)
    headers = login("alice")
    match_id = create_match(client, headers)
    result = tasks.send_match_finished_notification.apply(args=[match_id])
    assert result.state == "FAILURE"
    assert len(attempts) == 4  # first try + 3 retries


def test_delivery_without_webhook_only_logs(monkeypatch):
    monkeypatch.setattr(settings, "webhook_url", None)
    tasks.deliver_notification({"event": "x"})  # must not raise


def test_delivery_failure_becomes_notification_error(monkeypatch):
    monkeypatch.setattr(settings, "webhook_url", "http://example.invalid/hook")

    def refuse(*args, **kwargs):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(tasks.urllib.request, "urlopen", refuse)
    with pytest.raises(NotificationError):
        tasks.deliver_notification({"event": "x"})


def test_delivery_posts_json_to_the_webhook(monkeypatch):
    monkeypatch.setattr(settings, "webhook_url", "http://example.invalid/hook")
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = request.data
        captured["method"] = request.get_method()
        return FakeResponse()

    monkeypatch.setattr(tasks.urllib.request, "urlopen", fake_urlopen)
    tasks.deliver_notification({"event": "match_finished"})
    assert captured["url"] == "http://example.invalid/hook"
    assert captured["method"] == "POST"
    assert b"match_finished" in captured["body"]


# ---------- WebSockets ----------
def test_websocket_sends_a_snapshot_first(client, login):
    match_id = create_match(client, login("alice"), "A", "B")
    with client.websocket_connect(f"/ws/matches/{match_id}") as ws:
        message = ws.receive_json()
    assert message["type"] == "snapshot"
    assert message["match"]["id"] == match_id
    assert message["match"]["status"] == "scheduled"


def test_websocket_receives_score_updates(client, login):
    headers = login("alice")
    match_id = create_match(client, headers)
    with client.websocket_connect(f"/ws/matches/{match_id}") as ws:
        ws.receive_json()  # snapshot
        set_score(client, headers, match_id, 1, 0, status="live")
        message = ws.receive_json()
    assert message["type"] == "score_update"
    assert (message["match"]["home_score"], message["match"]["status"]) == (1, "live")


def test_every_viewer_of_a_match_gets_the_update(client, login):
    headers = login("alice")
    match_id = create_match(client, headers)
    with client.websocket_connect(f"/ws/matches/{match_id}") as first:
        with client.websocket_connect(f"/ws/matches/{match_id}") as second:
            first.receive_json()
            second.receive_json()
            set_score(client, headers, match_id, 2, 2, status="live")
            assert first.receive_json()["match"]["home_score"] == 2
            assert second.receive_json()["match"]["home_score"] == 2


def test_viewers_only_get_their_own_match(client, login):
    headers = login("alice")
    first_id = create_match(client, headers, "A", "B")
    second_id = create_match(client, headers, "C", "D")
    with client.websocket_connect(f"/ws/matches/{second_id}") as ws:
        ws.receive_json()
        set_score(client, headers, first_id, 5, 0, status="live")  # a different match
        set_score(client, headers, second_id, 1, 1, status="live")
        message = ws.receive_json()
    assert message["match"]["id"] == second_id


def test_leaderboard_channel_announces_changes(client, login):
    headers = login("alice")
    match_id = create_match(client, headers)
    with client.websocket_connect("/ws/leaderboard") as ws:
        assert ws.receive_json() == {"type": "connected"}
        set_score(client, headers, match_id, 1, 0)
        assert ws.receive_json() == {"type": "leaderboard_changed"}


def test_deleting_a_match_is_announced(client, login):
    headers = login("alice")
    match_id = create_match(client, headers)
    with client.websocket_connect(f"/ws/matches/{match_id}") as ws:
        ws.receive_json()
        client.delete(f"/matches/{match_id}", headers=headers)
        assert ws.receive_json() == {"type": "match_deleted", "match_id": match_id}


def test_unknown_match_is_rejected(client):
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect("/ws/matches/999") as ws:
            ws.receive_json()
    assert error.value.code == 4404


def test_manager_forgets_closed_connections(client, login):
    match_id = create_match(client, login("alice"))
    with client.websocket_connect(f"/ws/matches/{match_id}") as ws:
        ws.receive_json()
        assert f"match:{match_id}" in manager._connections
    assert f"match:{match_id}" not in manager._connections


def test_manager_drops_a_dead_connection_while_broadcasting():
    class DeadSocket:
        async def send_json(self, message):
            raise RuntimeError("client vanished")

    local = ConnectionManager()
    local._connections["t"].add(DeadSocket())
    asyncio.run(local.broadcast("t", {"hello": 1}))
    assert "t" not in local._connections
