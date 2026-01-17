# Palette's Journal - Critical Learnings

## 2026-01-17 - Discord Button Layout & Visual Hierarchy
**Learning:** Hardcoding `row` indices on Discord buttons (e.g., `row=1`) strictly limits that row to 5 items and causes crashes if exceeded. Auto-layout (`row=None`) is safer for dynamic lists.
**Action:** Use distinct ButtonStyles and emojis to differentiate interactive (rollable) vs informational elements to improve scannability. Always leave `row=None` for dynamic lists unless specific grid alignment is required.
