def create_match(client, headers, home, away):
    response = client.post(
        "/matches", json={"home_team": home, "away_team": away}, headers=headers
    )
    assert response.status_code == 201
    return response.json()["id"]


def finish(client, headers, match_id, home_score, away_score):
    return client.patch(
        f"/matches/{match_id}/score",
        json={"home_score": home_score, "away_score": away_score, "status": "finished"},
        headers=headers,
    )


def test_create_match_requires_login(client):
    response = client.post("/matches", json={"home_team": "A", "away_team": "B"})
    assert response.status_code == 401


def test_match_teams_must_differ(client, login):
    response = client.post(
        "/matches", json={"home_team": "A", "away_team": "a"}, headers=login("alice")
    )
    assert response.status_code == 422


def test_new_match_defaults(client, login):
    match_id = create_match(client, login("alice"), "A", "B")
    match = client.get(f"/matches/{match_id}").json()
    assert (match["home_score"], match["away_score"], match["status"]) == (0, 0, "scheduled")


def test_only_creator_can_update_score(client, login):
    alice, bob = login("alice"), login("bob")
    match_id = create_match(client, alice, "A", "B")
    assert finish(client, bob, match_id, 1, 0).status_code == 403
    assert finish(client, alice, match_id, 1, 0).status_code == 200


def test_invalid_status_returns_422(client, login):
    headers = login("alice")
    match_id = create_match(client, headers, "A", "B")
    response = client.patch(
        f"/matches/{match_id}/score",
        json={"home_score": 1, "away_score": 0, "status": "cancelled"},
        headers=headers,
    )
    assert response.status_code == 422


def test_negative_score_returns_422(client, login):
    headers = login("alice")
    match_id = create_match(client, headers, "A", "B")
    assert finish(client, headers, match_id, -1, 0).status_code == 422


def test_filter_matches_by_status(client, login):
    headers = login("alice")
    first = create_match(client, headers, "A", "B")
    create_match(client, headers, "C", "D")
    finish(client, headers, first, 1, 0)
    page = client.get("/matches", params={"status": "finished"}).json()
    assert page["total"] == 1
    assert page["items"][0]["id"] == first


def test_unknown_match_returns_404(client):
    assert client.get("/matches/999").status_code == 404


def test_leaderboard_points_and_order(client, login):
    headers = login("alice")
    finish(client, headers, create_match(client, headers, "A", "B"), 2, 1)  # A wins
    finish(client, headers, create_match(client, headers, "A", "C"), 0, 0)  # draw
    finish(client, headers, create_match(client, headers, "B", "C"), 3, 1)  # B wins
    create_match(client, headers, "D", "A")  # scheduled: must be ignored

    table = client.get("/leaderboard").json()
    assert [row["team"] for row in table] == ["A", "B", "C"]
    a, b, c = table
    assert (a["played"], a["won"], a["drawn"], a["lost"], a["points"]) == (2, 1, 1, 0, 4)
    assert (b["points"], b["goal_difference"]) == (3, 1)
    assert (c["points"], c["goal_difference"]) == (1, -2)


def test_leaderboard_empty(client):
    assert client.get("/leaderboard").json() == []
