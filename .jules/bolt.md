## 2026-01-13 - SQLite Connection Overhead in Autocompletes
**Learning:** In `discord.py` bots using `aiosqlite`, creating a new connection for every autocomplete interaction is a major performance bottleneck (approx. 3x slower than shared pool).
**Action:** Always implement a shared `aiosqlite` connection pool (or single persistent connection) in `setup_hook` and reuse it across Cogs, especially for hot paths like `autocomplete`.
