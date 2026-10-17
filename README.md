# Academia - Gestão de Treinos (MVP)

Sistema web para gerenciar alunos, professores, exercícios, fichas de treino, registro de treinos,
avaliações físicas e dashboard de evolução. Stack: **Python + Flask + SQLite + JWT + Chart.js**.

## Como rodar no VS Code
```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
flask run --debug
```
Abra http://127.0.0.1:5000 — o banco (`academia.db`) é criado automaticamente.

**Login inicial:** `admin@academia.com` / `admin123`

## Perfis
| Perfil | Pode |
|---|---|
| admin | tudo: usuários, exercícios, fichas, avaliações, planos e matrículas |
| professor | cadastrar seus alunos, exercícios, fichas e avaliações; ver evolução dos seus alunos |
| aluno | ver suas fichas, registrar treinos, ver avaliações e dashboard |

## Testes
```bash
pytest tests/unit tests/integration -v     # unitários e integração (não precisam do servidor)
pytest tests/selenium -v                   # UI: rode `flask run` em outro terminal antes
```
Sem pytest: `python -m unittest discover -s tests -t .`

## Relação com a atividade avaliativa
| Item | Onde está |
|---|---|
| 1 Login | `POST /api/auth/login` (JWT) e tela de login |
| 2 Admin | perfil `admin` e decorator `@auth("admin")` |
| 3 / 4 Cadastro / remoção de usuário | `routes/usuarios.py` |
| 5 / 6 Cadastro / remoção de exercícios (3 tipos) | `routes/exercicios.py` |
| 7 Compra e venda | venda de planos: `POST /api/matriculas` |
| 8 Atualização de estoque | atualização do histórico: `POST /api/treinos` |
| 9 Unitário / integração | `tests/unit`, `tests/integration` |
| 10-12 Sistema, aceitação, alfa/beta | roteiro manual com o fluxo completo (ver `TestFluxoCompleto`) |
| 13 Regressão | reexecutar toda a suíte após cada mudança |
| 14 Automação Selenium | `tests/selenium/test_ui.py` |

## Fora do MVP
Notificações/lembretes e relatórios em PDF (ficam para evoluir no TCC).
