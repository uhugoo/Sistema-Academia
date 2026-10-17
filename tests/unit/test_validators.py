import unittest
import validators as v


class TestValidators(unittest.TestCase):
    def test_nome_completo(self):
        self.assertIsNone(v.nome("Maria Silva"))
        self.assertIsNotNone(v.nome("Maria"))
        self.assertIsNotNone(v.nome(""))

    def test_email(self):
        self.assertIsNone(v.email("a@b.com"))
        for ruim in ("", "abc", "a@b", "a b@c.com", None):
            self.assertIsNotNone(v.email(ruim), ruim)

    def test_telefone(self):
        self.assertIsNone(v.telefone("(75) 98888-7777"))
        self.assertIsNone(v.telefone("7533334444"))
        self.assertIsNotNone(v.telefone("12345"))

    def test_senha(self):
        self.assertIsNone(v.senha("123456"))
        self.assertIsNotNone(v.senha("123"))

    def test_inteiro_positivo(self):
        self.assertIsNone(v.inteiro_positivo(3, "x"))
        for ruim in (0, -1, 2.5, "3", True, None):
            self.assertIsNotNone(v.inteiro_positivo(ruim, "x"), ruim)

    def test_carga(self):
        self.assertIsNone(v.carga(0))
        self.assertIsNone(v.carga(22.5))
        self.assertIsNotNone(v.carga(-1))
        self.assertIsNotNone(v.carga("10"))

    def test_intervalo_e_data(self):
        self.assertIsNone(v.intervalo(70, 20, 400, "Peso"))
        self.assertIsNotNone(v.intervalo(10, 20, 400, "Peso"))
        self.assertIsNone(v.data("2026-03-15"))
        self.assertIsNotNone(v.data("15/03/2026"))
