import os
import tempfile
import unittest
from app import create_app


class BaseTest(unittest.TestCase):
    """Cria um banco temporário novo para cada teste."""

    def setUp(self):
        self.fd, self.path = tempfile.mkstemp(suffix=".db")
        self.app = create_app({"DATABASE": self.path, "TESTING": True})
        self.client = self.app.test_client()

    def tearDown(self):
        os.close(self.fd)
        os.remove(self.path)

    # --- helpers ---
    def login(self, email, senha):
        r = self.client.post("/api/auth/login", json={"email": email, "senha": senha})
        return r.get_json()

    def hdr(self, email, senha):
        return {"Authorization": "Bearer " + self.login(email, senha)["token"]}

    def admin(self):
        return self.hdr("admin@academia.com", "admin123")

    def novo_usuario(self, hdr, perfil="aluno", n=1, **extra):
        d = {"nome_completo": f"Pessoa Teste{n}", "email": f"{perfil}{n}@teste.com",
             "telefone": "75988887777", "senha": "senha123", "perfil": perfil, **extra}
        r = self.client.post("/api/usuarios", json=d, headers=hdr)
        self.assertEqual(r.status_code, 201, r.get_json())
        return r.get_json()["id"], d

    def novo_exercicio(self, hdr, nome="Supino Reto", tipo="musculacao"):
        r = self.client.post("/api/exercicios", json={"nome": nome, "tipo": tipo}, headers=hdr)
        self.assertEqual(r.status_code, 201, r.get_json())
        return r.get_json()["id"]
