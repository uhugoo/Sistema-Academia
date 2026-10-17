from flask import Blueprint, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash
import validators as v
from auth import auth, erro, gerar_token
from db import q, run

bp = Blueprint("usuarios", __name__, url_prefix="/api")


def criar_usuario(d, perfil, professor_id=None):
    nome = (d.get("nome_completo") or "").strip()
    email = (d.get("email") or "").strip().lower()
    tel = d.get("telefone") or ""
    senha = d.get("senha") or ""
    for msg in (v.nome(nome), v.email(email), v.telefone(tel), v.senha(senha)):
        if msg:
            return None, msg
    if perfil not in v.PERFIS:
        return None, "Perfil inválido"
    if q("SELECT 1 FROM usuarios WHERE email=?", (email,), one=True):
        return None, "E-mail já cadastrado"
    uid = run("INSERT INTO usuarios(nome_completo,email,telefone,senha_hash,perfil) VALUES(?,?,?,?,?)",
              (nome, email, tel, generate_password_hash(senha), perfil))
    if perfil == "aluno":
        run("INSERT INTO alunos(usuario_id,professor_id) VALUES(?,?)", (uid, professor_id))
    return uid, None


@bp.post("/auth/login")
def login():
    d = request.get_json(silent=True) or {}
    u = q("SELECT * FROM usuarios WHERE email=?", ((d.get("email") or "").strip().lower(),), one=True)
    if not u or not check_password_hash(u["senha_hash"], d.get("senha") or ""):
        return erro("E-mail ou senha incorretos", 401)
    if not u["ativo"]:
        return erro("Usuário inativo", 403)
    return jsonify({"token": gerar_token(u), "id": u["id"], "nome": u["nome_completo"], "perfil": u["perfil"]})


@bp.post("/auth/registro")
def registro():
    uid, msg = criar_usuario(request.get_json(silent=True) or {}, "aluno")
    if msg:
        return erro(msg, 409 if "cadastrado" in msg else 400)
    return jsonify({"id": uid}), 201


@bp.get("/usuarios")
@auth("admin", "professor")
def listar():
    busca = f"%{request.args.get('q', '').strip()}%"
    perfil = request.args.get("perfil")
    sql = ("SELECT u.id,u.nome_completo,u.email,u.telefone,u.perfil,a.professor_id FROM usuarios u "
           "LEFT JOIN alunos a ON a.usuario_id=u.id WHERE (u.nome_completo LIKE ? OR u.email LIKE ?)")
    args = [busca, busca]
    if g.user["perfil"] == "professor":
        sql += " AND a.professor_id=?"
        args.append(g.user["id"])
    if perfil in v.PERFIS:
        sql += " AND u.perfil=?"
        args.append(perfil)
    return jsonify(q(sql + " ORDER BY u.nome_completo", args))


@bp.post("/usuarios")
@auth("admin", "professor")
def criar():
    d = request.get_json(silent=True) or {}
    if g.user["perfil"] == "professor":
        perfil, prof_id = "aluno", g.user["id"]
    else:
        perfil, prof_id = d.get("perfil", "aluno"), d.get("professor_id")
        if prof_id and not q("SELECT 1 FROM usuarios WHERE id=? AND perfil='professor'", (prof_id,), one=True):
            return erro("Professor não encontrado", 404)
    uid, msg = criar_usuario(d, perfil, prof_id)
    if msg:
        return erro(msg, 409 if "cadastrado" in msg else 400)
    return jsonify({"id": uid}), 201


@bp.delete("/usuarios/<int:uid>")
@auth("admin")
def remover(uid):
    if uid == g.user["id"]:
        return erro("Você não pode remover o próprio usuário", 400)
    if not q("SELECT 1 FROM usuarios WHERE id=?", (uid,), one=True):
        return erro("Usuário não encontrado", 404)
    run("DELETE FROM usuarios WHERE id=?", (uid,))
    return jsonify({"ok": True})
