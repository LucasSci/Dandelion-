## 2026-01-13 - SQLite Connection Overhead in Autocompletes
**Learning:** In `discord.py` bots using `aiosqlite`, creating a new connection for every autocomplete interaction is a major performance bottleneck (approx. 3x slower than shared pool).
**Action:** Always implement a shared `aiosqlite` connection pool (or single persistent connection) in `setup_hook` and reuse it across Cogs, especially for hot paths like `autocomplete`.
## 2024-05-22 - Single Connection Pattern for SQLite
**Learning:** Opening and closing SQLite connections (`aiosqlite.connect`) for every command or event (like autocomplete or loops) introduces significant File I/O overhead. This is a common anti-pattern in async Discord bots using SQLite.
**Action:** Initialize a single shared `aiosqlite.Connection` in the bot's startup (`setup_hook`) and reuse it across all cogs. Ensure it is closed properly on shutdown.
