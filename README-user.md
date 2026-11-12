# User guide — Insta G Photo Processor

Prepare panoramas as adjoining carousel tiles, or add a background around a portrait. Processing takes place on your computer. The application does not need an account, upload your photos, or change the original files.

## Download and run on Windows

1. Open **Releases** in the project's GitHub repository and download **InstaGPhotoProcessor.exe** from the latest release's **Assets**. The **Source code** archives are for development; you do not need them to use the app.
2. Save the EXE in a folder of your choice and double-click it. No installer, Python installation or separate HEIC codec is required. Use a Windows x64 computer; Windows 11 x64 is the tested environment.
3. Close an older running version before opening a new one, because both use the same saved session. The first start of a one-file app can take a moment while it unpacks its bundled components into a temporary folder.

The app saves settings separately in Windows Documents. Moving or replacing the EXE does not remove those settings.

## First start and preferences

On first start, choose a **default export folder**, an **appearance** and an **interface language**. **OK** applies your choices; **Use defaults / Skip** completes setup with the defaults. English and the system appearance are the initial defaults. The default output folder is `Export` inside the application's data folder in your actual Windows Documents folder.

Open **Preferences** later to change these choices. Available languages are English, Slovak and Czech. Appearance can follow Windows or remain light or dark. The system option follows subsequent Windows appearance changes. **Cancel** leaves your previous preferences intact.

Export files go into the configured folder. If you delete or move that folder, choose an existing destination in Preferences; the application reports the problem and does not silently recreate a deleted custom folder.

## A quick first export

1. Click **Add photos**, or drag JPEG/JPG, PNG or HEIC/HEIF files into the library on the left. Adding a file does not automatically open it.
2. Click a photo to open its preview. Wait until the current preview has finished. The photo becomes yellow **Prepared**.
3. Optionally crop directly in the middle preview by dragging the photo's edge or corner handles. Choose **Carousel / Split** for several adjoining tiles, or **Expand canvas** for a single image with padding. Set the tile count and aspect ratio.
4. Adjust the photo's placement and background. Check the white output frame and the output dimensions in the right panel.
5. Use **Export all** for every prepared or exported photo, or check the required photos and use **Export selected**. Blue imported photos are always skipped.
6. Wait for the export summary. It reports original photos, output files and errors separately.

## Library colors and selection

| State | Meaning |
| --- | --- |
| Blue — Imported | Imported into the library but not yet successfully displayed in its current preview. Open it before exporting. |
| Yellow — Prepared | The selected photo's current preview has been displayed successfully. It is eligible for export. |
| Green — Exported | All output tiles were saved successfully using the photo's current settings. |
| Red — Failed | Import, preview or export failed. Read the reason in the tooltip or status bar, fix the cause, and retry. |

Clicking a row opens its preview. A checkbox marks the photo for batch actions independently of the active preview. Checking a photo does not prepare it, change its settings, or remove a valid green state.

Changing an exported photo's composition invalidates its green state. A failed or outdated preview cannot mark a photo prepared. Hover keeps each state's identifying color.

**Remove selected**, **Remove all**, **Remove exported** and the trash icon remove library entries only. They never delete your source photos or completed exports. **Retry failed** lets you try failed photos again after fixing the cause.

## Choose an input crop

Drag the handles on the photo's edges or corners in the middle preview. Move an edge inward to exclude that area, or outward to recover previously excluded pixels, up to the original photo's boundary. There is no separate dialog or need to enter pixel coordinates. Dragging inside the photo still adjusts its placement on the output canvas.

The camera remains steady while you drag and changes are saved automatically. **Escape** restores the crop from the start of the gesture. After releasing the handle, Fit view still shows the whole original photo and output canvas. Excluded areas remain visible under a dark overlay, so you can restore an edge to the original boundary in one drag. The crop can have any aspect ratio and remains inside the original, at least 1 × 1 px.

**Reset crop**, immediately below **Center image** in the right panel, restores the entire photo. Every actual crop change invalidates a previous green export state. The original file is never changed, so excluded areas can always be recovered.

