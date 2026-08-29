import sqlite3
from pathlib import Path


class Database:
    def __init__(self, path: str):
        self.path = path

    def _connect(self):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self):
        with self._connect() as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country TEXT NOT NULL,
                name TEXT NOT NULL,
                host TEXT NOT NULL UNIQUE,
                ssh_user TEXT NOT NULL,
                ssh_key TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                server_id INTEGER NOT NULL,
                client_uuid TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                vless_url TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(server_id) REFERENCES servers(id)
            );
            """)

    def add_server(self, country, name, host, ssh_user, ssh_key):
        with self._connect() as con:
            cur = con.execute(
                """INSERT INTO servers(country,name,host,ssh_user,ssh_key)
                   VALUES(?,?,?,?,?)""",
                (country, name, host, ssh_user, ssh_key)
            )
            return cur.lastrowid

    def get_active_servers(self):
        with self._connect() as con:
            rows = con.execute("""
                SELECT s.*, COUNT(u.id) AS users_count
                FROM servers s
                LEFT JOIN user_configs u
                  ON u.server_id = s.id AND u.active = 1
                WHERE s.active = 1
                GROUP BY s.id
                ORDER BY users_count ASC, s.id ASC
            """).fetchall()
            return [dict(x) for x in rows]

    def get_all_servers(self):
        with self._connect() as con:
            return [dict(x) for x in con.execute(
                "SELECT * FROM servers ORDER BY id DESC"
            ).fetchall()]

    def get_server(self, server_id):
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM servers WHERE id=?",
                (server_id,)
            ).fetchone()
            return dict(row) if row else None

    def create_user_config(
        self, telegram_id, server_id, client_uuid, email, vless_url
    ):
        with self._connect() as con:
            con.execute(
                """INSERT INTO user_configs
                   (telegram_id,server_id,client_uuid,email,vless_url)
                   VALUES(?,?,?,?,?)""",
                (telegram_id, server_id, client_uuid, email, vless_url)
            )

    def get_user_config(self, telegram_id):
        with self._connect() as con:
            row = con.execute("""
                SELECT u.*, s.name AS server_name
                FROM user_configs u
                JOIN servers s ON s.id = u.server_id
                WHERE u.telegram_id=? AND u.active=1
                ORDER BY u.id DESC LIMIT 1
            """, (telegram_id,)).fetchone()
            return dict(row) if row else None

    def get_user_configs(self):
        with self._connect() as con:
            return [dict(x) for x in con.execute("""
                SELECT u.*, s.name AS server_name
                FROM user_configs u
                JOIN servers s ON s.id = u.server_id
                ORDER BY u.id DESC
            """).fetchall()]
