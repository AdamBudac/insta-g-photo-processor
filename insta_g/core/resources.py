"""Best-effort physical-memory checks without a fixed image-size limit.

Available RAM is a changing snapshot, and the caller supplies an estimate.
Passing this check does not reserve memory or guarantee a later allocation.
"""

from __future__ import annotations

import ctypes
import os

_WINDOWS = os.name == "nt"
_MIB = 1024 * 1024


class _MemoryStatusEx(ctypes.Structure):
    """Win32 MEMORYSTATUSEX with explicit Windows-width integer fields."""

    _fields_ = [
        ("dwLength", ctypes.c_uint32),
        ("dwMemoryLoad", ctypes.c_uint32),
        ("ullTotalPhys", ctypes.c_uint64),
        ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64),
        ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64),
        ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]


def _windows_available_memory() -> int | None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    memory_status = kernel32.GlobalMemoryStatusEx
    memory_status.argtypes = [ctypes.POINTER(_MemoryStatusEx)]
    memory_status.restype = ctypes.c_int
    status = _MemoryStatusEx(dwLength=ctypes.sizeof(_MemoryStatusEx))
    if not memory_status(ctypes.byref(status)):
        return None
    return int(status.ullAvailPhys)


def _posix_available_memory() -> int | None:
    # SC_AVPHYS_PAGES is not available on every POSIX host. Using total RAM
    # instead would overstate memory that is available to this operation.
    pages = os.sysconf("SC_AVPHYS_PAGES")
    page_size = os.sysconf("SC_PAGE_SIZE")
    if pages < 0 or page_size <= 0:
        return None
    return int(pages * page_size)


def available_memory() -> int | None:
    """Return currently available physical bytes, or None if not detectable."""
    try:
        return _windows_available_memory() if _WINDOWS else _posix_available_memory()
    except (AttributeError, OSError, TypeError, ValueError, OverflowError, ctypes.ArgumentError):
        return None


def ensure_memory(required_bytes: int, operation: str) -> None:
    """Reject an estimate exceeding 75% of currently available physical RAM.

    Detection failure introduces no substitute fixed cap. Real allocation
    failures must still be handled by the caller, even after a successful check.
    """
    if isinstance(required_bytes, bool) or not isinstance(required_bytes, int) or required_bytes < 0:
        raise ValueError("Odhad pamäte musí byť nezáporné celé číslo v bajtoch.")
    if not isinstance(operation, str) or not operation.strip():
        raise ValueError("Názov operácie musí byť neprázdny text.")
    available = available_memory()
    # Integer arithmetic avoids floating-point rounding at the threshold and
    # allows callers to validate estimates larger than the host address space.
    if available is None or required_bytes * 4 <= available * 3:
        return
    required_mib = (required_bytes + _MIB - 1) // _MIB
    available_mib = available // _MIB
    required_text = f"{required_mib:,}".replace(",", " ")
    available_text = f"{available_mib:,}".replace(",", " ")
    raise MemoryError(
        f"Operácia „{operation.strip()}“ vyžaduje približne {required_text} MiB pamäte, "
        f"dostupné je {available_text} MiB. Zatvorte iné aplikácie alebo spracujte menší obrázok."
    )
