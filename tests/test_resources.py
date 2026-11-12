"""Isolated resource estimates; no large allocations or environment changes."""

from __future__ import annotations

import ctypes
import os
from types import SimpleNamespace

import pytest

from insta_g.core import resources

MIB = 1024 * 1024


@pytest.mark.parametrize("required", [0, 1, 750 * MIB])
def test_sufficient_memory_and_exact_threshold_are_accepted(
    monkeypatch: pytest.MonkeyPatch, required: int,
) -> None:
    monkeypatch.setattr(resources, "available_memory", lambda: 1000 * MIB)
    resources.ensure_memory(required, "Načítanie obrázka")


def test_above_threshold_reports_required_and_available_mib(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(resources, "available_memory", lambda: 1000 * MIB)
    with pytest.raises(MemoryError) as caught:
        resources.ensure_memory(750 * MIB + 1, "Export panorámy")
    message = str(caught.value)
    assert "Export panorámy" in message
    assert "vyžaduje približne 751 MiB" in message
    assert "dostupné je 1 000 MiB" in message


def test_threshold_uses_exact_integer_arithmetic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(resources, "available_memory", lambda: 7)
    resources.ensure_memory(5, "Test")
    with pytest.raises(MemoryError):
        resources.ensure_memory(6, "Test")


def test_no_available_ram_allows_zero_but_rejects_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(resources, "available_memory", lambda: 0)
    resources.ensure_memory(0, "Test")
    with pytest.raises(MemoryError, match="dostupné je 0 MiB"):
        resources.ensure_memory(1, "Test")


def test_unknown_memory_does_not_introduce_a_fixed_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(resources, "available_memory", lambda: None)
    resources.ensure_memory(10**1000, "Veľký originál")


def test_large_image_estimate_is_allowed_when_ram_is_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(resources, "available_memory", lambda: 16 * 1024 * MIB)
    # A 240 MP source is above the previous 80 MP cap, but its practical
    # 12-byte/pixel estimate fits comfortably in this mocked available RAM.
    resources.ensure_memory(240_000_000 * 12, "Načítanie originálu")


@pytest.mark.parametrize("required", [-1, True, False, 1.0, None, "12"])
def test_invalid_estimate_is_rejected_without_memory_probe(
    monkeypatch: pytest.MonkeyPatch, required: object,
) -> None:
    def unexpected_probe() -> None:
        pytest.fail("Invalid input must be rejected before probing the host")

    monkeypatch.setattr(resources, "available_memory", unexpected_probe)
    with pytest.raises(ValueError, match="Odhad pamäte"):
        resources.ensure_memory(required, "Test")  # type: ignore[arg-type]


@pytest.mark.parametrize("operation", ["", " \t", None, 5])
def test_invalid_operation_is_rejected(operation: object) -> None:
    with pytest.raises(ValueError, match="Názov operácie"):
        resources.ensure_memory(1, operation)  # type: ignore[arg-type]


def test_windows_probe_reads_available_physical_not_total_ram(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, bool]] = []

    class FakeGlobalMemoryStatusEx:
        def __call__(self, pointer: object) -> int:
            state = ctypes.cast(pointer, ctypes.POINTER(resources._MemoryStatusEx)).contents
            assert state.dwLength == ctypes.sizeof(resources._MemoryStatusEx) == 64
            state.ullTotalPhys = 64 * 1024 * MIB
            state.ullAvailPhys = 1234 * MIB
            return 1

    function = FakeGlobalMemoryStatusEx()

    def load_windows_library(name: str, *, use_last_error: bool) -> SimpleNamespace:
        calls.append((name, use_last_error))
        return SimpleNamespace(GlobalMemoryStatusEx=function)

    monkeypatch.setattr(resources, "_WINDOWS", True)
    monkeypatch.setattr(resources.ctypes, "WinDLL", load_windows_library, raising=False)
    assert resources.available_memory() == 1234 * MIB
    assert calls == [("kernel32", True)]
    assert function.argtypes == [ctypes.POINTER(resources._MemoryStatusEx)]
    assert function.restype is ctypes.c_int


def test_failed_windows_api_returns_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailedStatus:
        def __call__(self, _pointer: object) -> int:
            return 0

    monkeypatch.setattr(resources, "_WINDOWS", True)
    monkeypatch.setattr(
        resources.ctypes, "WinDLL",
        lambda *_args, **_kwargs: SimpleNamespace(GlobalMemoryStatusEx=FailedStatus()),
        raising=False,
    )
    assert resources.available_memory() is None


def test_posix_probe_multiplies_available_pages_by_page_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def sysconf(name: str) -> int:
        calls.append(name)
        return {"SC_AVPHYS_PAGES": 123456, "SC_PAGE_SIZE": 4096}[name]

    monkeypatch.setattr(resources, "_WINDOWS", False)
    monkeypatch.setattr(resources.os, "sysconf", sysconf, raising=False)
    assert resources.available_memory() == 123456 * 4096
    assert calls == ["SC_AVPHYS_PAGES", "SC_PAGE_SIZE"]


@pytest.mark.parametrize(("pages", "page_size"), [(-1, 4096), (1, 0), (1, -1)])
def test_invalid_posix_counters_return_unknown(
    monkeypatch: pytest.MonkeyPatch, pages: int, page_size: int,
) -> None:
    monkeypatch.setattr(resources, "_WINDOWS", False)
    monkeypatch.setattr(
        resources.os, "sysconf",
        lambda name: {"SC_AVPHYS_PAGES": pages, "SC_PAGE_SIZE": page_size}[name],
        raising=False,
    )
    assert resources.available_memory() is None


@pytest.mark.parametrize("error", [OSError("API unavailable"), ValueError("unknown key"), AttributeError("no API")])
def test_unavailable_platform_probe_returns_unknown(
    monkeypatch: pytest.MonkeyPatch, error: Exception,
) -> None:
    def failed_probe() -> None:
        raise error

    monkeypatch.setattr(resources, "_WINDOWS", False)
    monkeypatch.setattr(resources, "_posix_available_memory", failed_probe)
    assert resources.available_memory() is None


def test_live_probe_is_read_only_and_returns_bytes_or_unknown() -> None:
    before = dict(os.environ)
    available = resources.available_memory()
    assert available is None or (isinstance(available, int) and available >= 0)
    assert dict(os.environ) == before
