"""Responsive geometry, cached backgrounds and bounded latest-only jobs."""

from dataclasses import replace
from threading import Event

import numpy as np
import pytest
from PIL import Image, ImageChops

from insta_g.core.geometry import get_geometry
from insta_g.core.imaging import _background_region, load_image, render_composite
from insta_g.core.models import Settings
from insta_g.gui import preview_renderer, workers
from insta_g.gui.preview_renderer import PreviewRenderer
from insta_g.gui.window import MainWindow
from insta_g.persistence import Session, SessionStore


@pytest.mark.parametrize("background_mode", ["blur", "solid"])
def test_cached_layers_match_shared_composite_for_all_offsets(background_mode, monkeypatch):
    source = Image.fromarray(np.random.default_rng(8).integers(0, 256, (160, 60, 3), dtype=np.uint8))
    source.info["source_size"] = (600, 1600)
    renderer = PreviewRenderer()
    calls = []
    prepare = preview_renderer._make_background

    def counted(*args):
        calls.append(True)
        return prepare(*args)

    monkeypatch.setattr(preview_renderer, "_make_background", counted)
    settings = Settings(mode="expand", ratio_mode="fixed", ratio=1,
                        background_mode=background_mode, background_color="#82A5C9")
    try:
        for offset in (-1, -.15, 0, .5, 1):
            current = replace(settings, offset_x=offset)
            result, background = renderer.render(source, current)
            expected = render_composite(source, current, max_edge=2048)
            try:
                assert ImageChops.difference(result, expected).getbbox() is None
                assert background.size == result.size
            finally:
                result.close()
                expected.close()
                background.close()
        assert len(calls) == 1
        for changed in (replace(settings, ratio=3 / 4), replace(settings, blur=95)):
            result, background = renderer.render(source, changed)
            result.close()
            background.close()
        assert len(calls) == 3
    finally:
        renderer.close()
        source.close()


