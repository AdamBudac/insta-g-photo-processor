"""A photo export is atomic as a series; other photos and old files survive."""

from pathlib import Path

from PIL import Image

from insta_g.core import export as export_module
from insta_g.core.export import export_records
from insta_g.core.models import ImageRecord, Settings


def record(path: Path, *, splits: int = 3) -> ImageRecord:
    Image.new("RGB", (splits * 32, 32), "#2468ab").save(path)
    return ImageRecord(str(path), Settings(splits=splits, ratio_mode="fixed", ratio=1))


def test_second_tile_failure_rolls_back_series_and_continues_with_later_photo(
    tmp_path, monkeypatch,
):
    failed = record(tmp_path / "partial.png")
    later = record(tmp_path / "complete.png", splits=1)
    directory = tmp_path / "out"
    directory.mkdir()
    existing = directory / "partial_01.jpg"
    existing.write_bytes(b"previous export must remain byte-for-byte unchanged")
    second_existing = directory / "partial_02.jpg"
    second_existing.write_bytes(b"unrelated existing second tile")
    original_save = export_module._save_jpeg_exclusive

    def fail_second(image, directory, stem, index, cancelled):
        if stem == "partial" and index == 2:
            raise OSError("injected second-tile failure")
        return original_save(image, directory, stem, index, cancelled)

    monkeypatch.setattr(export_module, "_save_jpeg_exclusive", fail_second)
    report = export_records([failed, later], directory)
    assert report.processed_count == 2
    assert set(report.failed) == {failed.path}
    assert "injected second-tile failure" in report.failed[failed.path]
    assert len(report.errors) == 1
    assert not report.cancelled
    assert report.completed == {later.path: later.settings.to_dict()}
    assert len(report.paths) == 1
    assert report.paths[0].name == "complete_01.jpg"
    with Image.open(report.paths[0]) as exported:
        assert exported.size == (32, 32)
        assert exported.mode == "RGB"
        exported.verify()
    assert existing.read_bytes() == b"previous export must remain byte-for-byte unchanged"
    assert second_existing.read_bytes() == b"unrelated existing second tile"
    assert set(directory.iterdir()) == {existing, second_existing, *report.paths}


def test_cancellation_mid_series_removes_every_new_tile_and_keeps_previous_photos(tmp_path):
    complete = record(tmp_path / "complete.png", splits=1)
    partial = record(tmp_path / "partial.png", splits=3)
    untouched = record(tmp_path / "untouched.png", splits=1)
    directory = tmp_path / "out"
    directory.mkdir()
    existing = directory / "partial_01.jpg"
    existing.write_bytes(b"previous file")
    stop = False

    def stop_mid_series(done, total, name):
        nonlocal stop
        assert total == 5
        if done == 3:
            stop = True

    report = export_records([complete, partial, untouched], directory,
                            progress=stop_mid_series, cancelled=lambda: stop)
    assert report.cancelled
    assert report.processed_count == 2
    assert not report.errors
    assert not report.failed
    assert report.completed == {complete.path: complete.settings.to_dict()}
    assert len(report.paths) == 1 and report.paths[0].name == "complete_01.jpg"
    assert existing.read_bytes() == b"previous file"
    assert set(directory.iterdir()) == {existing, *report.paths}


def test_failed_input_and_success_have_independent_report_entries(tmp_path):
    missing = ImageRecord(str(tmp_path / "missing.png"))
    successful = record(tmp_path / "success.png", splits=1)
    report = export_records([missing, successful], tmp_path / "out")
    assert report.processed_count == 2
    assert set(report.failed) == {missing.path}
    assert set(report.completed) == {successful.path}
    assert len(report.errors) == len(report.paths) == 1


def test_missing_preferred_output_is_not_recreated(tmp_path):
    source = record(tmp_path / "source.png")
    directory = tmp_path / "removed" / "export"
    report = export_records([source], directory, create_output=False)
    assert not directory.exists()
    assert not directory.parent.exists()
    assert report.errors
    assert report.processed_count == 0
    assert not report.paths
    assert not report.completed
    assert not report.failed


def test_cancellation_before_first_photo_reports_zero_processed(tmp_path):
    source = record(tmp_path / "source.png")
    directory = tmp_path / "out"
    report = export_records([source], directory, cancelled=lambda: True)
    assert report.cancelled
    assert report.processed_count == 0
    assert not report.paths and not report.completed and not report.failed
    assert not list(directory.iterdir())
