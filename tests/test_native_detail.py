"""Native detail matches export geometry while remaining optional and bounded."""

import os
from dataclasses import replace
from threading import Event
from types import SimpleNamespace

import imagecodecs
import numpy as np
import pytest
from PIL import Image
from PySide6.QtGui import QImage

from insta_g.core import hdr, imaging
from insta_g.core.geometry import get_geometry
from insta_g.core.imaging import render_composite, render_region
from insta_g.core.models import ImageRecord, Settings
from insta_g.gui import workers
from insta_g.gui.window import MainWindow
from insta_g.gui.workers import DetailJob, DetailRenderer
from insta_g.persistence import Session, SessionStore


def pattern(width=300, height=40):
    return Image.frombytes("RGB", (width, height), bytes(
        channel for y in range(height) for x in range(width)
        for channel in ((x * 17) % 256, (y * 23) % 256, (x * 7 + y * 11) % 256)
    ))


@pytest.mark.parametrize("background", ["blur", "solid"])
@pytest.mark.parametrize("offset", [-1, -.35, .8, 1])
def test_fit_detail_matches_full_composite_crop_with_global_background(background, offset):
    settings = Settings(splits=3, ratio_mode="fixed", ratio=1, fit_mode="fit", blur=7,
                        offset_y=offset, background_mode=background, background_color="#123456")
    rect = (35, 7, 185, 77)
    with pattern() as source, render_composite(source, settings) as complete:
        with render_region(source, settings, rect, (150, 70)) as detail, complete.crop(rect) as crop:
            assert detail.size == crop.size
            assert detail.tobytes() == crop.tobytes()


@pytest.mark.parametrize("offset", [-1, -.47, 0, .63, 1])
def test_fill_detail_matches_native_crop_without_resampling(offset):
    settings = Settings(splits=3, ratio_mode="fixed", ratio=1, fit_mode="fill", offset_x=offset)
    rect = (7, 6, 100, 31)
    with pattern() as source, render_composite(source, settings) as complete:
        with render_region(source, settings, rect, (93, 25)) as detail, complete.crop(rect) as crop:
            assert detail.tobytes() == crop.tobytes()


def test_detail_uses_same_alpha_matte_as_full_composite():
    with Image.new("RGBA", (100, 50), (20, 60, 100, 128)) as source:
        settings = Settings(mode="expand", ratio_mode="fixed", ratio=1)
        with render_composite(source, settings) as complete:
            with render_region(source, settings, (10, 10, 90, 80), (80, 70)) as detail:
                with complete.crop((10, 10, 90, 80)) as crop:
                    assert detail.tobytes() == crop.tobytes()


@pytest.mark.parametrize("target", [(2 ** 31, 100), (100, 2 ** 31), (0, 100), (12.5, 100), (True, 100)])
def test_detail_target_rejects_invalid_or_unbounded_size(target):
    with pattern() as source, pytest.raises(ValueError):
        render_region(source, Settings(), (0, 0, 20, 20), target)


def test_physical_viewport_above_2048_is_rendered_at_requested_resolution():
    settings = Settings(mode="expand", ratio_mode="fixed", ratio=1.5)
    with Image.new("RGB", (3000, 2000), "#123456") as source:
        with render_region(source, settings, (0, 0, 3000, 2000), (3840, 2560)) as result:
            assert result.size == (3840, 2560)
            assert result.getpixel((3839, 2559)) == (18, 52, 86)


def test_reduced_region_requires_explicit_pyramid_permission():
    settings = Settings(mode="expand", ratio_mode="fixed", ratio=1)
    with Image.new("RGB", (50, 50), "red") as source:
        source.info["source_size"] = (200, 200)
        with pytest.raises(ValueError, match="originálne"):
            render_region(source, settings, (0, 0, 200, 200), (30, 30))
        with render_region(source, settings, (0, 0, 200, 200), (30, 30), allow_reduced=True) as result:
            assert result.size == (30, 30) and result.getpixel((15, 15)) == (255, 0, 0)


