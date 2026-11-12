"""Real filesystem tests for session round-trips and failure recovery."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import insta_g.persistence as persistence
from insta_g.core.models import ImageRecord, Settings
from insta_g.persistence import Session, SessionStore, StateError


def test_new_session_does_not_create_user_data(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "nested" / "session.json")
    assert store.load() == Session()
    assert not store.path.exists()


def test_round_trip_preserves_independent_settings_and_selection(tmp_path: Path) -> None:
    first = str(tmp_path / "panoráma.jpg")
    second = str(tmp_path / "portrét.heic")
    session = Session(
        [
            ImageRecord(first, Settings(splits=5, blur=0), checked=True, previewed=True),
            ImageRecord(second, Settings(mode="expand", ratio_mode="fixed", ratio=3 / 4,
                                         offset_x=0.5, blur=1000)),
        ],
        second, str(tmp_path / "výstup"),
    )
    session.records[1].exported_settings = session.records[1].settings.to_dict()
    store = SessionStore(tmp_path / "nested" / "session.json")
    store.save(session)
    loaded = store.load()
    assert loaded == session
    assert loaded.records[0].settings is not loaded.records[1].settings
    loaded.records[0].settings.blur = 84
    assert store.load().records[0].settings.blur == 0
    assert loaded.records[1].settings.blur == 1000
    assert loaded.records[0].checked and not loaded.records[0].is_exported
    assert loaded.records[0].previewed and loaded.records[0].status == "staging"
    assert not loaded.records[1].checked and loaded.records[1].is_exported
    assert not loaded.records[1].previewed and loaded.records[1].status == "exported"
    loaded.records[1].settings.offset_x = 0.25
    assert not loaded.records[1].is_exported
    assert store.load().records[1].is_exported
    assert json.loads(store.path.read_text(encoding="utf-8"))["schema_version"] == 6
    assert "portrét" in store.path.read_text(encoding="utf-8")


def test_no_selected_photo_is_preserved_with_imported_records(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "session.json")
    session = Session([ImageRecord("first.jpg"), ImageRecord("second.jpg")])
    store.save(session)
    restored = store.load()
    assert restored == session and restored.selected_path is None
    assert [record.status for record in restored.records] == ["imported", "imported"]


def test_failed_atomic_replace_keeps_previous_state_and_cleans_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = SessionStore(tmp_path / "session.json")
    store.save(Session())
    previous = store.path.read_bytes()

    def denied(*args: object) -> None:
        raise PermissionError("simulated locked session")

    monkeypatch.setattr(persistence.os, "replace", denied)
    with pytest.raises(StateError, match="locked session"):
        store.save(Session([ImageRecord("example.jpg")]))
    assert store.path.read_bytes() == previous
    assert list(tmp_path.glob("*.tmp")) == []


@pytest.mark.parametrize("contents", [
    "{invalid", "[]", '{"schema_version":true,"records":[]}',
    '{"schema_version":999,"records":[]}',
    '{"schema_version":1,"records":"bad"}',
    '{"schema_version":1,"records":[{"path":"image.jpg","settings":{"blur":true}}]}',
    '{"schema_version":1,"records":[],"export_dir":12}',
    '{"schema_version":1,"records":[],"selected_path":[]}',
    '{"schema_version":3,"records":[{"path":"image.jpg","checked":1}]}',
    '{"schema_version":3,"records":[{"path":"image.jpg","exported_settings":[]}]}',
    '{"schema_version":3,"records":[{"path":"image.jpg","exported_settings":{"blur":-1}}]}',
    '{"schema_version":4,"records":[{"path":"image.jpg","previewed":1}]}',
    '{"schema_version":4,"records":[{"path":"image.jpg","previewed":null}]}',
    "[" * 1500 + "0" + "]" * 1500,
])
def test_invalid_state_is_reported_and_preserved(tmp_path: Path, contents: str) -> None:
    path = tmp_path / "session.json"
    path.write_text(contents, encoding="utf-8")
    store = SessionStore(path)
    with pytest.raises(StateError):
        store.load()
    assert path.read_text(encoding="utf-8") == contents
    backup = store.preserve_invalid()
    assert backup.read_text(encoding="utf-8") == contents
    assert not path.exists()
    store.save(Session())
    assert store.load() == Session()
    assert backup.exists()


def test_duplicate_paths_are_rejected(tmp_path: Path) -> None:
    path = str(tmp_path / "image.jpg")
    data = {"schema_version": 1, "records": [ImageRecord(path).to_dict()] * 2}
    store = SessionStore(tmp_path / "session.json")
    store.path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(StateError, match="duplicitné"):
        store.load()


def test_deleted_source_still_has_restorable_settings(tmp_path: Path) -> None:
    path = str(tmp_path / "not-present.heic")
    store = SessionStore(tmp_path / "session.json")
    store.save(Session([ImageRecord(path, Settings(blur=99))], "other.jpg"))
    loaded = store.load()
    assert loaded.selected_path == path
    assert loaded.records[0].settings.blur == 99
    assert not Path(path).exists()


def test_save_and_load_use_the_same_record_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = SessionStore(tmp_path / "session.json")
    store.save(Session())
    before = store.path.read_bytes()
    monkeypatch.setattr(persistence, "MAX_RECORDS", 1)
    with pytest.raises(StateError):
        store.save(Session([ImageRecord("a.jpg"), ImageRecord("b.jpg")]))
    assert store.path.read_bytes() == before
    assert store.load() == Session()


def test_oversize_save_keeps_previous_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = SessionStore(tmp_path / "session.json")
    store.save(Session())
    before = store.path.read_bytes()
    monkeypatch.setattr(persistence, "MAX_STATE_BYTES", 1024)
    with pytest.raises(StateError, match="5 MB"):
        store.save(Session([ImageRecord("a" * 2000 + ".jpg")]))
    assert store.path.read_bytes() == before
    assert store.load() == Session()


def test_oversize_load_does_not_modify_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = SessionStore(tmp_path / "session.json")
    store.path.write_bytes(b" " * 100)
    monkeypatch.setattr(persistence, "MAX_STATE_BYTES", 10)
    with pytest.raises(StateError, match="5 MB"):
        store.load()
    assert store.path.stat().st_size == 100


@pytest.mark.parametrize("old_ratio,orientation,expected", [
    (4 / 3, "portrait", 3 / 4),
    (16 / 9, "landscape", 16 / 9),
    (3 / 2, "portrait", 3 / 4),
])
def test_legacy_session_migrates_without_losing_original_json(
    tmp_path: Path, old_ratio: float, orientation: str, expected: float,
) -> None:
    store = SessionStore(tmp_path / "session.json")
    payload = {
        "schema_version": 1,
        "records": [{"path": "old.jpg", "settings": {
            "mode": "split", "splits": 4, "ratio_mode": "fixed", "ratio": old_ratio,
            "orientation": orientation, "blur": 38, "export_width": 1080,
        }}],
        "selected_path": "old.jpg", "export_dir": "old-output",
    }
    original = json.dumps(payload).encode("utf-8")
    store.path.write_bytes(original)
    restored = store.load()
    assert restored.selected_path == "old.jpg"
    assert restored.records[0].settings.ratio == pytest.approx(expected)
    assert restored.records[0].settings.splits == 4
    assert restored.records[0].settings.fit_mode == "fit"
    assert store.path.read_bytes() == original
    store.save(restored)
    backups = list(tmp_path.glob("session.v1-backup-*.json"))
    assert len(backups) == 1 and backups[0].read_bytes() == original
    updated = json.loads(store.path.read_text(encoding="utf-8"))
    assert updated["schema_version"] == 6
    assert updated["records"][0]["checked"] is False
    assert updated["records"][0]["exported_settings"] is None
    assert updated["records"][0]["previewed"] is False
    assert "export_width" not in updated["records"][0]["settings"]
    assert "orientation" not in updated["records"][0]["settings"]
    store.save(restored)
    assert len(list(tmp_path.glob("session.v1-backup-*.json"))) == 1


@pytest.mark.parametrize("fit_mode", [None, "fit", "fill"])
def test_v2_session_migrates_without_changing_saved_placement_or_original_json(
    tmp_path: Path, fit_mode: str | None,
) -> None:
    settings = {"splits": 5, "ratio_mode": "fixed", "ratio": 1.0, "blur": 23}
    if fit_mode is not None:
        settings["fit_mode"] = fit_mode
    payload = {
        "schema_version": 2,
        "records": [{"path": "old.png", "settings": settings}],
        "selected_path": "old.png", "export_dir": "output",
    }
    original = json.dumps(payload).encode("utf-8")
    store = SessionStore(tmp_path / "session.json")
    store.path.write_bytes(original)
    restored = store.load()
    assert restored.records[0].settings.fit_mode == (fit_mode or "fit")
    assert not restored.records[0].checked and not restored.records[0].is_exported
    assert store.path.read_bytes() == original
    store.save(restored)
    backups = list(tmp_path.glob("session.v2-backup-*.json"))
    assert len(backups) == 1 and backups[0].read_bytes() == original
    updated = json.loads(store.path.read_text(encoding="utf-8"))
    assert updated["schema_version"] == 6
    assert updated["records"][0]["checked"] is False
    assert updated["records"][0]["exported_settings"] is None
    assert updated["records"][0]["previewed"] is False
    assert store.load() == restored
    store.save(restored)
    assert len(list(tmp_path.glob("session.v2-backup-*.json"))) == 1


@pytest.mark.parametrize("exported", [False, True])
def test_v3_session_defaults_preview_state_and_keeps_exact_backup(
    tmp_path: Path, exported: bool,
) -> None:
    record = ImageRecord("saved.png", checked=True)
    if exported:
        record.exported_settings = record.settings.to_dict()
    saved_record = record.to_dict()
    del saved_record["previewed"]
    original = json.dumps({
        "schema_version": 3, "records": [saved_record], "selected_path": None,
    }).encode("utf-8")
    store = SessionStore(tmp_path / "session.json")
    store.path.write_bytes(original)
    restored = store.load()
    assert restored.selected_path is None
    assert restored.records[0].previewed is False
    assert restored.records[0].checked is True
    assert restored.records[0].status == ("exported" if exported else "imported")
    assert store.path.read_bytes() == original
    store.save(restored)
    backups = list(tmp_path.glob("session.v3-backup-*.json"))
    assert len(backups) == 1 and backups[0].read_bytes() == original
    updated = json.loads(store.path.read_text(encoding="utf-8"))
    assert updated["schema_version"] == 6
    assert updated["records"][0]["previewed"] is False
    assert store.load() == restored
    store.save(restored)
    assert len(list(tmp_path.glob("session.v3-backup-*.json"))) == 1


def test_fit_and_offsets_survive_session_roundtrip(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "session.json")
    settings = Settings(fit_mode="fill", offset_x=-1.0, offset_y=0.64, ratio=3 / 4)
    store.save(Session([ImageRecord("panorama.png", settings)]))
    assert store.load().records[0].settings == settings


def test_v5_crop_migration_preserves_export_status_and_exact_original_backup(tmp_path: Path) -> None:
    settings = Settings(fit_mode="fill", offset_x=0.75, offset_y=-0.25)
    old_settings = settings.to_dict()
    del old_settings["crop_box"]
    original = json.dumps({
        "schema_version": 5,
        "records": [{
            "path": "pôvodná fotografia.heic", "settings": old_settings,
            "checked": True, "previewed": True, "exported_settings": old_settings,
            "last_error": None, "failure_stage": None,
        }],
        "selected_path": "pôvodná fotografia.heic", "export_dir": "výstup",
    }, ensure_ascii=False, indent=3).replace("\n", "\r\n").encode("utf-8")
    store = SessionStore(tmp_path / "session.json")
    store.path.write_bytes(original)
    restored = store.load()
    record = restored.records[0]
    assert record.settings.crop_box is None
    assert record.status == "exported" and record.checked and record.previewed
    assert record.settings == settings
    assert restored.selected_path == record.path
    assert store.path.read_bytes() == original
    store.save(restored)
    backups = list(tmp_path.glob("session.v5-backup-*.json"))
    assert len(backups) == 1 and backups[0].read_bytes() == original
    updated = json.loads(store.path.read_text(encoding="utf-8"))
    assert updated["schema_version"] == 6
    assert updated["records"][0]["settings"]["crop_box"] is None
    assert updated["records"][0]["exported_settings"]["crop_box"] is None
    assert store.load() == restored
    assert store.load().records[0].is_exported
    store.save(restored)
    assert len(list(tmp_path.glob("session.v5-backup-*.json"))) == 1


def test_crop_and_export_snapshot_roundtrip_independently_per_photo(tmp_path: Path) -> None:
    first = ImageRecord("first.png", Settings(crop_box=(100, 50, 900, 450)), previewed=True)
    first.exported_settings = first.settings.to_dict()
    second = ImageRecord("second.png", Settings(crop_box=(10, 20, 110, 220)), previewed=True)
    store = SessionStore(tmp_path / "session.json")
    original = Session([first, second], first.path)
    store.save(original)
    json_records = json.loads(store.path.read_text(encoding="utf-8"))["records"]
    assert json_records[0]["settings"]["crop_box"] == [100, 50, 900, 450]
    loaded = store.load()
    assert loaded == original
    assert loaded.records[0].status == "exported"
    assert loaded.records[1].status == "staging"
    loaded.records[0].settings.crop_box = (101, 50, 901, 450)
    assert loaded.records[0].status == "staging"
    assert loaded.records[1].settings.crop_box == (10, 20, 110, 220)
    assert store.load().records[0].settings.crop_box == (100, 50, 900, 450)


@pytest.mark.parametrize("field", ["settings", "exported_settings"])
@pytest.mark.parametrize("crop_box", [[0, 0, 0, 20], [True, 0, 10, 20], [-1, 0, 10, 20], [0, 0, 10.5, 20]])
def test_invalid_saved_crop_never_discards_or_overwrites_original_state(
    tmp_path: Path, field: str, crop_box: list[object],
) -> None:
    original = json.dumps({
        "schema_version": 6,
        "records": [{"path": "source.jpg", field: {"crop_box": crop_box}}],
    }).encode("utf-8")
    store = SessionStore(tmp_path / "session.json")
    store.path.write_bytes(original)
    with pytest.raises(StateError, match="[Vv]ýrez"):
        store.load()
    assert store.path.read_bytes() == original


def test_invalid_crop_save_keeps_previous_state(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "session.json")
    store.save(Session([ImageRecord("valid.jpg")]))
    original = store.path.read_bytes()
    invalid = ImageRecord("invalid.jpg", Settings(crop_box=(0, 0, 0, 10)))
    with pytest.raises(StateError, match="[Vv]ýrez"):
        store.save(Session([invalid]))
    assert store.path.read_bytes() == original
    assert not list(tmp_path.glob("*.tmp"))
