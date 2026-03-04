# Cross-OS UI Check (PyQt5 Kiosk)

## Goal
Validate that fonts, icons, and simple animations render consistently across OS targets:
Linux, macOS, Windows, Android (if applicable), and ARM64 variants.

## Pre-checks (All OS)
- Ensure PyQt5 is installed and app launches.
- Verify the app loads without tracebacks.
- Confirm the `fonts/` directory is present and readable.

## Quick Visual Checks
1. Language page loads (buttons readable, no missing glyphs).
2. Menu page loads (cards visible, QR rendered or "QR unavailable" shown).
3. Route result page loads with:
   - Map area shows "Loading map" then map or "Map unavailable".
   - Loading animation (spinner) updates.
4. Food detail page loads (images either show or fallback text appears).

## Font Checks
- Korean, Japanese, Chinese (Simplified/Traditional), Cyrillic, Latin Extended.
- Look for tofu/missing glyph boxes.
- If missing, ensure fallback fonts exist for that OS.

## Animation Checks
- Map loading spinner updates ("| / - \").
- Map card background changes while loading.
- No UI freeze while loading map/weather.

## Performance & UX
- Switch between pages quickly; UI should stay responsive.
- If network is slow/unavailable, UI should not lock.

## Output Artifacts
Capture a screenshot per OS for comparison.
- Use `tools/qt_smoke_screenshot.py` to capture a baseline.

## Pass/Fail Criteria
- No UI freeze during map/weather fetch.
- No missing glyphs on key languages.
- Map loading text and spinner visible.
- Consistent layout across OS.

