## 2024-05-22 - [Discord UI Row Limits]
**Learning:** assigning `row=1` to dynamic buttons (like skills) hard-limits the View to 5 items total on that row, causing a `ValueError` crash if more are added.
**Action:** Always use `row=None` (default) for dynamic lists of buttons to allow Discord to automatically wrap them across available rows (up to 25 items total).