def test_detail_checks_memory_before_creating_target(monkeypatch):
    checks = []

    def stop_allocation(size, description):
        checks.append((size, description))
        raise MemoryError("low RAM")

    monkeypatch.setattr(imaging, "ensure_memory", stop_allocation)
    with pattern() as source, pytest.raises(MemoryError, match="low RAM"):
        render_region(source, Settings(), (0, 0, 20, 20), (800, 600))
    assert checks[0][0] == 800 * 600 * 12


def test_renderer_reads_native_source_pixels_beyond_thumbnail_resolution(tmp_path, monkeypatch):
    path = tmp_path / "native.png"
    settings = Settings(splits=3, ratio_mode="fixed", ratio=1, fit_mode="fill")
    with pattern(3000, 40) as source:
        source.save(path)
        left = get_geometry(source.size, settings).foreground_box[0]
        expected = source.crop((20 - left, 0, 30 - left, 40))
    monkeypatch.setattr(workers, "available_memory", lambda: 2 * 1024 ** 3)
    renderer = DetailRenderer()
    with renderer.render(str(path), (3000, 40), settings, (20, 0, 30, 40), (10, 40), Event()) as result:
        assert result.tobytes() == expected.tobytes()
    expected.close()
    renderer._source.close()


@pytest.mark.parametrize("stale_size", [False, True])
def test_ram_budget_fallback_never_decodes_native_pixels(tmp_path, monkeypatch, stale_size):
    path = tmp_path / "source.png"
    with pattern() as source:
        source.save(path)
    calls = []
    monkeypatch.setattr(workers, "available_memory", lambda: 10_000)

    def forbidden_decode(*args, **kwargs):
        calls.append(True)
        raise AssertionError("native decode must be skipped")

    monkeypatch.setattr(workers, "load_image", forbidden_decode)
    size = (1, 1) if stale_size else (300, 40)
    assert DetailRenderer().render(str(path), size, Settings(), (0, 0, 5, 5), (5, 5), Event()) is None
    assert not calls


def test_cache_contains_only_one_source_and_invalidates_file_modification(tmp_path, monkeypatch):
    paths = [tmp_path / name for name in ("a.png", "b.png")]
    for path in paths:
        Image.new("RGB", (90, 30), "#112233").save(path)
    real_load = workers.load_image
    loads = []

    def counted_load(path):
        loads.append(path)
        return real_load(path)

    monkeypatch.setattr(workers, "load_image", counted_load)
    monkeypatch.setattr(workers, "available_memory", lambda: 2 * 1024 ** 3)
    renderer = DetailRenderer()
    settings = Settings(splits=3, ratio_mode="fixed", ratio=1)

    def render(path):
        with renderer.render(str(path), (90, 30), settings, (0, 0, 20, 20), (20, 20), Event()) as result:
            return result.getpixel((5, 5))

    assert render(paths[0]) == (17, 34, 51)
    first = renderer._source
    render(paths[0])
    assert len(loads) == 1
    previous_stat = paths[0].stat()
    Image.new("RGB", (90, 30), "#334455").save(paths[0])
    os.utime(paths[0], ns=(previous_stat.st_atime_ns, previous_stat.st_mtime_ns + 1_000_000_000))
    assert render(paths[0]) == (51, 68, 85)
    assert len(loads) == 2
    with pytest.raises(ValueError):
        first.getpixel((0, 0))
    second = renderer._source
    render(paths[1])
    assert len(loads) == 3 and renderer._key[0] == str(paths[1])
    with pytest.raises(ValueError):
        second.getpixel((0, 0))
    renderer._source.close()


def test_pre_cancelled_renderer_does_not_even_stat_missing_source(tmp_path):
    cancelled = Event()
    cancelled.set()
    assert DetailRenderer().render(str(tmp_path / "missing.png"), (90, 30), Settings(),
                                   (0, 0, 20, 20), (20, 20), cancelled) is None


