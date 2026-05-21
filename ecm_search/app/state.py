import sqlite3


class State:
    """Persists the sync checkpoint and cycle counter in SQLite."""

    def __init__(self, path):
        self._path = path
        conn = self._conn()
        conn.execute(
            "CREATE TABLE IF NOT EXISTS sync_state ("
            "id INTEGER PRIMARY KEY CHECK (id = 1), "
            "checkpoint TEXT, cycle_count INTEGER)"
        )
        conn.execute(
            "INSERT OR IGNORE INTO sync_state (id, checkpoint, cycle_count) "
            "VALUES (1, '1970-01-01 00:00:00', 0)"
        )
        conn.commit()
        conn.close()

    def _conn(self):
        return sqlite3.connect(self._path)

    def get_checkpoint(self):
        conn = self._conn()
        value = conn.execute(
            "SELECT checkpoint FROM sync_state WHERE id = 1"
        ).fetchone()[0]
        conn.close()
        return value

    def set_checkpoint(self, value):
        conn = self._conn()
        conn.execute("UPDATE sync_state SET checkpoint = ? WHERE id = 1", (value,))
        conn.commit()
        conn.close()

    def get_cycle(self):
        conn = self._conn()
        value = conn.execute(
            "SELECT cycle_count FROM sync_state WHERE id = 1"
        ).fetchone()[0]
        conn.close()
        return value

    def incr_cycle(self):
        conn = self._conn()
        conn.execute("UPDATE sync_state SET cycle_count = cycle_count + 1 WHERE id = 1")
        conn.commit()
        conn.close()
