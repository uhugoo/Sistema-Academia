from datetime import date, timedelta
from flask import Blueprint, jsonify, request
import validators as v
from auth import auth, erro, filtro_aluno
from db import q, run

bp = Blueprint("financeiro", __name__, url_prefix="/api")


@bp.get("/planos")
@auth()
def listar_planos():
    return jsonify(q("SELECT * FROM planos ORDER BY duracao_meses"))


@bp.post("/planos")
@auth("admin")
def criar_plano():
    d = request.get_json(silent=True) or {}
    nome = (d.get("nome") or "").strip()
    if len(nome) < 2:
        return erro("Informe o nome do plano")
    msg = v.intervalo(d.get("valor"), 0.01, 100000, "Valor") or v.inteiro_positivo(d.get("duracao_meses"), "Duração")
    if msg:
        return erro(msg)
    if q("SELECT 1 FROM planos WHERE nome=?", (nome,), one=True):
        return erro("Plano já cadastrado", 409)
    return jsonify({"id": run("INSERT INTO planos(nome,valor,duracao_meses) VALUES(?,?,?)",
                              (nome, d["valor"], d["duracao_meses"]))}), 201


@bp.post("/matriculas")
@auth("admin")
def matricular():
    """Venda de plano: registra a matrícula do aluno com valor e vigência."""
    d = request.get_json(silent=True) or {}
    if not q("SELECT 1 FROM alunos WHERE usuario_id=?", (d.get("aluno_id"),), one=True):
        return erro("Aluno não encontrado", 404)
    plano = q("SELECT * FROM planos WHERE id=?", (d.get("plano_id"),), one=True)
    if not plano:
        return erro("Plano não encontrado", 404)
    inicio = date.today()
    fim = inicio + timedelta(days=30 * plano["duracao_meses"])
    mid = run("INSERT INTO matriculas(aluno_id,plano_id,data_inicio,data_fim,valor_pago) VALUES(?,?,?,?,?)",
              (d["aluno_id"], plano["id"], inicio.isoformat(), fim.isoformat(), plano["valor"]))
    return jsonify({"id": mid, "data_fim": fim.isoformat(), "valor_pago": plano["valor"]}), 201


@bp.get("/matriculas")
@auth("admin", "aluno")
def listar_matriculas():
    filtro, args = filtro_aluno("m.aluno_id")
    return jsonify(q("SELECT m.*,u.nome_completo AS aluno,p.nome AS plano FROM matriculas m "
                     "JOIN usuarios u ON u.id=m.aluno_id JOIN planos p ON p.id=m.plano_id "
                     f"WHERE {filtro} ORDER BY m.data_inicio DESC", args))
