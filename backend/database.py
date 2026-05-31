from pathlib import Path
from typing import Iterator

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from backend.config import settings


engine: Engine = create_engine(
    settings.db_url,
    echo=False,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _enable_sqlite_fk(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


def init_db() -> None:
    """Apply schema.sql idempotently + run migrations. Creates DB if absent."""
    db_path = Path(settings.DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    schema_path = Path(settings.SCHEMA_PATH)
    if not schema_path.exists():
        raise FileNotFoundError(f"schema.sql not found at {schema_path}")

    sql = schema_path.read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys = ON")
        for stmt in _split_sql(sql):
            if stmt.strip():
                conn.exec_driver_sql(stmt)
        _run_migrations(conn)


def _run_migrations(conn) -> None:
    """ALTER TABLE idempotente — SQLite não suporta IF NOT EXISTS em ADD COLUMN."""
    migrations: list[tuple[str, str, str]] = [
        # (table, column, ALTER SQL)
        ("clientes", "plano_id", "ALTER TABLE clientes ADD COLUMN plano_id INTEGER"),
        ("clientes", "grupo_id", "ALTER TABLE clientes ADD COLUMN grupo_id INTEGER"),
    ]
    for table, column, ddl in migrations:
        existing = {
            row[1] for row in conn.exec_driver_sql(
                f"PRAGMA table_info({table})"
            ).fetchall()
        }
        if column not in existing:
            conn.exec_driver_sql(ddl)

    # índices pós-migration
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS idx_clientes_plano_id ON clientes(plano_id)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS idx_clientes_grupo_id ON clientes(grupo_id)"
    )


def _split_sql(sql: str) -> list[str]:
    """Split on `;` boundaries while ignoring `;` inside string literals."""
    out: list[str] = []
    buf: list[str] = []
    in_string = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if ch == "'":
            if in_string and i + 1 < len(sql) and sql[i + 1] == "'":
                buf.append("''")
                i += 2
                continue
            in_string = not in_string
            buf.append(ch)
        elif ch == ";" and not in_string:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    if buf:
        out.append("".join(buf))
    return out


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
