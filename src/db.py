import os

import psycopg
from psycopg.rows import dict_row


def _connect():
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)


def ensure_contact(jid: str, display_name: str) -> None:
    with _connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO contacts (jid, display_name, last_seen)
               VALUES (%s, %s, NOW())
               ON CONFLICT (jid) DO UPDATE
               SET display_name = COALESCE(EXCLUDED.display_name, contacts.display_name),
                   last_seen = NOW()""",
            (jid, display_name or None),
        )


def insert_incoming_message(jid: str, content: str, wa_message_id: str | None) -> int | None:
    with _connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO messages (jid, role, content, wa_msg_id)
               VALUES (%s, 'user', %s, %s)
               ON CONFLICT (wa_msg_id) DO NOTHING
               RETURNING id""",
            (jid, content, wa_message_id),
        )
        row = cursor.fetchone()
        return row["id"] if row else None


def insert_outgoing_message(jid: str, content: str) -> None:
    with _connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO messages (jid, role, content) VALUES (%s, 'assistant', %s)",
            (jid, content),
        )


def get_recent_messages(jid: str, limit: int) -> list[dict[str, str]]:
    with _connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """SELECT role, content FROM (
                   SELECT role, content, created_at, id FROM messages
                   WHERE jid = %s ORDER BY created_at DESC, id DESC LIMIT %s
               ) recent ORDER BY created_at ASC, id ASC""",
            (jid, limit),
        )
        return list(cursor.fetchall())
