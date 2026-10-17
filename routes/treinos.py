from datetime import date
from flask import Blueprint, g, jsonify, request
import validators as v
from auth import auth, erro, filtro_aluno, pode_ver_aluno
from db import get_db, q, run

bp = Blueprint("treinos", __name__, url_prefix="/api")


def _itens_ficha(ficha_id):
    return q("SELECT fe.exercicio_id,e.nome,fe.series,fe.repeticoes,fe.carga_kg FROM ficha_exercicios fe "
             "JOIN exercicios e ON e.id=fe.exercicio_id WHERE fe.ficha_id=? ORDER BY fe.ordem", (ficha_id,))


# ---------- Fichas de treino ----------
@bp.get("/fichas")
@auth()
def listar_fichas():
    filtro, args = filtro_aluno("f.aluno_id")
    sql = ("SELECT f.id,f.aluno_id,u.nome_completo AS aluno,f.nome,f.data_inicio,f.ativa FROM fichas_treino f "
           f"JOIN usuarios u ON u.id=f.aluno_id WHERE {filtro}")
    if request.args.get("aluno_id"):
        sql += " AND f.aluno_id=?"
        args += (request.args["aluno_id"],)
    fichas = q(sql + " ORDER BY f.id DESC", args)
    for f in fichas:
        f["exercicios"] = _itens_ficha(f["id"])
    return jsonify(fichas)


@bp.post("/fichas")
@auth("admin", "professor")
def criar_ficha():
    d = request.get_json(silent=True) or {}
    aluno_id = d.get("aluno_id")
    if not isinstance(aluno_id, int) or not q("SELECT 1 FROM alunos WHERE usuario_id=?", (aluno_id,), one=True):
        return erro("Aluno não encontrado", 404)
    if not pode_ver_aluno(aluno_id):
        return erro("Este aluno não pertence a você", 403)
    nome = (d.get("nome") or "").strip()
    itens = d.get("exercicios") or []
    if len(nome) < 2:
        return erro("Informe o nome da ficha")
    if not itens:
        return erro("A ficha precisa de pelo menos um exercício")
    for it in itens:
        msg = (v.inteiro_positivo(it.get("series"), "Séries") or
               v.inteiro_positivo(it.get("repeticoes"), "Repetições") or v.carga(it.get("carga_kg")))
        if msg:
            return erro(msg)
        if not q("SELECT 1 FROM exercicios WHERE id=?", (it.get("exercicio_id"),), one=True):
            return erro("Exercício não encontrado", 404)
    fid = run("INSERT INTO fichas_treino(aluno_id,professor_id,nome,data_inicio) VALUES(?,?,?,?)",
              (aluno_id, g.user["id"] if g.user["perfil"] == "professor" else None, nome, date.today().isoformat()))
    for ordem, it in enumerate(itens, 1):
        run("INSERT INTO ficha_exercicios(ficha_id,exercicio_id,series,repeticoes,carga_kg,ordem) VALUES(?,?,?,?,?,?)",
            (fid, it["exercicio_id"], it["series"], it["repeticoes"], it["carga_kg"], ordem))
    return jsonify({"id": fid}), 201


@bp.put("/fichas/<int:fid>/ativa")
@auth("admin", "professor")
def alternar_ficha(fid):
    f = q("SELECT aluno_id FROM fichas_treino WHERE id=?", (fid,), one=True)
    if not f:
        return erro("Ficha não encontrada", 404)
    if not pode_ver_aluno(f["aluno_id"]):
        return erro("Acesso negado", 403)
    ativa = 1 if (request.get_json(silent=True) or {}).get("ativa", True) else 0
    run("UPDATE fichas_treino SET ativa=? WHERE id=?", (ativa, fid))
    return jsonify({"ok": True, "ativa": ativa})


@bp.delete("/fichas/<int:fid>")
@auth("admin", "professor")
def remover_ficha(fid):
    f = q("SELECT aluno_id FROM fichas_treino WHERE id=?", (fid,), one=True)
    if not f:
        return erro("Ficha não encontrada", 404)
    if not pode_ver_aluno(f["aluno_id"]):
        return erro("Acesso negado", 403)
    run("DELETE FROM fichas_treino WHERE id=?", (fid,))
    return jsonify({"ok": True})