def test_cancelled_detail_job_closes_result_and_does_not_emit_it(qapp):
    produced = Image.new("RGB", (10, 10))

    class Renderer:
        def render(self, path, size, settings, rect, target, cancelled):
            cancelled.set()
            return produced

    job = DetailJob(Renderer(), 1, "generated.png", (10, 10), Settings(),
                    {"native_rect": (0, 0, 10, 10), "target_size": (10, 10)})
    results, finished = [], []
    job.signals.detail.connect(lambda *args: results.append(args))
    job.signals.finished.connect(finished.append)
    job.run()
    assert not results and finished == [job]
    with pytest.raises(ValueError):
        produced.getpixel((0, 0))


def test_cached_native_source_still_checks_viewport_memory_without_redecode(tmp_path, monkeypatch):
    path = tmp_path / "source.png"
    Image.new("RGB", (90, 30), "red").save(path)
    monkeypatch.setattr(workers, "available_memory", lambda: 2 * 1024 ** 3)
    renderer = DetailRenderer()
    settings = Settings(splits=3, ratio_mode="fixed", ratio=1)
    try:
        with renderer.render(str(path), (90, 30), settings, (0, 0, 10, 10), (10, 10), Event()):
            cached = renderer._source
        monkeypatch.setattr(workers, "available_memory", lambda: 1_000_000)
        monkeypatch.setattr(workers, "load_image", lambda *_args: pytest.fail("cached source decoded twice"))
        assert renderer.render(str(path), (90, 30), settings, (0, 0, 10, 10), (3840, 2160), Event()) is None
        assert renderer.last_reason and renderer._source is cached
        # The existing native raster is already resident; only new viewport
        # work is charged against current free RAM, not a second native decode.
        with renderer.render(str(path), (90, 30), settings, (0, 0, 10, 10), (10, 10), Event()) as result:
            assert result.size == (10, 10)
        assert not renderer.last_reason
    finally:
        renderer.close()


def test_invalid_viewport_is_rejected_before_native_decode(tmp_path, monkeypatch):
    monkeypatch.setattr(workers, "load_image", lambda *_args: pytest.fail("invalid target decoded source"))
    with pytest.raises(ValueError):
        DetailRenderer().render(str(tmp_path / "missing.png"), (90, 30), Settings(),
                                (0, 0, 10, 10), (True, 100), Event())


def test_native_pyramid_is_bounded_reused_and_sharp_zoom_uses_original(tmp_path, monkeypatch):
    path = tmp_path / "source.png"
    with pattern(3000, 1000) as original:
        original.save(path)
    monkeypatch.setattr(workers, "available_memory", lambda: 4 * 1024 ** 3)
    renderer = DetailRenderer()
    settings = Settings(mode="expand", ratio_mode="fixed", ratio=3 / 2)
    try:
        with renderer.render(str(path), (3000, 1000), settings, (0, 500, 3000, 1500), (300, 100), Event()):
            level = next(iter(renderer._levels.values()))
        assert renderer._source.size == (3000, 1000)
        assert level.info["source_size"] == (3000, 1000)
        with renderer.render(str(path), (3000, 1000), settings, (10, 500, 3010, 1500), (300, 100), Event()):
            assert level in renderer._levels.values()
        for target in ((600, 200), (1100, 367), (300, 100)):
            with renderer.render(str(path), (3000, 1000), settings, (0, 500, 3000, 1500), target, Event()):
                pass
            assert len(renderer._levels) <= 2
            assert sum(image.width * image.height * 4 for image in renderer._levels.values()) <= 3000 * 1000 * 4 // 3
        with renderer.render(str(path), (3000, 1000), settings, (20, 510, 30, 550), (10, 40), Event()) as result:
            with renderer._source.crop((20, 10, 30, 50)) as expected:
                assert result.tobytes() == expected.tobytes()
        cached_levels = list(renderer._levels.values())
    finally:
        renderer.close()
    assert not renderer._levels
    for image in cached_levels:
        with pytest.raises(ValueError):
            image.getpixel((0, 0))


