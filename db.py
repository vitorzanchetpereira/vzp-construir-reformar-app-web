"""
Camada de acesso ao banco — funciona em dois back-ends:
  • SQLite  (local, padrão)         — arquivo hub.db
  • Postgres (produção)             — quando a variável de ambiente DATABASE_URL
                                       começa com postgres:// ou postgresql://

O código da aplicação usa sempre placeholders com '?'; aqui traduzimos para '%s'
quando o back-end é Postgres.
"""
import os
from pathlib import Path

_DB_URL = os.environ.get("DATABASE_URL", "")
BACKEND = "postgres" if _DB_URL.startswith(("postgres://", "postgresql://")) else "sqlite"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "hub.db"

# ---------------------------------------------------------------- DDL por dialeto
_DDL_SQLITE = """
CREATE TABLE IF NOT EXISTS categorias (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome  TEXT NOT NULL UNIQUE,
    slug  TEXT NOT NULL UNIQUE,
    icone TEXT NOT NULL DEFAULT '🔧'
);
CREATE TABLE IF NOT EXISTS prestadores (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nome         TEXT NOT NULL,
    categoria_id INTEGER NOT NULL REFERENCES categorias(id),
    cidade       TEXT NOT NULL DEFAULT 'Sorriso/MT',
    telefone     TEXT, whatsapp TEXT, descricao TEXT,
    verificado   INTEGER NOT NULL DEFAULT 0,
    criado_em    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS avaliacoes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    prestador_id INTEGER NOT NULL REFERENCES prestadores(id) ON DELETE CASCADE,
    autor        TEXT NOT NULL,
    nota         INTEGER NOT NULL CHECK (nota BETWEEN 1 AND 5),
    comentario   TEXT,
    status       TEXT NOT NULL DEFAULT 'pendente',
    criado_em    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS usuarios (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    email        TEXT NOT NULL UNIQUE,
    senha_hash   TEXT NOT NULL,
    papel        TEXT NOT NULL DEFAULT 'prestador',
    prestador_id INTEGER REFERENCES prestadores(id) ON DELETE CASCADE,
    criado_em    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_prestadores_categoria ON prestadores(categoria_id);
CREATE INDEX IF NOT EXISTS idx_avaliacoes_prestador ON avaliacoes(prestador_id);
CREATE INDEX IF NOT EXISTS idx_avaliacoes_status ON avaliacoes(status);
CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);
"""

_DDL_POSTGRES = """
CREATE TABLE IF NOT EXISTS categorias (
    id    SERIAL PRIMARY KEY,
    nome  TEXT NOT NULL UNIQUE,
    slug  TEXT NOT NULL UNIQUE,
    icone TEXT NOT NULL DEFAULT '🔧'
);
CREATE TABLE IF NOT EXISTS prestadores (
    id           SERIAL PRIMARY KEY,
    nome         TEXT NOT NULL,
    categoria_id INTEGER NOT NULL REFERENCES categorias(id),
    cidade       TEXT NOT NULL DEFAULT 'Sorriso/MT',
    telefone     TEXT, whatsapp TEXT, descricao TEXT,
    verificado   INTEGER NOT NULL DEFAULT 0,
    criado_em    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS avaliacoes (
    id           SERIAL PRIMARY KEY,
    prestador_id INTEGER NOT NULL REFERENCES prestadores(id) ON DELETE CASCADE,
    autor        TEXT NOT NULL,
    nota         INTEGER NOT NULL CHECK (nota BETWEEN 1 AND 5),
    comentario   TEXT,
    status       TEXT NOT NULL DEFAULT 'pendente',
    criado_em    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS usuarios (
    id           SERIAL PRIMARY KEY,
    email        TEXT NOT NULL UNIQUE,
    senha_hash   TEXT NOT NULL,
    papel        TEXT NOT NULL DEFAULT 'prestador',
    prestador_id INTEGER REFERENCES prestadores(id) ON DELETE CASCADE,
    criado_em    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_prestadores_categoria ON prestadores(categoria_id);
CREATE INDEX IF NOT EXISTS idx_avaliacoes_prestador ON avaliacoes(prestador_id);
CREATE INDEX IF NOT EXISTS idx_avaliacoes_status ON avaliacoes(status);
CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);
"""


# ---------------------------------------------------------------- conexão
def get_conn():
    if BACKEND == "sqlite":
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    import psycopg2
    from psycopg2.extras import RealDictCursor
    return psycopg2.connect(_DB_URL, cursor_factory=RealDictCursor)


def _prep(sql):
    return sql if BACKEND == "sqlite" else sql.replace("?", "%s")


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    if BACKEND == "sqlite":
        cur.executescript(_DDL_SQLITE)
    else:
        cur.execute(_DDL_POSTGRES)
    conn.commit()
    cur.close()
    conn.close()


def query(sql, params=(), one=False):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(_prep(sql), params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return (rows[0] if rows else None) if one else rows


def execute(sql, params=()):
    conn = get_conn()
    cur = conn.cursor()
    new_id = None
    is_insert = sql.lstrip()[:6].upper() == "INSERT"
    if BACKEND == "postgres" and is_insert and "RETURNING" not in sql.upper():
        sql = sql.rstrip().rstrip(";") + " RETURNING id"
    cur.execute(_prep(sql), params)
    if BACKEND == "postgres":
        if is_insert:
            row = cur.fetchone()
            new_id = row["id"] if row else None
    else:
        new_id = cur.lastrowid
    conn.commit()
    cur.close()
    conn.close()
    return new_id