The selected area becomes the input for split, padding, placement and backgrounds, with no resizing. A blurred background is also taken from this area. The dimmed original outside the crop is a preview reference. **Retained** always compares visible foreground area with the full original: an 800 × 400 px crop from a 1000 × 500 px photo retains **64%**, even with Fit / Padding. Additional Fill / Crop can reduce it further.

## Carousel / Split and Expand canvas

Carousel supports **2–20 tiles**, ordered from left to right. All tiles have equal dimensions and share one continuous composition. A newly added carousel starts in **Fill / Crop**. A restored photo keeps its saved settings.

**Automatic ratio** calculates the tile ratio from the selected input area's width, height and tile count, within the application's range **3:4 to 16:9**. With no input crop, it uses the whole original. Direct presets are **16:9, 3:2, 4:3, 5:4, 1:1, 4:5 and 3:4**. The ratio slider allows intermediate values. Moving it disables the automatic ratio. Ratios are width divided by height; there is no separate orientation switch.

**Fit / Padding** keeps the whole selected input area at its native pixel scale and adds a background where necessary. **Fill / Crop** can discard an additional part of that input. The dimmed image outside the white frame shows the area discarded by Fill. To recover areas excluded by the input crop, move its edge handles outward or use Reset crop.

**Expand canvas** creates one image and always uses Fit / Padding, preserving the whole selected input area. An incompatible ratio adds padding on the sides or at the top and bottom.

For example, a 6000 × 2000 px panorama split into three square tiles creates three 2000 × 2000 px files. The app does not resize the foreground to a fixed Instagram resolution.

## Position, zoom and composition

Use the **Horizontal** and **Vertical** sliders, or drag the photo using the **left mouse button** in the preview. Dragging adjusts the same placement used for export. **Center image** or a **left double-click** resets both position offsets, preserving the zoom. An axis with no extra padding or crop space cannot move further.

Drag with the **right mouse button** to move the viewport while zoomed in. The middle mouse button or Space + left drag works too; Escape ends the gesture. A **right double-click** restores **Fit view**: 100% zoom and a centered view of the whole original photo and canvas. Right drag and right double-click preserve the photo's placement, export state and saved settings.

**Preview zoom** ranges from **100% to 1000% relative to Fit view**. Returning to 100% automatically centers the whole original photo and canvas, with excluded areas dimmed. Zoom does not resize the export. During movement, cached pixels are drawn immediately. Available native foreground detail moves with the photo while the app updates the visible area in the background.

The small preview, up to 2048 pixels, appears first. The active original then loads in the background, even at 100% zoom, when enough memory is available. Its visible **native detail** adapts to the preview panel and your display's scaling, including high-resolution displays; it is not limited to 2048 pixels. Detail updates continue while dragging, zooming or changing placement and aspect ratio.

The caption distinguishes loading, native detail, and a reduced preview with a reason. Only one full original is kept for preview; memory use depends on the image, the visible area and available RAM. The first decode of a large source may take time. The small preview remains usable while it loads or if native detail cannot fit in memory. The preview always shows an SDR rendition, including when the original is HDR.

**Composition** offers **None, 2×2, 3×3, φ for the golden ratio, and X for diagonals**, in that order. All buttons and tooltips use the same font and style. These overlays are displayed only in the preview and never appear in exported files. Carousel tile boundaries are also preview annotations.

## Backgrounds and colors

Choose a **blurred photo**, **white**, **black**, or a **custom color** for padding. Use **Eyedropper** to click a color in the preview, or choose one of the five suggested dominant colors extracted from the photo. The custom color picker allows another color.

**Background blur** ranges from 0 to 1000 px in the original output scale. At 0 px the decorative photo background remains sharp. The background can be prepared at reduced resolution to keep memory use manageable; the original foreground remains at its native pixel scale.

## Dynamic range and output quality

For a detected HDR source, the **Dynamic range** setting selects original HDR or an SDR conversion. Supported sources include 10/12-bit PQ or HLG HEIC with supported BT.709, BT.2020 or Display P3 color signalling, supported Apple HEIC gain maps, ISO 21496 HEIC gain maps, and supported Ultra HDR or Apple HDR JPEG. Unknown or malformed HDR data produces a visible error instead of an incorrectly labeled HDR export.

