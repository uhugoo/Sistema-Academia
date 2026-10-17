let token = localStorage.getItem('token'), me = JSON.parse(localStorage.getItem('me') || 'null'), modoCadastro = false, graficos = [], FICHAS = [], EXERCICIOS = [];
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const ABAS = {
  admin: ['usuarios','exercicios','fichas','avaliacoes','dashboard','planos'],
  professor: ['usuarios','exercicios','fichas','avaliacoes','dashboard'],
  aluno: ['fichas','treinos','avaliacoes','dashboard']
};
const NOMES = {usuarios:'Usuários',exercicios:'Exercícios',fichas:'Fichas',treinos:'Treinos',avaliacoes:'Avaliações',dashboard:'Dashboard',planos:'Planos'};
const CARREGAR = {usuarios:carregarUsuarios,exercicios:carregarExercicios,fichas:carregarFichas,treinos:carregarTreinos,avaliacoes:carregarAvaliacoes,dashboard:carregarDashboard,planos:carregarPlanos};

function aviso(txt, erro) {
  const m = $('msg'); m.textContent = txt; m.className = erro ? 'err' : 'ok';
  setTimeout(() => m.className = 'oculto', 3500);
}
async function api(metodo, url, corpo) {
  const r = await fetch(url, {method: metodo, headers: {'Content-Type':'application/json', ...(token ? {Authorization:'Bearer '+token} : {})}, body: corpo ? JSON.stringify(corpo) : undefined});
  const d = await r.json().catch(() => ({}));
  if (r.status === 401 && token) { sair(); }
  if (!r.ok) throw new Error(d.erro || 'Erro ' + r.status);
  return d;
}
const tentar = fn => async (...a) => { try { await fn(...a); } catch (e) { aviso(e.message, true); } };

function alternarCadastro() {
  modoCadastro = !modoCadastro;
  $('campos-cadastro').classList.toggle('oculto', !modoCadastro);
  $('titulo-login').textContent = modoCadastro ? 'Criar conta' : 'Entrar';
  $('btn-login').textContent = modoCadastro ? 'Cadastrar' : 'Entrar';
  $('alternar').textContent = modoCadastro ? 'Já tenho conta' : 'Criar conta de aluno';
  $('msg-login').textContent = '';
}
async function entrar() {
  $('msg-login').textContent = '';
  try {
    if (modoCadastro) {
      await api('POST', '/api/auth/registro', {nome_completo: $('nome').value, telefone: telefoneCompleto($('ddd').value, $('telefone').value), email: $('email').value, senha: $('senha').value});
      aviso('Conta criada! Faça login.'); alternarCadastro(); return;
    }
    const d = await api('POST', '/api/auth/login', {email: $('email').value, senha: $('senha').value});
    token = d.token; me = d;
    localStorage.setItem('token', token); localStorage.setItem('me', JSON.stringify(me));
    iniciar();
  } catch (e) { $('msg-login').textContent = e.message; }
}
function sair() {
  token = null; me = null; localStorage.clear();
  $('painel').classList.add('oculto'); $('btn-sair').classList.add('oculto');
  $('tela-login').classList.remove('oculto'); $('usuario-logado').textContent = '';
}
function iniciar() {
  $('tela-login').classList.add('oculto'); $('painel').classList.remove('oculto'); $('btn-sair').classList.remove('oculto');
  $('usuario-logado').textContent = `${me.nome} (${me.perfil})`;
  $('u-perfil').classList.toggle('oculto', me.perfil !== 'admin');
  ['form-ficha','form-avaliacao'].forEach(id => $(id).classList.toggle('oculto', me.perfil === 'aluno'));
  $('d-aluno').classList.toggle('oculto', me.perfil === 'aluno');
  $('menu').innerHTML = ABAS[me.perfil].map(a => `<button id="menu-${a}" onclick="abrir('${a}')">${NOMES[a]}</button>`).join('');
  abrir(ABAS[me.perfil][0]);
}
const abrir = tentar(async aba => {
  document.querySelectorAll('.aba').forEach(e => e.classList.add('oculto'));
  $('aba-' + aba).classList.remove('oculto');
  document.querySelectorAll('#menu button').forEach(b => b.classList.toggle('ativa', b.id === 'menu-' + aba));
  await CARREGAR[aba]();
});
async function preencherAlunos(...ids) {
  const alunos = await api('GET', '/api/usuarios?perfil=aluno');
  ids.forEach(id => $(id).innerHTML = alunos.map(a => `<option value="${a.id}">${esc(a.nome_completo)}</option>`).join(''));
}

// ---- Telefone: junta DDD + número (só dígitos) e valida antes de enviar
function telefoneCompleto(ddd, numero) {
  ddd = ddd.replace(/\D/g, ''); numero = numero.replace(/\D/g, '');
  if (ddd.length !== 2) throw new Error('Informe o DDD com 2 dígitos');
  if (numero.length < 8 || numero.length > 9) throw new Error('Telefone deve ter 8 ou 9 dígitos');
  return ddd + numero;
}
document.addEventListener('input', e => { if (e.target.classList.contains('so-numeros')) e.target.value = e.target.value.replace(/\D/g, ''); });