# ---------- Treinos realizados ----------
@bp.post("/treinos")
@auth("aluno")
def registrar_treino():
    d = request.get_json(silent=True) or {}
    ficha = q("SELECT * FROM fichas_treino WHERE id=? AND aluno_id=?", (d.get("ficha_id"), g.user["id"]), one=True)
    if not ficha:
        return erro("Ficha não encontrada", 404)
    if not ficha["ativa"]:
        return erro("Esta ficha está inativa", 409)
    dia = d.get("data") or date.today().isoformat()
    msg = v.data(dia) or v.inteiro_positivo(d.get("duracao_min"), "Duração")
    series = d.get("series") or []
    if msg or not series:
        return erro(msg or "Registre ao menos uma série")
    ids_ficha = {i["exercicio_id"] for i in _itens_ficha(ficha["id"])}
    for s in series:
        msg = (v.inteiro_positivo(s.get("serie_num"), "Nº da série") or
               v.inteiro_positivo(s.get("repeticoes"), "Repetições") or v.carga(s.get("carga_kg")))
        if msg:
            return erro(msg)
        if s.get("exercicio_id") not in ids_ficha:
            return erro("Exercício não pertence à ficha")
    tid = run("INSERT INTO treinos_realizados(aluno_id,ficha_id,data,duracao_min) VALUES(?,?,?,?)",
              (g.user["id"], ficha["id"], dia, d["duracao_min"]))
    db = get_db()
    db.executemany("INSERT INTO registros_serie(treino_id,exercicio_id,serie_num,repeticoes,carga_kg) VALUES(?,?,?,?,?)",
                   [(tid, s["exercicio_id"], s["serie_num"], s["repeticoes"], s["carga_kg"]) for s in series])
    db.commit()
    return jsonify({"id": tid}), 201


@bp.get("/treinos")
@auth()
def historico():
    filtro, args = filtro_aluno("t.aluno_id")
    sql = ("SELECT t.id,t.aluno_id,u.nome_completo AS aluno,f.nome AS ficha,t.data,t.duracao_min,"
           "COALESCE(SUM(r.repeticoes*r.carga_kg),0) AS volume FROM treinos_realizados t "
           "JOIN usuarios u ON u.id=t.aluno_id LEFT JOIN fichas_treino f ON f.id=t.ficha_id "
           f"LEFT JOIN registros_serie r ON r.treino_id=t.id WHERE {filtro}")
    if request.args.get("aluno_id"):
        sql += " AND t.aluno_id=?"
        args += (request.args["aluno_id"],)
    return jsonify(q(sql + " GROUP BY t.id ORDER BY t.data DESC, t.id DESC", args))


# ---------- Avaliações físicas ----------
@bp.post("/avaliacoes")
@auth("admin", "professor")
def criar_avaliacao():
    d = request.get_json(silent=True) or {}
    aluno_id = d.get("aluno_id")
    if not isinstance(aluno_id, int) or not q("SELECT 1 FROM alunos WHERE usuario_id=?", (aluno_id,), one=True):
        return erro("Aluno não encontrado", 404)
    if not pode_ver_aluno(aluno_id):
        return erro("Este aluno não pertence a você", 403)
    dia = d.get("data") or date.today().isoformat()
    msg = (v.data(dia) or v.intervalo(d.get("peso"), 20, 400, "Peso (kg)") or
           v.intervalo(d.get("altura"), 0.5, 2.5, "Altura (m)") or
           v.intervalo(d.get("percentual_gordura"), 1, 70, "% de gordura"))
    if msg:
        return erro(msg)
    aid = run("INSERT INTO avaliacoes_fisicas(aluno_id,data,peso,altura,percentual_gordura) VALUES(?,?,?,?,?)",
              (aluno_id, dia, d["peso"], d["altura"], d["percentual_gordura"]))
    return jsonify({"id": aid}), 201


@bp.get("/avaliacoes")
@auth()
def listar_avaliacoes():
    filtro, args = filtro_aluno("a.aluno_id")
    sql = ("SELECT a.*,u.nome_completo AS aluno,ROUND(a.peso/(a.altura*a.altura),1) AS imc "
           f"FROM avaliacoes_fisicas a JOIN usuarios u ON u.id=a.aluno_id WHERE {filtro}")
    if request.args.get("aluno_id"):
        sql += " AND a.aluno_id=?"
        args += (request.args["aluno_id"],)
    return jsonify(q(sql + " ORDER BY a.data DESC, a.id DESC", args))


# ---------- Dashboard ----------
@bp.get("/dashboard/<int:aluno_id>")
@auth()
def dashboard(aluno_id):
    if not pode_ver_aluno(aluno_id):
        return erro("Acesso negado", 403)
    avaliacoes = q("SELECT data,peso,percentual_gordura,ROUND(peso/(altura*altura),1) AS imc "
                   "FROM avaliacoes_fisicas WHERE aluno_id=? ORDER BY data", (aluno_id,))
    treinos = q("SELECT t.data,t.duracao_min,COALESCE(SUM(r.repeticoes*r.carga_kg),0) AS volume "
                "FROM treinos_realizados t LEFT JOIN registros_serie r ON r.treino_id=t.id "
                "WHERE t.aluno_id=? GROUP BY t.id ORDER BY t.data,t.id", (aluno_id,))
    carga_max = q("SELECT MAX(carga_kg) AS m FROM registros_serie r JOIN treinos_realizados t ON t.id=r.treino_id "
                  "WHERE t.aluno_id=?", (aluno_id,), one=True)["m"]
    return jsonify({"avaliacoes": avaliacoes, "treinos": treinos, "total_treinos": len(treinos),
                    "carga_maxima": carga_max or 0,
                    "tempo_total_min": sum(t["duracao_min"] for t in treinos)})
