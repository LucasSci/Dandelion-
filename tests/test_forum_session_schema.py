import sqlite3

from database.migrations import migrate_db


def test_forum_tables_created_by_migration():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()

    cur.execute("CREATE TABLE personagens (id INTEGER PRIMARY KEY AUTOINCREMENT)")
    migrate_db(cur)

    tables = {
        row[0]
        for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }

    assert "forum_sessions" in tables
    assert "forum_session_participants" in tables
    assert "forum_session_posts" in tables

    idx = {
        row[0]
        for row in cur.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
    }
    assert "idx_forum_sessions_guild_status" in idx
    assert "idx_forum_posts_status" in idx
    assert "idx_forum_posts_user" in idx