// ---- Usuários
async function carregarUsuarios() {
  const us = await api('GET', '/api/usuarios?q=' + encodeURIComponent($('u-busca').value));
  $('tb-usuarios').innerHTML = us.map(u => `<tr><td>${u.id}</td><td>${esc(u.nome_completo)}</td><td>${esc(u.email)}</td><td>${esc(u.telefone)}</td><td>${u.perfil}</td>
    <td>${me.perfil === 'admin' && u.id !== me.id ? `<button class="del" onclick="removerUsuario(${u.id})">Remover</button>` : ''}</td></tr>`).join('');
}
const addUsuario = tentar(async () => {
  await api('POST', '/api/usuarios', {nome_completo: $('u-nome').value, email: $('u-email').value, telefone: telefoneCompleto($('u-ddd').value, $('u-tel').value), senha: $('u-senha').value, perfil: me.perfil === 'admin' ? $('u-perfil').value : 'aluno'});
  ['u-nome','u-email','u-ddd','u-tel','u-senha'].forEach(i => $(i).value = ''); aviso('Usuário cadastrado'); carregarUsuarios();
});
const removerUsuario = tentar(async id => { if (!confirm('Remover usuário?')) return; await api('DELETE', '/api/usuarios/' + id); aviso('Usuário removido'); carregarUsuarios(); });

// ---- Exercícios
async function carregarExercicios() {
  const grupos = await api('GET', '/api/grupos');
  const sel = $('e-grupo'), atual = sel.value;
  sel.innerHTML = '<option value="">Sem grupo</option>' + grupos.map(g => `<option value="${g.id}">${esc(g.nome)}</option>`).join(''); sel.value = atual;
  $('form-exercicio').classList.toggle('oculto', me.perfil === 'aluno');
  const ex = await api('GET', `/api/exercicios?q=${encodeURIComponent($('e-busca').value)}&tipo=${$('e-filtro').value}`);
  $('tb-exercicios').innerHTML = ex.map(e => `<tr><td>${esc(e.nome)}</td><td>${e.tipo}</td><td>${esc(e.grupo || '-')}</td>
    <td>${me.perfil !== 'aluno' ? `<button class="del" onclick="removerExercicio(${e.id})">Remover</button>` : ''}</td></tr>`).join('');
}
const addExercicio = tentar(async () => {
  await api('POST', '/api/exercicios', {nome: $('e-nome').value, tipo: $('e-tipo').value, grupo_muscular_id: $('e-grupo').value ? +$('e-grupo').value : null});
  $('e-nome').value = ''; aviso('Exercício cadastrado'); carregarExercicios();
});
const addGrupo = tentar(async () => { await api('POST', '/api/grupos', {nome: $('g-nome').value}); $('g-nome').value = ''; aviso('Grupo criado'); carregarExercicios(); });
const removerExercicio = tentar(async id => { if (!confirm('Remover exercício?')) return; await api('DELETE', '/api/exercicios/' + id); aviso('Exercício removido'); carregarExercicios(); });

// ---- Fichas
async function carregarFichas() {
  if (me.perfil !== 'aluno') { await preencherAlunos('f-aluno'); EXERCICIOS = await api('GET', '/api/exercicios'); if (!$('f-itens').children.length) addLinhaFicha(); }
  FICHAS = await api('GET', '/api/fichas');
  $('lista-fichas').innerHTML = FICHAS.map(f => `<div class="card"><strong>${esc(f.nome)}</strong> - ${esc(f.aluno)} (${f.data_inicio}) ${f.ativa ? '' : '<em>[inativa]</em>'}
    ${me.perfil !== 'aluno' ? `<button class="del" onclick="removerFicha(${f.id})">Excluir</button>` : ''}
    <ul>${f.exercicios.map(e => `<li>${esc(e.nome)}: ${e.series}x${e.repeticoes} - ${e.carga_kg} kg</li>`).join('')}</ul></div>`).join('') || '<p>Nenhuma ficha.</p>';
}
function addLinhaFicha() {
  const d = document.createElement('div'); d.className = 'linha linha-ficha';
  d.innerHTML = `<select>${EXERCICIOS.map(e => `<option value="${e.id}">${esc(e.nome)}</option>`).join('')}</select>
    <input type="number" min="1" placeholder="Séries" style="width:80px"><input type="number" min="1" placeholder="Reps" style="width:80px"><input type="number" min="0" step="0.5" placeholder="Carga kg" style="width:90px">`;
  $('f-itens').appendChild(d);
}
const criarFicha = tentar(async () => {
  const itens = [...document.querySelectorAll('.linha-ficha')].map(l => { const [s, a, b, c] = l.querySelectorAll('select,input'); return {exercicio_id: +s.value, series: +a.value, repeticoes: +b.value, carga_kg: c.value === '' ? -1 : +c.value}; });
  await api('POST', '/api/fichas', {aluno_id: +$('f-aluno').value, nome: $('f-nome').value, exercicios: itens});
  $('f-nome').value = ''; $('f-itens').innerHTML = ''; addLinhaFicha(); aviso('Ficha criada'); carregarFichas();
});
const removerFicha = tentar(async id => { if (!confirm('Excluir ficha?')) return; await api('DELETE', '/api/fichas/' + id); carregarFichas(); });