@pytest.mark.parametrize("failure", ["preflight", "allocation"])
def test_optional_pyramid_memory_failure_uses_native_pixels(tmp_path, monkeypatch, failure):
    path = tmp_path / "source.png"
    Image.new("RGB", (600, 400), "#123456").save(path)
    renderer = DetailRenderer()
    settings = Settings(mode="expand", ratio_mode="fixed", ratio=1.5)
    try:
        with renderer.render(str(path), (600, 400), settings, (0, 0, 10, 10), (10, 10), Event()):
            pass
        native_resize = renderer._source.resize
        if failure == "allocation":
            def failed_resize(*args, **kwargs):
                raise MemoryError("optional pyramid allocation")

            monkeypatch.setattr(renderer._source, "resize", failed_resize)
        else:
            checked = renderer._within_budget

            def failed_preparation(required):
                if required > 60 * 40 * 16:
                    raise MemoryError("optional pyramid preflight")
                return checked(required)

            monkeypatch.setattr(renderer, "_within_budget", failed_preparation)
        # Spy on the producer boundary: a native viewport can be produced even
        # if Pillow cannot allocate an extra reusable level.
        sources = []
        original_render = workers.render_region

        def recorded_render(source, *args, **kwargs):
            sources.append(source)
            if failure == "allocation":
                monkeypatch.setattr(source, "resize", native_resize)
            return original_render(source, *args, **kwargs)

        monkeypatch.setattr(workers, "render_region", recorded_render)
        with renderer.render(str(path), (600, 400), settings, (0, 0, 600, 400), (60, 40), Event()) as result:
            assert result.getpixel((30, 20)) == (18, 52, 86)
        assert sources == [renderer._source]
        assert not renderer._levels and not renderer.last_reason
    finally:
        renderer.close()


def test_fit_render_never_allocates_expanded_native_canvas(tmp_path, monkeypatch):
    path = tmp_path / "tall.png"
    Image.new("RGB", (50, 2000), "#123456").save(path)
    renderer = DetailRenderer()
    settings = Settings(splits=20, ratio_mode="fixed", ratio=1, fit_mode="fit",
                        background_mode="solid", background_color="#654321")
    geometry = get_geometry((50, 2000), settings)
    assert geometry.canvas_size == (40000, 2000)
    real_new = Image.new
    allocations = []

    def recorded_new(mode, size, *args, **kwargs):
        allocations.append(size)
        assert size != geometry.canvas_size
        return real_new(mode, size, *args, **kwargs)

    monkeypatch.setattr(Image, "new", recorded_new)
    try:
        with renderer.render(str(path), (50, 2000), settings, (0, 0, 40000, 2000), (3840, 192), Event()) as result:
            assert result.size == (3840, 192)
        assert allocations
    finally:
        renderer.close()


@pytest.fixture
def window(qtbot, tmp_path):
    path = tmp_path / "source.png"
    with pattern() as source:
        source.save(path)
    settings = Settings(splits=3, ratio_mode="fixed", ratio=1)
    record = ImageRecord(str(path), settings, previewed=True, exported_settings=settings.to_dict())
    store = SessionStore(tmp_path / "session.json")
    widget = MainWindow(store, Session([record]))

    def close_safely(window):
        window.close()
        qtbot.waitUntil(lambda: not window._jobs and window._writer.is_idle, timeout=30000)
        window.close()

    qtbot.addWidget(widget, before_close_func=close_safely)
    qtbot.waitUntil(lambda: not widget._jobs and widget._writer.is_idle, timeout=30000)
    # Select without scheduling decode: these checks exercise only the result gate.
    blocked = widget.image_list.blockSignals(True)
    widget.image_list.setCurrentRow(0)
    widget.image_list.blockSignals(blocked)
    widget.settings.set_record(settings)
    widget._sizes[str(path)] = (300, 40)
    yield widget
    widget._preview_timer.stop()
    widget.preview._detail_timer.stop()


