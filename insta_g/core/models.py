"""Validated, GUI-independent settings and imported image records."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, fields
from typing import Any, Literal

MIN_INSTAGRAM_RATIO = 3 / 4
MAX_INSTAGRAM_RATIO = 16 / 9
MAX_SPLITS = 20
MAX_PREVIEW_EDGE = 2048


@dataclass
class Settings:
    mode: Literal["split", "expand"] = "split"
    splits: int = 3
    ratio_mode: Literal["auto", "fixed"] = "auto"
    ratio: float = 4 / 3
    blur: int = 40
    fit_mode: Literal["fit", "fill"] = "fill"
    offset_x: float = 0.0
    offset_y: float = 0.0
    grid: Literal["none", "thirds", "golden", "diagonal", "center"] = "none"
    background_mode: Literal["blur", "solid"] = "blur"
    background_color: str = "#FFFFFF"
    hdr_mode: Literal["hdr", "sdr"] = "sdr"
    crop_box: tuple[int, int, int, int] | None = None

    def validate(self) -> Settings:
        """Reject invalid state instead of silently changing user choices."""
        if self.mode not in ("split", "expand"):
            raise ValueError("Režim musí byť split alebo expand.")
        if self.ratio_mode not in ("auto", "fixed"):
            raise ValueError("Režim pomeru musí byť auto alebo fixed.")
        if self.fit_mode not in ("fit", "fill"):
            raise ValueError("Spôsob umiestnenia musí byť fit alebo fill.")
        if self.grid not in ("none", "thirds", "golden", "diagonal", "center"):
            raise ValueError("Unknown composition grid.")
        if self.background_mode not in ("blur", "solid"):
            raise ValueError("Unknown background mode.")
        if (not isinstance(self.background_color, str) or len(self.background_color) != 7
                or self.background_color[0] != "#"
                or any(c not in "0123456789abcdefABCDEF" for c in self.background_color[1:])):
            raise ValueError("Background colour must be #RRGGBB.")
        if self.hdr_mode not in ("hdr", "sdr"):
            raise ValueError("Unknown HDR export mode.")
        if self.crop_box is not None:
            if (
                not isinstance(self.crop_box, tuple) or len(self.crop_box) != 4
                or any(type(value) is not int for value in self.crop_box)
            ):
                raise ValueError("Výrez musí obsahovať štyri celé pixelové súradnice.")
            left, top, right, bottom = self.crop_box
            if left < 0 or top < 0 or right <= left or bottom <= top:
                raise ValueError("Výrez musí mať kladnú plochu a nezáporný začiatok.")
        for name, value, lower, upper in (
            ("Počet dielov", self.splits, 1, MAX_SPLITS),
            ("Rozostrenie", self.blur, 0, 1000),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} musí byť celé číslo.")
            if not lower <= value <= upper:
                raise ValueError(f"{name} musí byť od {lower} do {upper}.")
        if (
            isinstance(self.ratio, bool)
            or not isinstance(self.ratio, (int, float))
            or not MIN_INSTAGRAM_RATIO <= self.ratio <= MAX_INSTAGRAM_RATIO
            or not math.isfinite(self.ratio)
        ):
            raise ValueError("Pomer strán musí byť konečné číslo od 3:4 do 16:9.")
        for name, offset in (("Vodorovný posun", self.offset_x), ("Zvislý posun", self.offset_y)):
            if (
                isinstance(offset, bool) or not isinstance(offset, (int, float))
                or not -1 <= offset <= 1 or not math.isfinite(offset)
            ):
                raise ValueError(f"{name} musí byť konečné číslo od -1 do 1.")
        return self

    @property
    def count(self) -> int:
        return self.splits if self.mode == "split" else 1

    def source_bounds(self, original_size: tuple[int, int]) -> tuple[int, int, int, int]:
        """Return an explicit half-open crop in upright original pixels."""
        self.validate()
        if len(original_size) != 2 or any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in original_size
        ):
            raise ValueError("Obrázok musí mať kladné celočíselné rozmery.")
        width, height = original_size
        if self.crop_box is None:
            return (0, 0, width, height)
        if self.crop_box[2] > width or self.crop_box[3] > height:
            raise ValueError("Výrez presahuje rozmery pôvodnej fotografie.")
        return self.crop_box

    def cropped_size(self, original_size: tuple[int, int]) -> tuple[int, int]:
        """Dimensions of the unscaled input used by split and expand."""
        left, top, right, bottom = self.source_bounds(original_size)
        return right - left, bottom - top

    def effective_ratio(self, width: int, height: int) -> float:
        self.validate()
        if width <= 0 or height <= 0:
            raise ValueError("Rozmery zdrojového obrázka musia byť kladné.")
        if self.ratio_mode == "auto" and self.mode == "split":
            return max(
                MIN_INSTAGRAM_RATIO,
                min(MAX_INSTAGRAM_RATIO, width / (self.count * height)),
            )
        return self.ratio

    @property
    def effective_fit_mode(self) -> str:
        return self.fit_mode if self.mode == "split" else "fit"

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)

    def export_dict(self) -> dict[str, Any]:
        """Composition guides affect only the viewport, never output validity."""
        data = self.to_dict()
        data.pop("grid")
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Settings:
        if not isinstance(data, dict):
            raise ValueError("Nastavenia obrázka musia byť JSON objekt.")
        data = data.copy()
        if isinstance(data.get("crop_box"), list):
            data["crop_box"] = tuple(data["crop_box"])
        # Saved records predating Fill as the new-image default must preserve
        # their complete source image when no explicit choice was stored.
        data.setdefault("fit_mode", "fit")
        legacy_orientation = data.pop("orientation", None)
        data.pop("export_width", None)
        if legacy_orientation is not None:
            if legacy_orientation not in ("landscape", "portrait"):
                raise ValueError("Neplatná orientácia v staršom formáte nastavení.")
            old_ratio = data.get("ratio", 4 / 3)
            if (
                isinstance(old_ratio, bool) or not isinstance(old_ratio, (int, float))
                or not 1 <= old_ratio <= 16 / 9 or not math.isfinite(old_ratio)
            ):
                raise ValueError("Neplatný pomer v staršom formáte nastavení.")
            ratio = 1 / old_ratio if legacy_orientation == "portrait" else old_ratio
            data["ratio"] = max(MIN_INSTAGRAM_RATIO, min(MAX_INSTAGRAM_RATIO, ratio))
        unknown = set(data) - {item.name for item in fields(cls)}
        if unknown:
            raise ValueError(f"Neznáme nastavenia: {', '.join(sorted(map(str, unknown)))}.")
        return cls(**data).validate()


@dataclass
class ImageRecord:
    path: str
    settings: Settings = field(default_factory=Settings)
    checked: bool = False
    exported_settings: dict[str, Any] | None = None
    previewed: bool = False
    last_error: str | None = None
    failure_stage: Literal["import", "preview", "export"] | None = None

    @property
    def is_exported(self) -> bool:
        return (
            self.last_error is None and self.exported_settings is not None
            and Settings.from_dict(self.exported_settings).export_dict() == self.settings.export_dict()
        )

    @property
    def status(self) -> Literal["imported", "staging", "exported", "failed"]:
        if self.last_error is not None:
            return "failed"
        if self.is_exported:
            return "exported"
        return "staging" if self.previewed else "imported"

    def to_dict(self) -> dict[str, Any]:
        if not isinstance(self.path, str) or not self.path.strip():
            raise ValueError("Cesta obrázka musí byť neprázdny text.")
        if type(self.checked) is not bool:
            raise ValueError("Označenie obrázka musí byť logická hodnota.")
        if type(self.previewed) is not bool:
            raise ValueError("Stav náhľadu obrázka musí byť logická hodnota.")
        if self.last_error is not None and (
            not isinstance(self.last_error, str) or not self.last_error.strip()
        ):
            raise ValueError("Failure reason must be nonempty text.")
        if self.failure_stage not in (None, "import", "preview", "export"):
            raise ValueError("Unknown failed processing stage.")
        exported = (
            Settings.from_dict(self.exported_settings).to_dict()
            if self.exported_settings is not None else None
        )
        return {
            "path": self.path, "settings": self.settings.to_dict(),
            "checked": self.checked, "exported_settings": exported,
            "previewed": self.previewed,
            "last_error": self.last_error, "failure_stage": self.failure_stage,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImageRecord:
        if not isinstance(data, dict):
            raise ValueError("Záznam obrázka musí byť JSON objekt.")
        if set(data) - {"path", "settings", "checked", "exported_settings", "previewed", "last_error", "failure_stage"}:
            raise ValueError("Záznam obrázka obsahuje neznáme položky.")
        path = data.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ValueError("Cesta obrázka musí byť neprázdny text.")
        checked = data.get("checked", False)
        if type(checked) is not bool:
            raise ValueError("Označenie obrázka musí byť logická hodnota.")
        previewed = data.get("previewed", False)
        if type(previewed) is not bool:
            raise ValueError("Stav náhľadu obrázka musí byť logická hodnota.")
        exported = data.get("exported_settings")
        if exported is not None:
            exported = Settings.from_dict(exported).to_dict()
        record = cls(path, Settings.from_dict(data.get("settings", {})), checked, exported, previewed,
                     data.get("last_error"), data.get("failure_stage"))
        record.to_dict()
        return record
