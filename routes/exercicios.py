import sqlite3
from flask import Blueprint, jsonify, request
import validators as v
from auth import auth, erro
from db import q, run

bp = Blueprint("exercicios", __name__, url_prefix="/api")


@bp.get("/grupos")
@auth()
def listar_grupos():
    return jsonify(q("SELECT * FROM grupos_musculares ORDER BY nome"))


@bp.post("/grupos")
@auth("admin", "professor")
def criar_grupo():
    nome = ((request.get_json(silent=True) or {}).get("nome") or "").strip()
    if len(nome) < 2:
        return erro("Informe o nome do grupo muscular")
    if q("SELECT 1 FROM grupos_musculares WHERE nome=?", (nome,), one=True):
        return erro("Grupo já cadastrado", 409)
    return jsonify({"id": run("INSERT INTO grupos_musculares(nome) VALUES(?)", (nome,))}), 201


@bp.get("/exercicios")
@auth()
def listar():
    sql = ("SELECT e.id,e.nome,e.tipo,e.grupo_muscular_id,g.nome AS grupo FROM exercicios e "
           "LEFT JOIN grupos_musculares g ON g.id=e.grupo_muscular_id WHERE e.nome LIKE ?")
    args = [f"%{request.args.get('q', '').strip()}%"]
    if request.args.get("tipo"):
        sql += " AND e.tipo=?"
        args.append(request.args["tipo"])
    if request.args.get("grupo_id"):
        sql += " AND e.grupo_muscular_id=?"
        args.append(request.args["grupo_id"])
    return jsonify(q(sql + " ORDER BY e.nome", args))


def validar(d):
    nome = (d.get("nome") or "").strip()
    if len(nome) < 2:
        return "Informe o nome do exercício"
    if d.get("tipo") not in v.TIPOS_EXERCICIO:
        return "Tipo inválido (musculacao, cardio ou alongamento)"
    gid = d.get("grupo_muscular_id")
    if gid and not q("SELECT 1 FROM grupos_musculares WHERE id=?", (gid,), one=True):
        return "Grupo muscular não encontrado"
    return None


@bp.post("/exercicios")
@auth("admin", "professor")
def criar():
    d = request.get_json(silent=True) or {}
    msg = validar(d)
    if msg:
        return erro(msg)
    nome = d["nome"].strip()
    if q("SELECT 1 FROM exercicios WHERE nome=?", (nome,), one=True):
        return erro("Exercício já cadastrado", 409)
    eid = run("INSERT INTO exercicios(nome,tipo,grupo_muscular_id) VALUES(?,?,?)",
              (nome, d["tipo"], d.get("grupo_muscular_id")))
    return jsonify({"id": eid}), 201


@bp.put("/exercicios/<int:eid>")
@auth("admin", "professor")
def editar(eid):
    d = request.get_json(silent=True) or {}
    if not q("SELECT 1 FROM exercicios WHERE id=?", (eid,), one=True):
        return erro("Exercício não encontrado", 404)
    msg = validar(d)
    if msg:
        return erro(msg)
    try:
        run("UPDATE exercicios SET nome=?,tipo=?,grupo_muscular_id=? WHERE id=?",
            (d["nome"].strip(), d["tipo"], d.get("grupo_muscular_id"), eid))
    except sqlite3.IntegrityError:
        return erro("Já existe exercício com esse nome", 409)
    return jsonify({"ok": True})


@bp.delete("/exercicios/<int:eid>")
@auth("admin", "professor")
def remover(eid):
    if not q("SELECT 1 FROM exercicios WHERE id=?", (eid,), one=True):
        return erro("Exercício não encontrado", 404)
    em_uso = q("SELECT 1 FROM ficha_exercicios fe JOIN fichas_treino f ON f.id=fe.ficha_id "
               "WHERE fe.exercicio_id=? AND f.ativa=1", (eid,), one=True)
    if em_uso:
        return erro("Exercício está em uma ficha ativa e não pode ser removido", 409)
    try:
        run("DELETE FROM exercicios WHERE id=?", (eid,))
    except sqlite3.IntegrityError:
        return erro("Exercício possui histórico de treinos e não pode ser removido", 409)
    return jsonify({"ok": True})