def test_window_rejects_cancelled_stale_other_photo_and_closing_detail(window, monkeypatch):
    applied = []
    monkeypatch.setattr(window.preview, "set_detail", lambda *args: applied.append(args))
    window._detail_generation = 5
    path = window._record().path
    image = QImage(10, 10, QImage.Format.Format_RGB32)
    rect = (0, 0, 10, 10)
    window._detail_ready(4, path, image, rect)
    window._detail_ready(5, "other.png", image, rect)
    assert not applied
    window._detail_job = SimpleNamespace(cancel=Event())
    window._cancel_detail()
    assert window._detail_job.cancel.is_set()
    window._detail_ready(5, path, image, rect)
    assert not applied
    window._detail_ready(6, path, image, rect)
    assert applied == [(image, rect)]
    window._closing = True
    window._detail_ready(6, path, image, rect)
    assert len(applied) == 1
    window._detail_job = None
    window._closing = False


def test_drag_persists_exact_offsets_and_grid_keeps_successful_export_snapshot(window, monkeypatch, qtbot):
    renders = []
    monkeypatch.setattr(window, "_queue_preview", lambda: renders.append(True))
    record = window._record()
    index = next(index for index, preset in enumerate(window.settings.GRID_PRESETS) if preset[0] == "thirds")
    window.settings.grid_buttons[index].click()
    assert record.settings.grid == "thirds"
    assert record.is_exported
    qtbot.waitUntil(lambda: window._writer.is_idle, timeout=10000)
    assert window.store.load().records[0].is_exported
    assert not renders
    window._mouse_offsets(.234567, -.345678)
    qtbot.waitUntil(lambda: window._writer.is_idle, timeout=10000)
    saved = window.store.load().records[0]
    assert saved.settings.offset_x == .234567
    assert saved.settings.offset_y == -.345678
    assert window.settings._settings == record.settings
    assert record.exported_settings is None and renders == [True]
    assert saved.settings.export_dict() == replace(record.settings, grid="golden").export_dict()


@pytest.mark.parametrize("size", [(8000, 6000), (10000, 8000)])
def test_native_sdr_detail_has_no_fixed_512_mib_or_pixel_ceiling(tmp_path, monkeypatch, size):
    path = tmp_path / "virtual-native.png"
    with pattern() as source:
        source.save(path)
    loads = []
    native = SimpleNamespace(size=size, close=lambda: None)
    monkeypatch.setattr(workers, "load_image", lambda path: loads.append(path) or native)
    monkeypatch.setattr(workers, "render_region", lambda *_args, **_kwargs: Image.new("RGB", (5, 5)))
    monkeypatch.setattr(workers, "available_memory", lambda: 8 * 1024 ** 3)
    renderer = DetailRenderer()
    try:
        with renderer.render(str(path), size, Settings(), (0, 0, 5, 5), (5, 5), Event()) as result:
            assert result.size == (5, 5)
        assert loads == [str(path)] and not renderer.last_reason
    finally:
        renderer.close()


def test_pq_tonemap_budget_uses_peak_112_bytes_per_pixel(tmp_path, monkeypatch):
    path = tmp_path / "virtual-pq.heic"
    with pattern() as source:
        source.save(path, format="PNG")
    monkeypatch.setattr(hdr, "detect_hdr", lambda _path: hdr.HdrInfo("heif_pq"))
    monkeypatch.setattr(workers, "available_memory", lambda: 3 * 1024 ** 3)
    monkeypatch.setattr(workers, "load_image", lambda *_args: pytest.fail("PQ decode exceeded its budget"))
    renderer = DetailRenderer()
    assert renderer.render(str(path), (4000, 3000), Settings(), (0, 0, 5, 5), (5, 5), Event()) is None
    assert renderer.last_reason


