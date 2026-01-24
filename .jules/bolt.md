## 2024-05-23 - [Discord UI Button Layout Limit]
**Learning:** `discord.ui.Button` with a fixed `row=X` will crash if you try to add more than 5 buttons to that row. Discord has a hard limit of 5 components per row.
**Action:** Use `row=None` when dynamically adding a list of buttons (like skills or inventory) to allow Discord to auto-layout them across available rows (up to 5 rows, 25 components total).

## 2024-05-23 - [SQL Limit for UI Pagination]
**Learning:** Fetching all records (e.g., skills) when the UI can only display a subset (20) is wasteful.
**Action:** Always pair UI display limits with SQL `LIMIT` clauses to optimize IO and memory usage.
## 2024-05-22 - [Discord UI Row Limits]
**Learning:** assigning `row=1` to dynamic buttons (like skills) hard-limits the View to 5 items total on that row, causing a `ValueError` crash if more are added.
**Action:** Always use `row=None` (default) for dynamic lists of buttons to allow Discord to automatically wrap them across available rows (up to 25 items total).

## 2024-05-24 - [Parallelizing Independent DB Reads]
**Learning:** Sequential `await` calls for independent database queries (e.g., fetching stats, skills, inventory) add up latency unnecessarily. `asyncio.gather` can parallelize these even with a single SQLite connection (saving dispatch overhead).
**Action:** Identify independent `await repo.fetch...` calls in Views and group them with `asyncio.gather`.

## 2024-05-24 - [Optimizing Independent DB Queries]
**Learning:** In Discord UI views (`ui/sheet_view.py`), independent database queries for different sections (e.g. resources, skills, items) were being awaited sequentially. This increases the total response time.
**Action:** Refactored `atualizar_botoes_habilidade`, `mostrar_combate`, and `mostrar_inventario` to use `asyncio.gather` for fetching data in parallel. This reduces latency, improving the responsiveness of the interactive character sheet.
