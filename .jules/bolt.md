## 2024-05-23 - [Discord UI Button Layout Limit]
**Learning:** `discord.ui.Button` with a fixed `row=X` will crash if you try to add more than 5 buttons to that row. Discord has a hard limit of 5 components per row.
**Action:** Use `row=None` when dynamically adding a list of buttons (like skills or inventory) to allow Discord to auto-layout them across available rows (up to 5 rows, 25 components total).

## 2024-05-23 - [SQL Limit for UI Pagination]
**Learning:** Fetching all records (e.g., skills) when the UI can only display a subset (20) is wasteful.
**Action:** Always pair UI display limits with SQL `LIMIT` clauses to optimize IO and memory usage.
## 2024-05-22 - [Discord UI Row Limits]
**Learning:** assigning `row=1` to dynamic buttons (like skills) hard-limits the View to 5 items total on that row, causing a `ValueError` crash if more are added.
**Action:** Always use `row=None` (default) for dynamic lists of buttons to allow Discord to automatically wrap them across available rows (up to 25 items total).