def test_real_12mp_hdr_gainmap_detail_uses_authored_sdr_base(tmp_path, monkeypatch):
    path = tmp_path / "twelve-megapixels.jpg"
    rgba = np.ones((3000, 4000, 4), dtype=np.float16)
    rgba[..., :3] = (3, 1.5, 0.5)
    path.write_bytes(imagecodecs.ultrahdr_encode(rgba, level=90, scale=8, gamut="BT_2100", transfer="LINEAR"))
    del rgba
    assert hdr.detect_hdr(path).kind == "ultrahdr"
    monkeypatch.setattr(workers, "available_memory", lambda: 2 * 1024 ** 3)
    monkeypatch.setattr(hdr, "load_hdr", lambda *_args, **_kwargs: pytest.fail("SDR detail reconstructed unnecessary HDR float data"))
    renderer = DetailRenderer()
    settings = Settings(mode="expand", ratio=4 / 3)
    try:
        with renderer.render(str(path), (4000, 3000), settings, (1500, 1000, 1600, 1100), (100, 100), Event()) as result:
            assert result.mode == "RGB" and result.size == (100, 100)
        assert renderer._source.size == (4000, 3000)
        assert not renderer.last_reason
    finally:
        renderer.close()


def test_low_memory_keeps_previous_native_cache_and_reports_reason(tmp_path, monkeypatch):
    paths = [tmp_path / name for name in ("first.png", "next.png")]
    for path in paths:
        Image.new("RGB", (300, 40), "red").save(path)
    monkeypatch.setattr(workers, "available_memory", lambda: 2 * 1024 ** 3)
    renderer = DetailRenderer()
    settings = Settings(splits=3, ratio_mode="fixed", ratio=1)
    with renderer.render(str(paths[0]), (300, 40), settings, (0, 0, 10, 10), (10, 10), Event()):
        cached = renderer._source
    monkeypatch.setattr(workers, "available_memory", lambda: 10_000)
    assert renderer.render(str(paths[1]), (300, 40), settings, (0, 0, 10, 10), (10, 10), Event()) is None
    assert renderer.last_reason and renderer._source is cached
    assert cached.getpixel((0, 0)) == (255, 0, 0)
    renderer.close()
    renderer.close()
    assert renderer._source is None and renderer._key is None
    with pytest.raises(ValueError):
        cached.getpixel((0, 0))


def test_cancelled_decode_is_cached_for_latest_request(tmp_path, monkeypatch):
    path = tmp_path / "cancelled.png"
    Image.new("RGB", (90, 30), "red").save(path)
    real_load = workers.load_image
    cancelled = Event()
    loads = []

    def loaded_before_cancellation(path):
        source = real_load(path)
        loads.append(path)
        cancelled.set()
        return source

    monkeypatch.setattr(workers, "load_image", loaded_before_cancellation)
    monkeypatch.setattr(workers, "available_memory", lambda: 2 * 1024 ** 3)
    renderer = DetailRenderer()
    settings = Settings(splits=3, ratio_mode="fixed", ratio=1)
    assert renderer.render(str(path), (90, 30), settings, (0, 0, 10, 10), (10, 10), cancelled) is None
    assert renderer._source is not None
    with renderer.render(str(path), (90, 30), settings, (0, 0, 10, 10), (10, 10), Event()) as result:
        assert result.size == (10, 10)
    assert loads == [str(path)]
    renderer.close()


def test_detail_job_reports_unavailable_reason_without_photo_failure(qapp, tmp_path):
    job = DetailJob(DetailRenderer(), 7, str(tmp_path / "missing.png"), (10, 10), Settings(),
                    {"native_rect": (0, 0, 10, 10), "target_size": (10, 10)})
    states, errors, finished = [], [], []
    job.signals.detail_status.connect(lambda *args: states.append(args))
    job.signals.error.connect(errors.append)
    job.signals.finished.connect(finished.append)
    job.run()
    assert [state[2] for state in states] == ["loading", "reduced"]
    assert states[-1][3] and job.renderer.last_reason == states[-1][3]
    assert not errors and finished == [job]
