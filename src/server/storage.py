"""Capa de almacenamiento con SQLite."""
import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import contextmanager

from .config import DB_PATH, DB_TIMEOUT
from ..common.crypto import hash_password, PBKDF2_ITERATIONS


logger = logging.getLogger(__name__)


class Storage:
    """Maneja la persistencia en SQLite."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    @contextmanager
    def _get_connection(self):
        """Context manager para conexiones SQLite."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=DB_TIMEOUT,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_database(self):
        """Crea las tablas si no existen."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    pw_hash BLOB NOT NULL,
                    pw_salt BLOB NOT NULL,
                    kdf_params_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    CONSTRAINT username_unique UNIQUE (username)
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    session_id TEXT UNIQUE NOT NULL,
                    created_at INTEGER NOT NULL,
                    last_seen INTEGER NOT NULL
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    from_account TEXT NOT NULL,
                    to_account TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    ts INTEGER NOT NULL,
                    raw_message_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    ts INTEGER NOT NULL,
                    created_at INTEGER NOT NULL,
                    CHECK(length(message_text) >= 1),
                    CHECK(length(message_text) <= 144)
                )
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_username_ts
                ON messages(username, ts DESC)
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    ip_address TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    ts INTEGER NOT NULL
                )
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_login_attempts_username_ts
                ON login_attempts(username, ts)
                """
            )

            logger.info(f"Base de datos inicializada en {self.db_path}")

    def _get_table_columns(self, conn: sqlite3.Connection, table: str) -> set[str]:
        """Obtiene las columnas existentes de una tabla SQLite."""
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        return {row["name"] for row in cursor.fetchall()}

    def create_user(self, username: str, password: str) -> bool:
        """Crea un nuevo usuario."""
        pw_hash, pw_salt = hash_password(password)
        kdf_params = {
            "algorithm": "PBKDF2-HMAC-SHA256",
            "iterations": PBKDF2_ITERATIONS,
            "salt_size": len(pw_salt),
        }

        with self._get_connection() as conn:
            cursor = conn.cursor()
            users_columns = self._get_table_columns(conn, "users")
            created_at = int(datetime.now().timestamp() * 1000)

            # Compatibilidad con esquemas legacy que todavia incluyen user_key/user_key_salt.
            if {"user_key", "user_key_salt"}.issubset(users_columns):
                cursor.execute(
                    """
                    INSERT INTO users (
                        username, pw_hash, pw_salt, kdf_params_json,
                        user_key, user_key_salt, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        username,
                        pw_hash,
                        pw_salt,
                        json.dumps(kdf_params),
                        b"",
                        b"",
                        created_at,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO users (
                        username, pw_hash, pw_salt, kdf_params_json, created_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        username,
                        pw_hash,
                        pw_salt,
                        json.dumps(kdf_params),
                        created_at,
                    ),
                )

        logger.info(f"Usuario '{username}' creado exitosamente")
        return True

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Obtiene informacion de un usuario o None si no existe."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, username, pw_hash, pw_salt, kdf_params_json, created_at
                FROM users
                WHERE username = ?
                """,
                (username,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            return {
                "id": row["id"],
                "username": row["username"],
                "pw_hash": row["pw_hash"],
                "pw_salt": row["pw_salt"],
                "kdf_params": json.loads(row["kdf_params_json"]),
                "created_at": row["created_at"],
            }

    def user_exists(self, username: str) -> bool:
        """Verifica si un usuario existe."""
        return self.get_user(username) is not None

    def create_session(self, username: str, session_id: str) -> bool:
        """Crea una nueva sesion."""
        now = int(datetime.now().timestamp() * 1000)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sessions (username, session_id, created_at, last_seen)
                VALUES (?, ?, ?, ?)
                """,
                (username, session_id, now, now),
            )

        logger.info(f"Sesion creada para usuario '{username}'")
        return True

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene informacion de una sesion."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, username, session_id, created_at, last_seen
                FROM sessions
                WHERE session_id = ?
                """,
                (session_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            return {
                "id": row["id"],
                "username": row["username"],
                "session_id": row["session_id"],
                "created_at": row["created_at"],
                "last_seen": row["last_seen"],
            }

    def update_session_last_seen(self, session_id: str) -> bool:
        """Actualiza el ultimo acceso de una sesion."""
        now = int(datetime.now().timestamp() * 1000)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE sessions
                SET last_seen = ?
                WHERE session_id = ?
                """,
                (now, session_id),
            )

        return cursor.rowcount > 0

    def delete_session(self, session_id: str) -> bool:
        """Elimina una sesion (logout)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

        return cursor.rowcount > 0

    def store_transaction(
        self,
        username: str,
        from_account: str,
        to_account: str,
        amount: str,
        ts: int,
        raw_message: str,
    ) -> int:
        """Almacena una transaccion y retorna su ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            tx_columns = self._get_table_columns(conn, "transactions")
            created_at = int(datetime.now().timestamp() * 1000)

            # Compatibilidad con esquemas legacy que todavia incluyen mac_trunc.
            if "mac_trunc" in tx_columns:
                cursor.execute(
                    """
                    INSERT INTO transactions (
                        username, from_account, to_account, amount, ts,
                        raw_message_json, mac_trunc, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        username,
                        from_account,
                        to_account,
                        amount,
                        ts,
                        raw_message,
                        "tls-only",
                        created_at,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO transactions (
                        username, from_account, to_account, amount, ts,
                        raw_message_json, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        username,
                        from_account,
                        to_account,
                        amount,
                        ts,
                        raw_message,
                        created_at,
                    ),
                )

            tx_id = cursor.lastrowid

        logger.info(f"Transaccion {tx_id} registrada para usuario '{username}'")
        return tx_id

    def get_user_transactions(self, username: str) -> List[Dict[str, Any]]:
        """Obtiene todas las transacciones de un usuario."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, username, from_account, to_account, amount, ts, created_at
                FROM transactions
                WHERE username = ?
                ORDER BY ts DESC
                """,
                (username,),
            )

            return [dict(row) for row in cursor.fetchall()]

    def store_message(self, username: str, text: str, ts: int) -> int:
        """Almacena un mensaje de texto y retorna su ID."""
        created_at = int(datetime.now().timestamp() * 1000)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO messages (username, message_text, ts, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (username, text, ts, created_at),
            )
            message_id = cursor.lastrowid

        logger.info(f"Mensaje {message_id} registrado para usuario '{username}'")
        return message_id

    def get_user_message_history(self, username: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtiene el historial de mensajes de un usuario en orden descendente."""
        safe_limit = max(1, min(int(limit), 500))
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, username, message_text, ts, created_at
                FROM messages
                WHERE username = ?
                ORDER BY ts DESC, id DESC
                LIMIT ?
                """,
                (username, safe_limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def count_user_messages(self, username: str) -> int:
        """Cuenta el total de mensajes de un usuario."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) as count
                FROM messages
                WHERE username = ?
                """,
                (username,),
            )
            row = cursor.fetchone()
            return int(row["count"]) if row else 0

    def record_login_attempt(self, username: str, ip_address: str, success: bool) -> None:
        """Registra un intento de login."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO login_attempts (username, ip_address, success, ts)
                VALUES (?, ?, ?, ?)
                """,
                (
                    username,
                    ip_address,
                    1 if success else 0,
                    int(datetime.now().timestamp() * 1000),
                ),
            )

    def get_failed_login_count(self, username: str, window_seconds: int) -> int:
        """Obtiene el numero de intentos fallidos en una ventana de tiempo."""
        cutoff_ts = int((datetime.now().timestamp() - window_seconds) * 1000)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) as count
                FROM login_attempts
                WHERE username = ? AND success = 0 AND ts > ?
                """,
                (username, cutoff_ts),
            )

            row = cursor.fetchone()
            return row["count"] if row else 0

    def cleanup_old_login_attempts(self, max_age_seconds: int = 3600):
        """Limpia intentos de login antiguos."""
        cutoff_ts = int((datetime.now().timestamp() - max_age_seconds) * 1000)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM login_attempts WHERE ts < ?", (cutoff_ts,))
            deleted = cursor.rowcount

        if deleted > 0:
            logger.debug(f"Limpiados {deleted} intentos de login antiguos")

    def clear_failed_login_attempts(self, username: str) -> None:
        """Elimina los intentos fallidos de un usuario tras login exitoso."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM login_attempts WHERE username = ? AND success = 0",
                (username,),
            )
            deleted = cursor.rowcount

        if deleted > 0:
            logger.debug(f"Limpiados {deleted} intentos fallidos de '{username}'")
