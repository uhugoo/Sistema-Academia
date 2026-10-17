import sqlite3
from flask import current_app, g
from werkzeug.security import generate_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome_completo TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  telefone TEXT NOT NULL,
  senha_hash TEXT NOT NULL,
  perfil TEXT NOT NULL CHECK(perfil IN ('aluno','professor','admin')),
  ativo INTEGER NOT NULL DEFAULT 1,
  criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS alunos(
  usuario_id INTEGER PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
  professor_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
  data_nascimento TEXT, objetivo TEXT);
CREATE TABLE IF NOT EXISTS grupos_musculares(
  id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS exercicios(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL UNIQUE,
  tipo TEXT NOT NULL CHECK(tipo IN ('musculacao','cardio','alongamento')),
  grupo_muscular_id INTEGER REFERENCES grupos_musculares(id) ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS fichas_treino(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  aluno_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  professor_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
  nome TEXT NOT NULL, data_inicio TEXT NOT NULL, ativa INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS ficha_exercicios(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ficha_id INTEGER NOT NULL REFERENCES fichas_treino(id) ON DELETE CASCADE,
  exercicio_id INTEGER NOT NULL REFERENCES exercicios(id) ON DELETE CASCADE,
  series INTEGER NOT NULL, repeticoes INTEGER NOT NULL, carga_kg REAL NOT NULL, ordem INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS treinos_realizados(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  aluno_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  ficha_id INTEGER REFERENCES fichas_treino(id) ON DELETE SET NULL,
  data TEXT NOT NULL, duracao_min INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS registros_serie(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  treino_id INTEGER NOT NULL REFERENCES treinos_realizados(id) ON DELETE CASCADE,
  exercicio_id INTEGER NOT NULL REFERENCES exercicios(id) ON DELETE RESTRICT,
  serie_num INTEGER NOT NULL, repeticoes INTEGER NOT NULL, carga_kg REAL NOT NULL);
CREATE TABLE IF NOT EXISTS avaliacoes_fisicas(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  aluno_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  data TEXT NOT NULL, peso REAL NOT NULL, altura REAL NOT NULL, percentual_gordura REAL NOT NULL);
CREATE TABLE IF NOT EXISTS planos(
  id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE,
  valor REAL NOT NULL, duracao_meses INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS matriculas(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  aluno_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  plano_id INTEGER NOT NULL REFERENCES planos(id) ON DELETE RESTRICT,
  data_inicio TEXT NOT NULL, data_fim TEXT NOT NULL, valor_pago REAL NOT NULL);
"""

GRUPOS_PADRAO = ["Peito", "Costas", "Pernas", "Ombros", "Braços", "Abdômen", "Cardio", "Mobilidade"]
PLANOS_PADRAO = [("Mensal", 99.90, 1), ("Trimestral", 269.90, 3), ("Anual", 899.90, 12)]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def q(sql, args=(), one=False):
    rows = [dict(r) for r in get_db().execute(sql, args).fetchall()]
    if one:
        return rows[0] if rows else None
    return rows


def run(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid


def init_db():
    """Cria tabelas e dados iniciais (admin, grupos musculares e planos)."""
    db = get_db()
    db.executescript(SCHEMA)
    if not q("SELECT 1 FROM usuarios WHERE perfil='admin'", one=True):
        run("INSERT INTO usuarios(nome_completo,email,telefone,senha_hash,perfil) VALUES(?,?,?,?,?)",
            ("Administrador Geral", "admin@academia.com", "75999999999",
             generate_password_hash("admin123"), "admin"))
    for g_nome in GRUPOS_PADRAO:
        db.execute("INSERT OR IGNORE INTO grupos_musculares(nome) VALUES(?)", (g_nome,))
    for nome, valor, meses in PLANOS_PADRAO:
        db.execute("INSERT OR IGNORE INTO planos(nome,valor,duracao_meses) VALUES(?,?,?)", (nome, valor, meses))
    db.commit()