// ---- Treinos (aluno)
async function carregarTreinos() {
  FICHAS = (await api('GET', '/api/fichas')).filter(f => f.ativa);
  $('t-ficha').innerHTML = FICHAS.map(f => `<option value="${f.id}">${esc(f.nome)}</option>`).join('');
  montarTreino();
  const ts = await api('GET', '/api/treinos');
  $('tb-treinos').innerHTML = ts.map(t => `<tr><td>${t.data}</td><td>${esc(t.ficha || '-')}</td><td>${t.duracao_min} min</td><td>${t.volume}</td></tr>`).join('');
}
function montarTreino() {
  const f = FICHAS.find(x => x.id == $('t-ficha').value);
  $('t-itens').innerHTML = f ? f.exercicios.map(e => `<div class="linha item-treino" data-ex="${e.exercicio_id}" data-series="${e.series}">
    <span style="min-width:180px">${esc(e.nome)} (${e.series} séries)</span>
    <input type="number" min="1" value="${e.repeticoes}" title="Repetições" style="width:80px"><input type="number" min="0" step="0.5" value="${e.carga_kg}" title="Carga kg" style="width:90px"></div>`).join('') : '<p>Sem fichas ativas.</p>';
}
const registrarTreino = tentar(async () => {
  const series = [];
  document.querySelectorAll('.item-treino').forEach(l => { const [r, c] = l.querySelectorAll('input');
    for (let n = 1; n <= +l.dataset.series; n++) series.push({exercicio_id: +l.dataset.ex, serie_num: n, repeticoes: +r.value, carga_kg: +c.value}); });
  await api('POST', '/api/treinos', {ficha_id: +$('t-ficha').value, duracao_min: +$('t-duracao').value, series});
  $('t-duracao').value = ''; aviso('Treino registrado!'); carregarTreinos();
});

// ---- Avaliações
async function carregarAvaliacoes() {
  if (me.perfil !== 'aluno') await preencherAlunos('a-aluno');
  const av = await api('GET', '/api/avaliacoes');
  $('tb-avaliacoes').innerHTML = av.map(a => `<tr><td>${a.data}</td><td>${esc(a.aluno)}</td><td>${a.peso} kg</td><td>${a.altura} m</td><td>${a.percentual_gordura}%</td><td>${a.imc}</td></tr>`).join('');
}
const addAvaliacao = tentar(async () => {
  await api('POST', '/api/avaliacoes', {aluno_id: +$('a-aluno').value, peso: +$('a-peso').value, altura: +$('a-altura').value, percentual_gordura: +$('a-gordura').value});
  aviso('Avaliação registrada'); carregarAvaliacoes();
});

// ---- Dashboard
async function carregarDashboard() {
  let id = me.id;
  if (me.perfil !== 'aluno') { if (!$('d-aluno').options.length) await preencherAlunos('d-aluno'); id = $('d-aluno').value; if (!id) { $('d-resumo').textContent = 'Nenhum aluno cadastrado.'; return; } }
  const d = await api('GET', '/api/dashboard/' + id);
  $('d-resumo').textContent = `Treinos: ${d.total_treinos} | Tempo total: ${d.tempo_total_min} min | Maior carga: ${d.carga_maxima} kg`;
  graficos.forEach(g => g.destroy());
  const linha = (canvas, rotulo, labels, dados) => new Chart($(canvas), {type: 'line', data: {labels, datasets: [{label: rotulo, data: dados, borderColor: '#2563eb', tension: .25}]}});
  graficos = [
    linha('grafico-peso', 'Peso (kg)', d.avaliacoes.map(a => a.data), d.avaliacoes.map(a => a.peso)),
    linha('grafico-volume', 'Volume por treino (kg)', d.treinos.map(t => t.data), d.treinos.map(t => t.volume))
  ];
}

// ---- Planos (admin)
async function carregarPlanos() {
  await preencherAlunos('p-aluno');
  const planos = await api('GET', '/api/planos');
  $('p-plano').innerHTML = planos.map(p => `<option value="${p.id}">${esc(p.nome)} - R$ ${p.valor.toFixed(2)}</option>`).join('');
  const ms = await api('GET', '/api/matriculas');
  $('tb-matriculas').innerHTML = ms.map(m => `<tr><td>${esc(m.aluno)}</td><td>${esc(m.plano)}</td><td>${m.data_inicio}</td><td>${m.data_fim}</td><td>R$ ${m.valor_pago.toFixed(2)}</td></tr>`).join('');
}
const matricular = tentar(async () => { await api('POST', '/api/matriculas', {aluno_id: +$('p-aluno').value, plano_id: +$('p-plano').value}); aviso('Matrícula realizada'); carregarPlanos(); });

if (token && me) iniciar();
$('senha').addEventListener('keydown', e => { if (e.key === 'Enter') entrar(); });