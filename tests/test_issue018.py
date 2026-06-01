from __future__ import annotations

import json
import sys
import types
from pathlib import Path

from clipper.cli import EXIT_FAILURE, EXIT_SUCCESS, main
from clipper.config import ClipperConfig
from clipper.scoring import score_video
from tests.test_issue006 import FakeClient, configure_default_llm, make_workspace
from tests.test_issue015 import make_sentence_transcript


def write_sentence_transcript(root: Path) -> None:
    (root / "work" / "sentences.json").write_text(json.dumps(make_sentence_transcript()), encoding="utf-8")


def write_visual_artifacts(root: Path) -> None:
    shots = {
        "schema_version": 1,
        "source_file": "source/source.mp4",
        "detection": {"threshold": 27.0},
        "shots": [
            {
                "id": "shot-0001",
                "start": 0.0,
                "end": 4.0,
                "duration": 4.0,
                "representative_frame_path": "work/frames/shot-0001.jpg",
                "representative_time": 2.0,
                "quality": {"sharpness": 1.0},
            }
        ],
    }
    visual = {
        "schema_version": 1,
        "source_file": "source/source.mp4",
        "shots_path": "work/shots.json",
        "provider": {"base_url": "https://vision.example/v1", "model": "vision"},
        "observations": [
            {
                "shot_id": "shot-0001",
                "start": 0.0,
                "end": 4.0,
                "representative_time": 2.0,
                "frame_path": "work/frames/shot-0001.jpg",
                "description": "A silent wide shot of a mountain sunrise.",
                "visible_people": [],
                "actions": ["sunrise"],
                "objects": ["mountain"],
                "mood": "calm",
                "setting": "outdoors",
                "visible_text": [],
            }
        ],
    }
    (root / "work" / "shots.json").write_text(json.dumps(shots), encoding="utf-8")
    (root / "work" / "visual-index.json").write_text(json.dumps(visual), encoding="utf-8")


def test_score_cli_requires_explicit_context(monkeypatch, tmp_path, capsys) -> None:
    configure_default_llm(monkeypatch)
    store, _ = make_workspace(tmp_path)

    assert main(["score", "video", "--store", str(store), "--directive", "Find moments", "--json"]) == EXIT_FAILURE

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "--with-transcript" in payload["error"]["message"]
    assert "--with-visuals" in payload["error"]["message"]


def test_transcript_only_scoring_requires_sentence_artifact(monkeypatch, tmp_path, capsys) -> None:
    configure_default_llm(monkeypatch)
    store, root = make_workspace(tmp_path)
    (root / "work" / "sentences.json").unlink()

    assert main(["score", "video", "--store", str(store), "--with-transcript", "--json"]) == EXIT_FAILURE

    payload = json.loads(capsys.readouterr().out)
    assert "requires sentence transcript artifact" in payload["error"]["message"]


def test_transcript_only_scoring_uses_sentences_and_enriches_dialogue(tmp_path) -> None:
    store, root = make_workspace(tmp_path)
    write_sentence_transcript(root)
    client = FakeClient(['[{"start":5,"end":11,"score":9,"reason":"laugh"}]'])

    _, _, scores, _ = score_video(
        store=store,
        video="video",
        directive="Find laughs",
        config=ClipperConfig(),
        client=client,
        with_transcript=True,
    )

    prompt = client.seen[0]["messages"][1]["content"]
    assert "Hosts laugh loudly." in prompt
    assert "raw faster whisper" not in prompt
    assert scores["segments"][0]["dialogue"] == "Hosts laugh loudly. A guest points at the chart."


def test_visual_only_scoring_uses_visual_index_without_transcript(tmp_path) -> None:
    store, root = make_workspace(tmp_path)
    (root / "work" / "transcript.json").unlink()
    write_visual_artifacts(root)
    client = FakeClient(['[{"start":0,"end":4,"score":8,"reason":"sunrise"}]'])

    _, _, scores, _ = score_video(
        store=store,
        video="video",
        directive="Find scenic shots",
        config=ClipperConfig(),
        client=client,
        with_visuals=True,
    )

    prompt = client.seen[0]["messages"][1]["content"]
    assert "A silent wide shot of a mountain sunrise." in prompt
    assert "shot-0001" in prompt
    assert scores["segments"] == [{"start": 0.0, "end": 4.0, "score": 8.0, "reason": "sunrise"}]


def test_combined_scoring_includes_transcript_and_visual_context(tmp_path) -> None:
    store, root = make_workspace(tmp_path)
    write_sentence_transcript(root)
    write_visual_artifacts(root)
    client = FakeClient(['[{"start":0,"end":9,"score":8,"reason":"multimodal"}]'])

    score_video(
        store=store,
        video="video",
        directive="Find moments",
        config=ClipperConfig(),
        client=client,
        with_transcript=True,
        with_visuals=True,
    )

    prompt = client.seen[0]["messages"][1]["content"]
    assert "Hosts laugh loudly." in prompt
    assert "A silent wide shot of a mountain sunrise." in prompt


def test_visual_scoring_requires_visual_artifacts(tmp_path) -> None:
    store, _ = make_workspace(tmp_path)
    try:
        score_video(store=store, video="video", directive="Find", config=ClipperConfig(), client=FakeClient([]), with_visuals=True)
    except ValueError as exc:
        assert "--with-visuals requires shot manifest artifact" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected missing visual artifact failure")


def test_score_cli_routes_context_flags(monkeypatch, tmp_path, capsys) -> None:
    configure_default_llm(monkeypatch)
    store, root = make_workspace(tmp_path)
    write_sentence_transcript(root)
    seen: list[dict[str, object]] = []

    class FakeOpenAI:
        def __init__(self, **_: object) -> None:
            self.chat = FakeClient(['[{"start":5,"end":11,"score":8,"reason":"hosts laugh"}]'], seen).chat

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))

    assert main(["score", "video", "--store", str(store), "--with-transcript", "--json"]) == EXIT_SUCCESS

    assert json.loads(capsys.readouterr().out)["result"]["segments"] == 1
    assert "Hosts laugh loudly." in seen[0]["messages"][1]["content"]
