import pytest

from contribradar.tracker import Pipeline, SeenSet, TransitionError

URL = "https://github.com/octocat/llm-tools/issues/42"
URL2 = "https://github.com/octocat/llm-tools/issues/43"


def test_add_and_defaults():
    pipe = Pipeline()
    item = pipe.add(URL, title="Add RAG support", score=80, date="2026-11-09")
    assert item["state"] == "found"
    assert item["added"] == "2026-11-09"
    assert item["history"] == [{"state": "found", "date": "2026-11-09"}]


def test_add_is_idempotent():
    pipe = Pipeline()
    pipe.add(URL, date="2026-11-09")
    pipe.add(URL, title="changed?", date="2026-11-10")
    assert len(pipe.items) == 1
    assert pipe.items[URL]["added"] == "2026-11-09"


def test_happy_path_transitions():
    pipe = Pipeline()
    pipe.add(URL, date="2026-11-09")
    for state in ["claimed", "pr_opened", "changes_requested", "pr_opened", "merged"]:
        item = pipe.move(URL, state, date="2026-11-10")
    assert item["state"] == "merged"
    assert [h["state"] for h in item["history"]] == [
        "found", "claimed", "pr_opened", "changes_requested", "pr_opened", "merged",
    ]


def test_merged_is_terminal():
    pipe = Pipeline()
    pipe.add(URL, state="found")
    pipe.move(URL, "claimed")
    pipe.move(URL, "pr_opened")
    pipe.move(URL, "merged")
    with pytest.raises(TransitionError):
        pipe.move(URL, "claimed")


def test_backward_transition_rejected():
    pipe = Pipeline()
    pipe.add(URL)
    pipe.move(URL, "claimed")
    pipe.move(URL, "pr_opened")
    with pytest.raises(TransitionError):
        pipe.move(URL, "claimed")


def test_dropped_from_anywhere_and_revive():
    pipe = Pipeline()
    pipe.add(URL)
    pipe.move(URL, "claimed")
    pipe.move(URL, "dropped")
    assert pipe.items[URL]["state"] == "dropped"
    pipe.move(URL, "found")
    assert pipe.items[URL]["state"] == "found"


def test_move_unknown_url_and_unknown_state():
    pipe = Pipeline()
    with pytest.raises(TransitionError):
        pipe.move(URL, "claimed")
    pipe.add(URL)
    with pytest.raises(TransitionError):
        pipe.move(URL, "shipped")


def test_move_to_same_state_is_noop():
    pipe = Pipeline()
    pipe.add(URL, date="2026-11-09")
    item = pipe.move(URL, "found", date="2026-11-11")
    assert len(item["history"]) == 1


def test_save_load_roundtrip(tmp_path):
    pipe = Pipeline()
    pipe.add(URL, title="One", score=70, date="2026-11-09")
    pipe.add(URL2, title="Two", date="2026-11-09")
    pipe.move(URL, "claimed", date="2026-11-10")
    path = tmp_path / "pipeline.json"
    pipe.save(path)
    loaded = Pipeline.load(path)
    assert loaded.items[URL]["state"] == "claimed"
    assert loaded.counts()["claimed"] == 1
    assert loaded.counts()["found"] == 1
    assert [i["url"] for i in loaded.list(state="found")] == [URL2]


def test_load_missing_file_is_empty(tmp_path):
    assert Pipeline.load(tmp_path / "nope.json").items == {}


def test_seen_set_roundtrip_and_dedup(tmp_path):
    seen = SeenSet()
    assert URL not in seen
    seen.mark(URL, date="2026-11-09")
    seen.mark(URL, date="2026-12-01")  # first-seen date wins
    path = tmp_path / "seen.json"
    seen.save(path)
    loaded = SeenSet.load(path)
    assert URL in loaded
    assert loaded.urls[URL] == "2026-11-09"
