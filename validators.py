"""Validações de dados. Cada função retorna None se OK, ou a mensagem de erro."""
import re
from datetime import datetime

TIPOS_EXERCICIO = ("musculacao", "cardio", "alongamento")
PERFIS = ("aluno", "professor", "admin")


def nome(valor):
    if not valor or len(valor.strip().split()) < 2:
        return "Informe o nome completo (nome e sobrenome)"
    return None


def email(valor):
    if not valor or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", valor):
        return "E-mail inválido"
    return None


def telefone(valor):
    digitos = re.sub(r"\D", "", valor or "")
    if len(digitos) not in (10, 11):
        return "Telefone inválido (use DDD + número)"
    return None


def senha(valor):
    if not valor or len(valor) < 6:
        return "A senha deve ter pelo menos 6 caracteres"
    return None


def inteiro_positivo(valor, campo):
    if not isinstance(valor, int) or isinstance(valor, bool) or valor <= 0:
        return f"{campo} deve ser um número inteiro maior que zero"
    return None


def carga(valor):
    if not isinstance(valor, (int, float)) or isinstance(valor, bool) or valor < 0:
        return "Carga deve ser um número maior ou igual a zero"
    return None


def intervalo(valor, minimo, maximo, campo):
    if not isinstance(valor, (int, float)) or isinstance(valor, bool) or not (minimo <= valor <= maximo):
        return f"{campo} deve estar entre {minimo} e {maximo}"
    return None


def data(valor):
    try:
        datetime.strptime(valor, "%Y-%m-%d")
        return None
    except (TypeError, ValueError):
        return "Data inválida (use AAAA-MM-DD)"
