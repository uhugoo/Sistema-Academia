import unittest
import jwt
from auth import gerar_token


class TestToken(unittest.TestCase):
    def test_token_contem_usuario_e_perfil(self):
        from flask import Flask
        app = Flask(__name__)
        app.config["SECRET_KEY"] = "chave-de-teste-com-tamanho-suficiente-123"
        with app.app_context():
            token = gerar_token({"id": 7, "perfil": "professor"})
            dados = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        self.assertEqual(dados["sub"], "7")
        self.assertEqual(dados["perfil"], "professor")
        self.assertIn("exp", dados)