def test_background_identity_and_solid_paths_do_not_run_affine_transform(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Identity/solid background must not run bicubic affine")

    geometry = get_geometry((60, 160), Settings(mode="expand", ratio=1, ratio_mode="fixed"))
    monkeypatch.setattr(Image.Image, "transform", forbidden)
    for background, size, left in (
        (Image.new("RGB", (1, 1), "#123456"), (2048, 2048), 30),
        (Image.new("RGB", (160, 160), "#123456"), (160, 160), 0),
    ):
        result = _background_region(background, geometry, size, native_left=left)
        assert result.size == size and result.getpixel((0, 0)) == (18, 52, 86)
        result.close()
        background.close()


def test_native_detail_reuses_background_when_panning_and_refreshes_changed_settings(tmp_path, monkeypatch):
    path = tmp_path / "portrait.png"
    Image.new("RGB", (50, 200), "#B07241").save(path)
    renderer = workers.DetailRenderer()
    settings = Settings(mode="expand", ratio_mode="fixed", ratio=1)
    prepare = workers._make_background
    calls = []

    def counted(*args):
        calls.append(True)
        return prepare(*args)

    monkeypatch.setattr(workers, "_make_background", counted)
    try:
        for left in (0, 10, 30):
            with renderer.render(str(path), (50, 200), settings, (left, 0, left + 80, 80), (80, 80), Event()):
                pass
        assert len(calls) == 1
        changed = replace(settings, blur=90)
        with renderer.render(str(path), (50, 200), changed, (0, 0, 80, 80), (80, 80), Event()):
            pass
        assert len(calls) == 2
    finally:
        renderer.close()


@pytest.fixture
def window(qtbot, tmp_path):
    widget = MainWindow(SessionStore(tmp_path / "session.json"), Session())

    def close_safely(window):
        window.close()
        qtbot.waitUntil(lambda: not window._jobs and window._writer.is_idle, timeout=30000)
        window.close()

    qtbot.addWidget(widget, before_close_func=close_safely)
    widget.resize(1100, 700)
    widget.show()
    return widget


def idle(qtbot, window):
    qtbot.waitUntil(lambda: not window._jobs and window._writer.is_idle
                    and not window._preview_timer.isActive()
                    and not window.preview._detail_timer.isActive()
                    and window._detail_pending is None, timeout=30000)


def prepare(qtbot, window, path):
    window.import_paths([str(path)])
    idle(qtbot, window)
    window.image_list.setCurrentRow(0)
    idle(qtbot, window)


def test_continuous_edits_update_geometry_immediately_and_queue_only_latest_job(window, qtbot, tmp_path, monkeypatch):
    path = tmp_path / "generated.png"
    Image.new("RGB", (1800, 500), "#526A7F").save(path)
    prepare(qtbot, window, path)
    entered, release = Event(), Event()
    calls = []
    original = window._preview_renderer.render

    def controlled(source, settings, **kwargs):
        calls.append(settings.blur)
        if len(calls) == 1:
            entered.set()
            release.wait(10)
        return original(source, settings, **kwargs)

    monkeypatch.setattr(window._preview_renderer, "render", controlled)
    try:
        window.settings.blur_value.setValue(41)
        qtbot.waitUntil(entered.is_set, timeout=10000)
        for value in range(42, 81):
            window._settings_changed(replace(window._record().settings, blur=value,
                                             ratio_mode="fixed", ratio=1,
                                             offset_x=(value - 60) / 40))
            assert window.preview._geometry == get_geometry((1800, 500), window._record().settings)
        window._render_preview()
        assert len([job for job in window._jobs if isinstance(job, workers.PreviewJob)]) == 1
        assert window._preview_pending
    finally:
        release.set()
    idle(qtbot, window)
    assert calls == [41, 80]
    assert not window.preview._pending_geometry
    assert window.store.load().records[0].settings.blur == 80


def test_zoom_restores_real_high_frequency_detail_instead_of_upscaled_thumbnail(window, qtbot, tmp_path, monkeypatch):
    window.resize(1800, 900)
    path = tmp_path / "native-pattern.png"
    stripes = np.broadcast_to((np.arange(4096) % 2 * 255).astype(np.uint8), (2048, 4096))
    with Image.fromarray(stripes).convert("RGB") as fixture:
        fixture.save(path)
    monkeypatch.setattr(workers, "available_memory", lambda: 4 * 1024 ** 3)
    prepare(qtbot, window, path)
    record = window._record()
    window._settings_changed(replace(record.settings, mode="expand", ratio_mode="fixed", ratio=16 / 9))
    idle(qtbot, window)
    assert max(window._sources[str(path)].size) == 2048
    window.preview.set_zoom(1000)
    idle(qtbot, window)
    assert window.preview._detail_state == "native"
    assert window.preview._mapping()[1] > 1
    assert window._detail_renderer._source.size == (4096, 2048)
    detail = window.preview._detail[0].toImage()
    values = [detail.pixelColor(x, detail.height() // 2).red() for x in range(detail.width())]
    assert np.std(values) > 40
    with load_image(path, max_edge=2048) as reduced:
        assert np.std(np.asarray(reduced)[reduced.height // 2, 20:-20, 0]) < 5
    window.preview.set_zoom(100)
    assert window.preview._pan.isNull()
    assert window.preview._detail is not None
    idle(qtbot, window)


def test_detail_worker_keeps_only_latest_pending_viewport(window, qtbot, tmp_path, monkeypatch):
    path = tmp_path / "generated.png"
    Image.new("RGB", (1800, 500), "#526A7F").save(path)
    prepare(qtbot, window, path)
    entered, release = Event(), Event()
    calls = []

    def controlled(path, size, settings, rect, target, cancelled):
        calls.append(rect)
        if len(calls) == 1:
            entered.set()
            release.wait(10)
        return Image.new("RGB", target, "#35715C")

    monkeypatch.setattr(window._detail_renderer, "render", controlled)
    try:
        window._request_detail({"native_rect": (0, 0, 100, 100), "target_size": (100, 100)})
        qtbot.waitUntil(entered.is_set, timeout=10000)
        first = window._detail_job
        for index in range(1, 60):
            window._request_detail({"native_rect": (index, 0, index + 100, 100), "target_size": (100, 100)})
        assert window._detail_job is first
        assert len([job for job in window._jobs if isinstance(job, workers.DetailJob)]) == 1
        assert window._detail_pending[-1]["native_rect"] == (59, 0, 159, 100)
    finally:
        release.set()
    idle(qtbot, window)
    assert calls == [(0, 0, 100, 100), (59, 0, 159, 100)]


@pytest.mark.parametrize("fail", [False, True])
def test_close_waits_for_save_and_preserves_a_visible_final_save_error(window, qtbot, tmp_path, monkeypatch, fail):
    path = tmp_path / "generated.png"
    Image.new("RGB", (600, 200), "#526A7F").save(path)
    prepare(qtbot, window, path)
    entered, release = Event(), Event()
    original = window.store.save

    def controlled(snapshot):
        entered.set()
        release.wait(10)
        if fail:
            raise OSError("generated final save failure")
        original(snapshot)

    monkeypatch.setattr(window.store, "save", controlled)
    try:
        window._settings_changed(replace(window._record().settings, blur=73))
        qtbot.waitUntil(entered.is_set, timeout=10000)
        window.close()
        assert window._closing and window.isVisible() and not window.isEnabled()
    finally:
        release.set()
    if fail:
        qtbot.waitUntil(lambda: window._writer.is_idle and not window._closing, timeout=10000)
        assert window.isVisible() and window.isEnabled()
        assert "generated final save failure" in window.notice.text()
        monkeypatch.setattr(window.store, "save", original)
        window._persist(changed=window._record())
        idle(qtbot, window)
        assert not window._last_save_error
    else:
        qtbot.waitUntil(lambda: not window.isVisible() and window._writer.is_idle, timeout=10000)
        assert window.store.load().records[0].settings.blur == 73