The preview always displays an SDR rendition. For gain-map photos, it uses the camera-authored SDR base and converts its color profile to sRGB. PQ/HLG sources are tone mapped with highlight and gamut compression. This lets you compose the image on a standard display; it is not an HDR display preview.

An HDR export uses `_HDR` before the tile number. Converting an HDR source to SDR uses `_SDR`. Ordinary SDR sources retain the usual filename without either range suffix.

Standard SDR output is **JPEG**, quality **99**, with an sRGB color profile and no original EXIF or GPS metadata. Quality 99 is an encoder setting, not a percentage of retained data. PNG transparency is composited for output. Input orientation is respected.

Retaining HDR keeps the source's container family: HEIC produces **10-bit PQ BT.2020 HEIC**; supported HDR JPEG produces **JPEG with an ISO gain map and an SDR base**. The original HDR representation can therefore change while the HDR image and native foreground dimensions are retained. These outputs omit original EXIF and GPS metadata. A filename extension alone does not prove the presence of HDR data.

The bundled HDR JPEG codec supports at most **8192 px per side of each output tile**. This is a real encoder limit. More tiles can reduce an excessive tile width; an excessive height requires another crop or a smaller source. HDR HEIC processing and all large exports are also subject to available memory and codec constraints.

## Export behavior

Only **Prepared** and **Exported** photos are eligible. **Export selected** captures the checked eligible photos when it starts. **Export all** captures every eligible library photo, even if unchecked. The active preview does not determine the export scope. Later checkbox or settings changes affect the next export.

Each photo is treated as a unit: all its tiles must succeed. If export fails or is cancelled while processing a photo, incomplete outputs belonging to that photo are removed. Completed photos from earlier in the batch stay on disk. One photo's error does not prevent other photos from being processed.

The window remains usable during export. Use **Cancel export** to request cancellation; the current decoding or rendering operation may need to finish before cancellation takes effect. The summary distinguishes the number of successfully exported originals from the number of files written.

Existing files are not overwritten: the app chooses another available filename. Source photos are never overwritten. A green status means the whole photo was successfully exported with its current settings.

The application preserves foreground pixels at **1:1 scale**. Fit enlarges the canvas; Fill cuts a region from the photo. Rounding tile dimensions to whole pixels can add padding or slightly change the crop. The output dimensions shown in the settings panel are authoritative.

Very large images are checked against available memory. **SDR JPEG** supports at most **65,500 px per side** of one tile; **HDR JPEG** supports **8192 px per side** with the bundled codec. There is no fixed 80 MP limit. A small preview does not guarantee that an original can be exported within available RAM.

## Saved data and recovery

Your per-photo settings, including input crops, paths, checkboxes, preview readiness and export states are saved automatically in `session.json` under `<Windows Documents>/insta-g-photo-processor` for a new installation. Global appearance, language, onboarding and default export folder are stored separately in `preferences.json` in the same folder. Windows folder redirection is respected.

Upgrading from Insta G Image Resizer preserves your existing data: if the new folder has neither state file and the old `<Windows Documents>/insta-g-image-resizer` contains one, the application continues using the old folder without moving your files. Existing state in the new folder takes priority. Your configured export folder is preserved.

These files contain settings and paths, not copies of your photos. Every change is written in order outside the GUI thread; closing waits for pending writes. Moving a source file requires importing it from its new location. A save error is shown visibly; until saving succeeds, recent changes may exist only in memory.

Writes use a temporary file and atomic replacement. Invalid saved data is reported and preserved in a dated backup before new data can be saved. The application must not silently discard or overwrite an unreadable state.

## Help and keyboard shortcuts

Open **Help → User guide** for this scrollable guide in your selected language. **About** identifies the application. Common shortcuts are **Ctrl+O** to import, **Ctrl+E** to export all eligible photos, **Delete** to remove checked library entries, and **Alt+F4** to close the window.

The application prepares local files. It does not publish to Instagram. Instagram may resize or recompress uploaded files, and its supported ratios can change. The chosen ratio is never silently changed to match a service limit.
