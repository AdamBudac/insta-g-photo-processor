"""Library, native-resolution composition preview and per-photo controls."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from insta_g.core.geometry import get_geometry
from insta_g.core.models import Settings
from insta_g.gui.library import ImageList as ImageList
from insta_g.gui.preview import PreviewWidget as PreviewWidget
from insta_g.i18n import tr


class SettingsPanel(QWidget):
    settingsChanged = Signal(object)
    requestColorPick = Signal()
    MIN_RATIO = 3 / 4
    MAX_RATIO = 16 / 9
    PRESETS = [("16:9", 16 / 9), ("3:2", 3 / 2), ("4:3", 4 / 3),
               ("5:4", 5 / 4), ("1:1", 1.0), ("4:5", 4 / 5), ("3:4", 3 / 4)]
    GRID_PRESETS = (
        ("none", "None", "No composition grid"),
        ("center", "2×2", "2×2 grid (center cross)"),
        ("thirds", "3×3", "3×3 grid (rule of thirds)"),
        ("golden", "φ", "Golden ratio"),
        ("diagonal", "X", "Diagonals"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsPanel")
        self.setMinimumWidth(350)
        self._settings = Settings()
        self._loading = False
        self._hdr_available = False
        self._dominant_colors: list[str] = []
        self._source_size: tuple[int, int] | None = None
        self._translations: list[tuple[QWidget, str, str]] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 20)
        layout.setSpacing(12)
        heading = QLabel("Úprava fotografie")
        heading.setObjectName("panelHeading")
        layout.addWidget(heading)
        self.filename = QLabel("Vyberte fotografiu v knižnici")
        self.filename.setWordWrap(True)
        self.filename.setObjectName("selectedFilename")
        layout.addWidget(self.filename)
        self.controls = QWidget()
        controls = QVBoxLayout(self.controls)
        controls.setContentsMargins(0, 6, 0, 0)
        controls.setSpacing(13)
        controls.addWidget(QLabel("Režim"))
        mode_row = QHBoxLayout()
        mode_row.setSpacing(4)
        self.mode_buttons = QButtonGroup(self)
        self.split_button = QPushButton("Carousel / Split")
        self.split_button.setObjectName("splitModeButton")
        self.expand_button = QPushButton("Doplniť okraje")
        self.expand_button.setObjectName("expandModeButton")
        for index, button in enumerate((self.split_button, self.expand_button)):
            button.setCheckable(True)
            button.setMinimumWidth(0)
            self.mode_buttons.addButton(button, index)
            mode_row.addWidget(button, 1)
        self.split_button.setToolTip("Rozdelí fotografiu na nadväzujúce diely carouselu.")
        self.expand_button.setToolTip("Zachová celú fotografiu a doplní okraje do zvoleného pomeru.")
        controls.addLayout(mode_row)
        form = QFormLayout()
        form.setSpacing(10)
        self.splits = QSpinBox()
        self.splits.setObjectName("splitCount")
        self.splits.setRange(2, 20)
        form.addRow("Počet dielov", self.splits)
        controls.addLayout(form)
        self.auto = QCheckBox("Automatický pomer")
        self.auto.setObjectName("autoRatioCheck")
        self.auto.setToolTip("Pomer vychádza z celého originálu a počtu dielov, v rozsahu 3:4 až 16:9.")
        controls.addWidget(self.auto)
        ratio_header = QHBoxLayout()
        ratio_header.addWidget(QLabel("Pomer jedného dielu"))
        ratio_header.addStretch()
        self.ratio_label = QLabel()
        self.ratio_label.setObjectName("effectiveRatioLabel")
        ratio_header.addWidget(self.ratio_label)
        controls.addLayout(ratio_header)
        self.ratio_buttons: list[QPushButton] = []
        self.ratio_group = QButtonGroup(self)
        ratio_row = QHBoxLayout()
        ratio_row.setSpacing(3)
        for index, (text, _) in enumerate(self.PRESETS):
            button = QPushButton(text)
            button.setObjectName("ratio_" + text.replace(":", "_"))
            button.setProperty("compact", True)
            button.setMinimumWidth(0)
            button.setCheckable(True)
            self.ratio_group.addButton(button, index)
            self.ratio_buttons.append(button)
            ratio_row.addWidget(button, 1)
        controls.addLayout(ratio_row)
        self.ratio = QSlider(Qt.Orientation.Horizontal)
        self.ratio.setObjectName("ratioSlider")
        self.ratio.setRange(0, 1000)
        self.ratio.setToolTip("Plynulý pomer od 3:4 po 16:9. Posun vypne automatický pomer.")
        controls.addWidget(self.ratio)
        endpoints = QHBoxLayout()
        endpoints.addWidget(QLabel("3:4"))
        endpoints.addStretch()
        endpoints.addWidget(QLabel("16:9"))
        controls.addLayout(endpoints)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        controls.addWidget(line)
        controls.addWidget(QLabel("Umiestnenie originálu"))
        fit_row = QHBoxLayout()
        fit_row.setSpacing(4)
        self.fit_group = QButtonGroup(self)
        self.fit_button = QPushButton("Fit / Padding")
        self.fit_button.setObjectName("fitButton")
        self.fill_button = QPushButton("Fill / Crop")
        self.fill_button.setObjectName("fillButton")
        for index, button in enumerate((self.fit_button, self.fill_button)):
            button.setCheckable(True)
            self.fit_group.addButton(button, index)
            fit_row.addWidget(button, 1)
        self.fit_button.setToolTip("Zachová všetky pôvodné pixely; potrebnú plochu doplní pozadím.")
        self.fill_button.setToolTip("Vyplní plátno pôvodnými pixelmi a oreže časti mimo bieleho rámu.")
        controls.addLayout(fit_row)
        self.offset_x, self.offset_x_label = self._offset_control(controls, "Vodorovne", "offsetXSlider")
        self.offset_y, self.offset_y_label = self._offset_control(controls, "Zvislo", "offsetYSlider")
        self.center_button = QPushButton("Vycentrovať")
        self.center_button.setObjectName("centerImageButton")
        self.center_button.clicked.connect(self._center)
        controls.addWidget(self.center_button)
        self.reset_crop_button = QPushButton()
        self.reset_crop_button.setObjectName("resetCropButton")
        self._translate(self.reset_crop_button, "Reset crop")
        self._translate(self.reset_crop_button, "Restore the whole original photo.", "setToolTip")
        self.reset_crop_button.clicked.connect(lambda: self.set_crop(None))
        controls.addWidget(self.reset_crop_button)
        controls.addWidget(self._label("Background"))
        background_row = QHBoxLayout()
        background_row.setSpacing(3)
        self.background_buttons: list[QPushButton] = []
        self.background_group = QButtonGroup(self)
        for index, (text, name) in enumerate((
            ("Blur", "backgroundBlurButton"), ("White", "backgroundWhiteButton"),
            ("Black", "backgroundBlackButton"), ("Eyedropper", "backgroundEyedropperButton"),
            ("Custom", "backgroundCustomButton"),
        )):
            button = QPushButton()
            self._translate(button, text)
            button.setObjectName(name)
            button.setMinimumWidth(0)
            button.setProperty("compact", True)
            button.setStyleSheet("font-size: 11px; padding: 7px 3px;")
            button.setCheckable(index != 3)
            self.background_group.addButton(button, index)
            self.background_buttons.append(button)
            background_row.addWidget(button, 1)
        self.background_group.idClicked.connect(self._background_clicked)
        controls.addLayout(background_row)
        self.dominant_label = self._label("Dominant colors")
        controls.addWidget(self.dominant_label)
        dominant_row = QHBoxLayout()
        dominant_row.setSpacing(5)
        self.dominant_color_buttons: list[QPushButton] = []
        for index in range(5):
            button = QPushButton()
            button.setObjectName(f"dominantColor{index + 1}")
            button.setMinimumWidth(0)
            button.setFixedHeight(26)
            button.clicked.connect(lambda checked=False, i=index: self._dominant_clicked(i))
            self.dominant_color_buttons.append(button)
            dominant_row.addWidget(button, 1)
        controls.addLayout(dominant_row)
        self.set_dominant_colors([])
        controls.addWidget(QLabel("Rozostrenie doplneného pozadia"))
        blur_row = QHBoxLayout()
        self.blur = QSlider(Qt.Orientation.Horizontal)
        self.blur.setObjectName("blurSlider")
        self.blur.setRange(0, 1000)
        self.blur_value = QSpinBox()
        self.blur_value.setObjectName("blurSpin")
        self.blur_value.setRange(0, 1000)
        self.blur_value.setSuffix(" px")
        self.blur_value.setToolTip("Polomer rozostrenia v pôvodných pixeloch. 0 px ponechá pozadie ostré.")
        blur_row.addWidget(self.blur, 1)
        blur_row.addWidget(self.blur_value)
        controls.addLayout(blur_row)
        self.composition_label = self._label("Composition")
        self.composition_label.setObjectName("compositionHeading")
        controls.addWidget(self.composition_label)
        grid_row = QHBoxLayout()
        grid_row.setSpacing(3)
        self.grid_group = QButtonGroup(self)
        self.grid_buttons: list[QPushButton] = []
        for index, (mode, caption, description) in enumerate(self.GRID_PRESETS):
            button = QPushButton(caption)
            if index == 0:
                self._translate(button, "None")
            button.setObjectName(f"grid_{mode}")
            button.setMinimumWidth(0)
            button.setCheckable(True)
            self._translate(button, description, "setToolTip")
            self._translate(button, description, "setAccessibleName")
            self.grid_group.addButton(button, index)
            self.grid_buttons.append(button)
            grid_row.addWidget(button, 1)
        self.grid_group.idClicked.connect(self._grid_changed)
        controls.addLayout(grid_row)
        controls.addWidget(self._label("Dynamic range"))
        hdr_row = QHBoxLayout()
        self.hdr_group = QButtonGroup(self)
        self.hdr_button = QPushButton()
        self.hdr_button.setObjectName("originalHDRButton")
        self._translate(self.hdr_button, "Original HDR")
        self.sdr_button = QPushButton()
        self.sdr_button.setObjectName("sdrButton")
        self._translate(self.sdr_button, "SDR")
        for index, button in enumerate((self.hdr_button, self.sdr_button)):
            button.setCheckable(True)
            self.hdr_group.addButton(button, index)
            hdr_row.addWidget(button, 1)
        self.hdr_group.idClicked.connect(self._hdr_changed)
        controls.addLayout(hdr_row)
        self.hdr_note = QLabel()
        self.hdr_note.setWordWrap(True)
        self.hdr_note.setObjectName("hdrInfoLabel")
        controls.addWidget(self.hdr_note)
        self.retained_label = QLabel()
        self.retained_label.setObjectName("retainedPercentageLabel")
        controls.addWidget(self.retained_label)
        self.geometry_label = QLabel()
        self.geometry_label.setObjectName("geometryLabel")
        self.geometry_label.setWordWrap(True)
        controls.addWidget(self.geometry_label)
        self.warning = QLabel()
        self.warning.setObjectName("ratioWarning")
        self.warning.setWordWrap(True)
        self.warning.hide()
        controls.addWidget(self.warning)
        self.note = QLabel("JPEG · kvalita 99 % · sRGB\nPôvodné pixely bez prevzorkovania.\nKaždá zmena sa automaticky uloží.")
        self.note.setObjectName("secondaryText")
        self.note.setWordWrap(True)
        controls.addWidget(self.note)
        controls.addStretch()
        layout.addWidget(self.controls, 1)
        self.mode_buttons.idClicked.connect(self._mode_changed)
        self.splits.valueChanged.connect(self._changed)
        self.auto.toggled.connect(self._changed)
        self.ratio_group.idClicked.connect(self._preset_changed)
        self.fit_group.idClicked.connect(self._fit_changed)
        self.ratio.valueChanged.connect(self._ratio_changed)
        self.offset_x.valueChanged.connect(self._changed)
        self.offset_y.valueChanged.connect(self._changed)
        self.blur.valueChanged.connect(self.blur_value.setValue)
        self.blur_value.valueChanged.connect(self.blur.setValue)
        self.blur_value.valueChanged.connect(self._changed)
        legacy_text = {
            "Úprava fotografie": "Adjust photo", "Režim": "Mode",
            "Doplniť okraje": "Expand canvas", "Počet dielov": "Number of tiles",
            "Automatický pomer": "Automatic ratio", "Pomer jedného dielu": "Tile aspect ratio",
            "Umiestnenie originálu": "Original placement", "Vodorovne": "Horizontal",
            "Zvislo": "Vertical", "Vycentrovať": "Center image",
            "Rozostrenie doplneného pozadia": "Background blur",
            "Rozdelí fotografiu na nadväzujúce diely carouselu.":
                "Split the photo into adjoining carousel tiles.",
            "Zachová celú fotografiu a doplní okraje do zvoleného pomeru.":
                "Keep the entire photo and pad the canvas to the selected ratio.",
            "Pomer vychádza z celého originálu a počtu dielov, v rozsahu 3:4 až 16:9.":
                "Calculate the ratio from the entire source and tile count, between 3:4 and 16:9.",
            "Plynulý pomer od 3:4 po 16:9. Posun vypne automatický pomer.":
                "Aspect ratio from 3:4 to 16:9. Moving this slider turns off automatic ratio.",
            "Zachová všetky pôvodné pixely; potrebnú plochu doplní pozadím.":
                "Keep all original pixels and fill the extra canvas with the background.",
            "Vyplní plátno pôvodnými pixelmi a oreže časti mimo bieleho rámu.":
                "Fill the canvas with original pixels and crop outside the white frame.",
            "-100 %: ľavý/horný okraj · 0 %: stred · +100 %: pravý/dolný okraj":
                "-100%: left/top · 0%: center · +100%: right/bottom",
            "Polomer rozostrenia v pôvodných pixeloch. 0 px ponechá pozadie ostré.":
                "Blur radius in original pixels. 0 px keeps the background sharp.",
            "JPEG · kvalita 99 % · sRGB\nPôvodné pixely bez prevzorkovania.\nKaždá zmena sa automaticky uloží.":
                "JPEG · quality 99% · sRGB\nOriginal pixels without resampling.\nChanges are saved automatically.",
        }
        for widget in self.findChildren(QWidget):
            if widget is self.filename:
                continue
            for getter, setter in (("text", "setText"), ("toolTip", "setToolTip")):
                if hasattr(widget, getter) and hasattr(widget, setter):
                    current = getattr(widget, getter)()
                    if current in legacy_text:
                        self._translate(widget, legacy_text[current], setter)
        self.set_record(None)

    def _translate(self, widget: QWidget, source: str, method: str = "setText") -> None:
        self._translations.append((widget, source, method))
        getattr(widget, method)(tr(source))

    def _label(self, source: str) -> QLabel:
        label = QLabel()
        self._translate(label, source)
        return label

    def retranslate_ui(self) -> None:
        for widget, source, method in self._translations:
            getattr(widget, method)(tr(source))
        if not self.controls.isEnabled():
            self.filename.setText(tr("Select a photo in the library"))
        self.set_geometry(self._source_size)

    def set_dominant_colors(self, colors: list[str]) -> None:
        self._dominant_colors = list(dict.fromkeys(
            QColor(color).name().upper() for color in colors if QColor(color).isValid()
        ))[:5]
        for index, button in enumerate(self.dominant_color_buttons):
            available = index < len(self._dominant_colors)
            button.setEnabled(available)
            color = self._dominant_colors[index] if available else "#252B36"
            button.setStyleSheet(f"background-color: {color}; border: 1px solid #7b8495; "
                                "border-radius: 4px; padding: 0;")
            if available:
                value = QColor(color)
                button.setToolTip(f"{color} · RGB {value.red()}, {value.green()}, {value.blue()}")
                button.setAccessibleName(button.toolTip())
            else:
                button.setToolTip("")
                button.setAccessibleName("")

    def _dominant_clicked(self, index: int) -> None:
        if index < len(self._dominant_colors):
            self.set_picked_color(self._dominant_colors[index])

    def _background_clicked(self, index: int) -> None:
        if self._loading:
            return
        if index == 3:
            self.requestColorPick.emit()
            return
        if index == 4:
            color = QColorDialog.getColor(
                QColor(self._settings.background_color), self, tr("Custom background color"),
                QColorDialog.ColorDialogOption.DontUseNativeDialog,
            )
            if color.isValid():
                self.set_picked_color(color.name())
            else:
                self._update_availability()
            return
        if index == 0:
            self._settings = replace(self._settings, background_mode="blur")
            self._changed()
        else:
            self.set_picked_color("#FFFFFF" if index == 1 else "#000000")

    def set_picked_color(self, color: str) -> None:
        value = QColor(color)
        if not value.isValid() or self._loading:
            return
        self._settings = replace(self._settings, background_mode="solid",
                                 background_color=value.name().upper())
        self._changed()

    def _grid_changed(self, index: int) -> None:
        if not self._loading:
            self._settings = replace(self._settings, grid=self.GRID_PRESETS[index][0])
            self._changed()

    def set_hdr_info(self, info: dict | None) -> None:
        """Update capability display without changing the photo's saved choice.

        Empty metadata means decoding is pending, for example after restoring a
        session or evicting the source thumbnail. It does not establish SDR.
        Even an unavailable HDR decoder must not silently replace a deliberate
        Original HDR selection when another control subsequently emits settings.
        """
        info = info or {}
        known = "is_hdr" in info or "hdr" in info
        self._hdr_available = known and bool(info.get("is_hdr", info.get("hdr"))) and bool(
            info.get("supported", True)
        ) and not bool(info.get("error"))
        self.hdr_note.setText(str(info.get("description", "")))
        self._update_availability()

    def _hdr_changed(self, index: int) -> None:
        if not self._loading and (index == 1 or self._hdr_available):
            self._settings = replace(self._settings, hdr_mode="hdr" if index == 0 else "sdr")
            self._changed()

    def set_offsets(self, x: float, y: float) -> None:
        """Synchronize sliders after viewport dragging without losing precision."""
        self._loading = True
        self.offset_x.setValue(round(x * 100))
        self.offset_y.setValue(round(y * 100))
        self._settings = replace(self._settings, offset_x=x, offset_y=y)
        self._loading = False
        self._update_availability()

    def set_crop(self, crop_box: tuple[int, int, int, int] | None) -> None:
        """Commit a source crop through the usual per-photo update."""
        if self._loading or self._settings.crop_box == crop_box:
            return
        self._settings = replace(self._settings, crop_box=crop_box)
        self._changed()
        self.set_geometry(self._source_size)

    @staticmethod
    def _offset_control(layout: QVBoxLayout, text: str, name: str) -> tuple[QSlider, QLabel]:
        row = QHBoxLayout()
        row.addWidget(QLabel(text))
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setObjectName(name)
        slider.setRange(-100, 100)
        slider.setToolTip("-100 %: ľavý/horný okraj · 0 %: stred · +100 %: pravý/dolný okraj")
        value = QLabel("0 %")
        value.setMinimumWidth(42)
        row.addWidget(slider, 1)
        row.addWidget(value)
        layout.addLayout(row)
        return slider, value

    @classmethod
    def _slider_value(cls, ratio: float) -> int:
        return round((ratio - cls.MIN_RATIO) / (cls.MAX_RATIO - cls.MIN_RATIO) * 1000)

    def set_record(self, settings: Settings | None, filename: str = "") -> None:
        self._loading = True
        self.controls.setEnabled(settings is not None)
        self.filename.setText(filename or tr("Select a photo in the library"))
        self._settings = replace(settings) if settings is not None else Settings()
        value = self._settings
        self.split_button.setChecked(value.mode == "split")
        self.expand_button.setChecked(value.mode == "expand")
        self.splits.setValue(value.splits)
        self.auto.setChecked(value.ratio_mode == "auto" and value.mode == "split")
        self.ratio.setValue(self._slider_value(value.ratio))
        self.blur_value.setValue(value.blur)
        self.offset_x.setValue(round(value.offset_x * 100))
        self.offset_y.setValue(round(value.offset_y * 100))
        self._loading = False
        self._update_availability()

    def _select_preset(self, ratio: float | None) -> None:
        self.ratio_group.setExclusive(False)
        for button, (_, value) in zip(self.ratio_buttons, self.PRESETS):
            button.setChecked(ratio is not None and abs(ratio - value) < 0.00001)
        self.ratio_group.setExclusive(True)

    def _disable_auto(self) -> None:
        blocked = self.auto.blockSignals(True)
        self.auto.setChecked(False)
        self.auto.blockSignals(blocked)

    def _preset_changed(self, index: int) -> None:
        if self._loading:
            return
        value = self.PRESETS[index][1]
        self._disable_auto()
        self._settings = replace(self._settings, ratio=value)
        blocked = self.ratio.blockSignals(True)
        self.ratio.setValue(self._slider_value(value))
        self.ratio.blockSignals(blocked)
        self._changed()

    def _ratio_changed(self, value: int) -> None:
        if self._loading:
            return
        self._disable_auto()
        ratio = self.MIN_RATIO + (self.MAX_RATIO - self.MIN_RATIO) * value / 1000
        self._settings = replace(self._settings, ratio=ratio)
        self._changed()

    def _mode_changed(self, index: int) -> None:
        if self._loading:
            return
        mode = "split" if index == 0 else "expand"
        if mode == self._settings.mode:
            return
        self._settings = replace(
            self._settings, mode=mode, fit_mode="fill" if mode == "split" else "fit",
        )
        self._changed()

    def _fit_changed(self, index: int) -> None:
        if not self._loading:
            self._settings = replace(self._settings, fit_mode="fit" if index == 0 else "fill")
            self._changed()

    def _center(self) -> None:
        self._loading = True
        self.offset_x.setValue(0)
        self.offset_y.setValue(0)
        self._loading = False
        self._changed()

    def _changed(self, *_: object) -> None:
        if self._loading:
            return
        mode = self._settings.mode
        if mode == "expand":
            self._disable_auto()
        self._settings = replace(
            self._settings, mode=mode, splits=self.splits.value(),
            ratio_mode="auto" if self.auto.isChecked() else "fixed",
            blur=self.blur_value.value(),
            offset_x=(self._settings.offset_x
                      if round(self._settings.offset_x * 100) == self.offset_x.value()
                      else self.offset_x.value() / 100),
            offset_y=(self._settings.offset_y
                      if round(self._settings.offset_y * 100) == self.offset_y.value()
                      else self.offset_y.value() / 100),
        )
        self._update_availability()
        self.settingsChanged.emit(replace(self._settings))

    def _update_availability(self) -> None:
        self.reset_crop_button.setEnabled(self._settings.crop_box is not None)
        split = self._settings.mode == "split"
        self.splits.setEnabled(split)
        self.auto.setEnabled(split)
        self.fill_button.setEnabled(split)
        fill = self._settings.effective_fit_mode == "fill"
        self.fill_button.setChecked(fill)
        self.fit_button.setChecked(not fill)
        blur = self._settings.background_mode == "blur"
        self.blur.setEnabled(not fill and blur)
        self.blur_value.setEnabled(not fill and blur)
        color = self._settings.background_color.upper()
        background_index = (0 if blur else 1 if color == "#FFFFFF" else
                            2 if color == "#000000" else 4)
        self.background_buttons[background_index].setChecked(True)
        self.background_buttons[4].setToolTip(color)
        for button, (mode, _, _) in zip(self.grid_buttons, self.GRID_PRESETS):
            button.setChecked(mode == self._settings.grid)
        self.hdr_button.setEnabled(self._hdr_available)
        self.hdr_button.setChecked(self._settings.hdr_mode == "hdr")
        self.sdr_button.setChecked(self._settings.hdr_mode != "hdr")
        self._select_preset(None if self.auto.isChecked() else self._settings.ratio)
        self.ratio_label.setText(f"{self._settings.ratio:.3f}:1")
        self.offset_x_label.setText(f"{self.offset_x.value():+d} %")
        self.offset_y_label.setText(f"{self.offset_y.value():+d} %")

    def set_geometry(self, size: tuple[int, int] | None) -> None:
        self._source_size = size
        if size is None:
            self.geometry_label.clear()
            self.retained_label.clear()
            self.warning.hide()
            return
        box = self._settings.crop_box
        try:
            geometry = get_geometry(size, self._settings)
        except ValueError as error:
            self.geometry_label.setText(tr("Original {width} × {height} px", width=size[0],
                                           height=size[1]) + "\n" + tr("Unable to create output."))
            self.retained_label.clear()
            self.warning.setText(str(error))
            self.warning.show()
            return
        self.ratio_label.setText(f"{geometry.ratio:.3f}:1")
        if self.auto.isChecked():
            blocked = self.ratio.blockSignals(True)
            self.ratio.setValue(self._slider_value(geometry.ratio))
            self.ratio.blockSignals(blocked)
        self.geometry_label.setText(
            tr("Original {width} × {height} px", width=size[0], height=size[1]) + "\n" +
            ((tr("Crop {width} × {height} px", width=box[2] - box[0], height=box[3] - box[1])
              + "\n") if box else "") +
            tr("Output {count} × {width} × {height} px", count=geometry.count,
               width=geometry.tile_width, height=geometry.tile_height)
        )
        retained = geometry.retained_percentage
        percent = f"{retained:.1f}".rstrip("0").rstrip(".")
        self.retained_label.setText(tr("Retained: {percent}%", percent=percent))
        fill = self._settings.mode == "split" and self._settings.fit_mode == "fill"
        self.warning.setVisible(fill)
        self.warning.setText(tr("Fill crops outside the white frame. Cropped areas remain dimly visible."))
