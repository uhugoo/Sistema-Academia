from tests.base import BaseTest


class TestLoginEAcesso(BaseTest):
    def test_login_valido_e_invalido(self):
        ok = self.login("admin@academia.com", "admin123")
        self.assertIn("token", ok)
        self.assertEqual(ok["perfil"], "admin")
        r = self.client.post("/api/auth/login", json={"email": "admin@academia.com", "senha": "errada"})
        self.assertEqual(r.status_code, 401)

    def test_rota_protegida_sem_token(self):
        self.assertEqual(self.client.get("/api/usuarios").status_code, 401)

    def test_aluno_nao_acessa_area_admin(self):
        adm = self.admin()
        _, d = self.novo_usuario(adm, "aluno")
        h = self.hdr(d["email"], d["senha"])
        self.assertEqual(self.client.get("/api/usuarios", headers=h).status_code, 403)
        self.assertEqual(self.client.post("/api/planos", json={}, headers=h).status_code, 403)

    def test_registro_publico_cria_aluno(self):
        r = self.client.post("/api/auth/registro", json={
            "nome_completo": "Joao Souza", "email": "joao@x.com", "telefone": "75911112222", "senha": "abc123"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.login("joao@x.com", "abc123")["perfil"], "aluno")


class TestUsuarios(BaseTest):
    def test_cadastro_e_remocao(self):
        adm = self.admin()
        uid, d = self.novo_usuario(adm, "professor")
        emails = [u["email"] for u in self.client.get("/api/usuarios", headers=adm).get_json()]
        self.assertIn(d["email"], emails)
        self.assertEqual(self.client.delete(f"/api/usuarios/{uid}", headers=adm).status_code, 200)
        emails = [u["email"] for u in self.client.get("/api/usuarios", headers=adm).get_json()]
        self.assertNotIn(d["email"], emails)

    def test_email_duplicado_e_dados_invalidos(self):
        adm = self.admin()
        _, d = self.novo_usuario(adm)
        self.assertEqual(self.client.post("/api/usuarios", json=d, headers=adm).status_code, 409)
        ruim = dict(d, email="invalido", nome_completo="Um")
        self.assertEqual(self.client.post("/api/usuarios", json=ruim, headers=adm).status_code, 400)

    def test_admin_nao_remove_a_si_mesmo(self):
        adm = self.admin()
        r = self.client.delete("/api/usuarios/1", headers=adm)
        self.assertEqual(r.status_code, 400)

    def test_professor_so_ve_os_proprios_alunos(self):
        adm = self.admin()
        p1, d1 = self.novo_usuario(adm, "professor", 1)
        p2, d2 = self.novo_usuario(adm, "professor", 2)
        h1, h2 = self.hdr(d1["email"], d1["senha"]), self.hdr(d2["email"], d2["senha"])
        self.novo_usuario(h1, "aluno", 1)
        self.novo_usuario(h2, "aluno", 2)
        nomes1 = [u["email"] for u in self.client.get("/api/usuarios", headers=h1).get_json()]
        self.assertEqual(nomes1, ["aluno1@teste.com"])


class TestExercicios(BaseTest):
    def test_crud_e_filtros(self):
        adm = self.admin()
        eid = self.novo_exercicio(adm, "Supino Reto")
        self.novo_exercicio(adm, "Esteira", "cardio")
        r = self.client.get("/api/exercicios?tipo=cardio", headers=adm).get_json()
        self.assertEqual([e["nome"] for e in r], ["Esteira"])
        r = self.client.get("/api/exercicios?q=supino", headers=adm).get_json()
        self.assertEqual(len(r), 1)
        self.assertEqual(self.client.put(f"/api/exercicios/{eid}", headers=adm,
                         json={"nome": "Supino Inclinado", "tipo": "musculacao"}).status_code, 200)
        self.assertEqual(self.client.delete(f"/api/exercicios/{eid}", headers=adm).status_code, 200)

    def test_tipo_invalido_e_duplicado(self):
        adm = self.admin()
        self.assertEqual(self.client.post("/api/exercicios", json={"nome": "Abc", "tipo": "yoga"}, headers=adm).status_code, 400)
        self.novo_exercicio(adm)
        self.assertEqual(self.client.post("/api/exercicios", json={"nome": "Supino Reto", "tipo": "cardio"}, headers=adm).status_code, 409)

    def test_aluno_nao_cadastra_exercicio(self):
        adm = self.admin()
        _, d = self.novo_usuario(adm)
        h = self.hdr(d["email"], d["senha"])
        self.assertEqual(self.client.post("/api/exercicios", json={"nome": "Abc", "tipo": "cardio"}, headers=h).status_code, 403)


class TestFluxoCompleto(BaseTest):
    """Professor cria ficha -> aluno registra treino -> dashboard mostra evolução."""

    def preparar(self):
        adm = self.admin()
        _, dp = self.novo_usuario(adm, "professor")
        hp = self.hdr(dp["email"], dp["senha"])
        aid, da = self.novo_usuario(hp, "aluno")
        ha = self.hdr(da["email"], da["senha"])
        eid = self.novo_exercicio(hp)
        r = self.client.post("/api/fichas", headers=hp, json={
            "aluno_id": aid, "nome": "Ficha A",
            "exercicios": [{"exercicio_id": eid, "series": 3, "repeticoes": 10, "carga_kg": 40}]})
        self.assertEqual(r.status_code, 201, r.get_json())
        return adm, hp, ha, aid, eid, r.get_json()["id"]

    def test_fluxo(self):
        adm, hp, ha, aid, eid, fid = self.preparar()
        series = [{"exercicio_id": eid, "serie_num": n, "repeticoes": 10, "carga_kg": 40} for n in (1, 2, 3)]
        r = self.client.post("/api/treinos", headers=ha, json={"ficha_id": fid, "duracao_min": 50, "series": series})
        self.assertEqual(r.status_code, 201, r.get_json())
        self.client.post("/api/avaliacoes", headers=hp, json={"aluno_id": aid, "peso": 80, "altura": 1.8, "percentual_gordura": 20})
        dash = self.client.get(f"/api/dashboard/{aid}", headers=ha).get_json()
        self.assertEqual(dash["total_treinos"], 1)
        self.assertEqual(dash["treinos"][0]["volume"], 1200)
        self.assertEqual(dash["carga_maxima"], 40)
        self.assertEqual(dash["avaliacoes"][0]["imc"], 24.7)

    def test_exercicio_em_ficha_ativa_nao_pode_ser_removido(self):
        adm, hp, ha, aid, eid, fid = self.preparar()
        self.assertEqual(self.client.delete(f"/api/exercicios/{eid}", headers=hp).status_code, 409)
        self.client.put(f"/api/fichas/{fid}/ativa", headers=hp, json={"ativa": False})
        self.assertEqual(self.client.delete(f"/api/exercicios/{eid}", headers=hp).status_code, 200)

    def test_validacoes_de_ficha_e_treino(self):
        adm, hp, ha, aid, eid, fid = self.preparar()
        ruim = {"aluno_id": aid, "nome": "X1", "exercicios": [{"exercicio_id": eid, "series": 0, "repeticoes": 10, "carga_kg": 5}]}
        self.assertEqual(self.client.post("/api/fichas", headers=hp, json=ruim).status_code, 400)
        serie = {"exercicio_id": eid, "serie_num": 1, "repeticoes": -3, "carga_kg": 40}
        r = self.client.post("/api/treinos", headers=ha, json={"ficha_id": fid, "duracao_min": 30, "series": [serie]})
        self.assertEqual(r.status_code, 400)

    def test_isolamento_entre_alunos_e_professores(self):
        adm, hp, ha, aid, eid, fid = self.preparar()
        _, d2 = self.novo_usuario(adm, "aluno", 9)
        h2 = self.hdr(d2["email"], d2["senha"])
        self.assertEqual(self.client.get(f"/api/dashboard/{aid}", headers=h2).status_code, 403)
        self.assertEqual(self.client.get("/api/fichas", headers=h2).get_json(), [])
        _, dp2 = self.novo_usuario(adm, "professor", 5)
        hp2 = self.hdr(dp2["email"], dp2["senha"])
        self.assertEqual(self.client.get(f"/api/dashboard/{aid}", headers=hp2).status_code, 403)
        self.assertEqual(len(self.client.get("/api/fichas", headers=hp).get_json()), 1)


class TestPlanos(BaseTest):
    def test_venda_de_plano(self):
        adm = self.admin()
        aid, _ = self.novo_usuario(adm)
        planos = self.client.get("/api/planos", headers=adm).get_json()
        anual = [p for p in planos if p["nome"] == "Anual"][0]
        r = self.client.post("/api/matriculas", headers=adm, json={"aluno_id": aid, "plano_id": anual["id"]})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["valor_pago"], anual["valor"])
        self.assertEqual(len(self.client.get("/api/matriculas", headers=adm).get_json()), 1)

    def test_plano_inexistente(self):
        adm = self.admin()
        aid, _ = self.novo_usuario(adm)
        r = self.client.post("/api/matriculas", headers=adm, json={"aluno_id": aid, "plano_id": 999})
        self.assertEqual(r.status_code, 404)
