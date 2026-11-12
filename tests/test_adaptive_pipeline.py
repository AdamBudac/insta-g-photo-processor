"""Native viewport warming and non-starving continuous interaction."""

from dataclasses import replace
from threading import Event

import pytest
from PIL import Image

from insta_g.core.geometry import get_geometry
from insta_g.gui.window import MainWindow
from insta_g.persistence import Session, SessionStore


@pytest.fixture
def window(qtbot, tmp_path):
    widget = MainWindow(SessionStore(tmp_path / "session.json"), Session())

    def close_safely(widget):
        widget.close()
        qtbot.waitUntil(lambda: not widget._jobs and widget._writer.is_idle, timeout=30000)
        widget.close()

    qtbot.addWidget(widget, before_close_func=close_safely)
    widget.show()
    path = tmp_path / "native.png"
    Image.new("RGB", (3200, 800), "#2468AB").save(path)
    widget.import_paths([str(path)])
    wait_idle(qtbot, widget)
    assert widget._detail_renderer._source is None
    widget.image_list.setCurrentRow(0)
    wait_idle(qtbot, widget)
    return widget


def wait_idle(qtbot, widget):
    qtbot.waitUntil(lambda: not widget._jobs and widget._writer.is_idle
                   and not widget._preview_timer.isActive()
                   and not widget.preview._detail_timer.isActive()
                   and widget._detail_pending is None, timeout=30000)


def test_opening_photo_warms_exactly_one_native_source_at_fit(window):
    assert window.preview.zoom_percent == 100
    assert window._detail_renderer._source.size == (3200, 800)
    assert max(window._sources[window._record().path].size) == 2048
    assert window.preview._detail is not None
    assert window.preview._detail_state == "native"
    assert window._record().status == "staging"


def test_continuous_changes_finish_active_native_frame_and_reuse_its_geometry(
    window, qtbot, monkeypatch,
):
    entered, release = Event(), Event()
    calls, accepted = [], []
    render = window._detail_renderer.render
    accept = window.preview.set_detail
    original_settings = replace(window._record().settings)
    original_geometry = get_geometry((3200, 800), original_settings)

    def controlled(path, size, settings, rect, target, cancelled):
        calls.append((settings, cancelled))
        if len(calls) == 1:
            entered.set()
            release.wait(10)
        return render(path, size, settings, rect, target, cancelled)

    def capture(image, rect, **kwargs):
        accepted.append(kwargs)
        return accept(image, rect, **kwargs)

    monkeypatch.setattr(window._detail_renderer, "render", controlled)
    monkeypatch.setattr(window.preview, "set_detail", capture)
    try:
        window._request_detail({"native_rect": (0, 0, 100, 100), "target_size": (100, 100)})
        qtbot.waitUntil(entered.is_set, timeout=10000)
        active = window._detail_job
        for offset in (-.9, -.3, .4, .8):
            window._settings_changed(replace(window._record().settings, offset_x=offset))
            window.preview._request_detail()
        assert window._detail_job is active
        assert not active.cancel.is_set()
        assert window._detail_pending is not None
    finally:
        release.set()
    wait_idle(qtbot, window)
    assert accepted[0]["geometry"] == original_geometry
    assert accepted[0]["settings"] == original_settings
    assert all(not cancelled.is_set() for _, cancelled in calls)
    assert window.preview._geometry == get_geometry((3200, 800), window._record().settings)
    assert window.preview._detail_state == "native"


def test_close_stops_delayed_native_work(window, qtbot):
    window.preview.set_zoom(300)
    assert window.preview._detail_timer.isActive()
    window.close()
    qtbot.wait(80)
    assert not window.preview._detail_timer.isActive()
    assert not window._jobs
    assert window._detail_renderer._source is None


def test_completed_status_cannot_claim_full_detail_for_a_newer_camera(window):
    window.preview.set_zoom(300)
    # The next request is throttled. A just-completed previous request still
    # has the current generation, but cannot satisfy the new pixel density.
    window._detail_status(window._detail_generation, window._record().path, "native", "")
    assert window.preview._detail_state == "loading"
