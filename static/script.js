// ============================================
// CONTROLO DE GASTOS — script.js
// Fala com a API (/api/movimentos, /api/resumo, /api/auth/...) via fetch.
// ============================================

const CATEGORIAS = {
    despesa: ['Alimentação', 'Transporte', 'Casa', 'Saúde', 'Lazer', 'Educação', 'Outros'],
    receita: ['Salário', 'Freelance', 'Outros']
};

const CHAVE_TOKEN = 'gastos_token';

function obterToken() {
    return localStorage.getItem(CHAVE_TOKEN);
}

function guardarToken(token) {
    localStorage.setItem(CHAVE_TOKEN, token);
}

function limparToken() {
    localStorage.removeItem(CHAVE_TOKEN);
}

// Wrapper à volta do fetch que junta sempre o cabeçalho de autenticação, e
// que trata uma resposta 401 (token inválido ou expirado) mostrando o ecrã
// de login outra vez.
async function pedidoAutenticado(url, opcoes = {}) {
    const token = obterToken();
    const cabecalhos = Object.assign({}, opcoes.headers, {
        'Authorization': `Bearer ${token}`,
    });
    const resposta = await fetch(url, Object.assign({}, opcoes, { headers: cabecalhos }));
    if (resposta.status === 401) {
        limparToken();
        mostrarAuth();
        throw new Error('Sessão expirada');
    }
    return resposta;
}

function mostrarApp(nomeUtilizador) {
    document.getElementById('authEcra').hidden = true;
    document.getElementById('appConteudo').hidden = false;
    const rotulo = document.getElementById('utilizadorAtual');
    const btnSair = document.getElementById('btnSair');
    if (rotulo) {
        rotulo.hidden = false;
        rotulo.textContent = nomeUtilizador ? `Olá, ${nomeUtilizador}` : '';
    }
    if (btnSair) btnSair.hidden = false;
}

function mostrarAuth() {
    document.getElementById('authEcra').hidden = false;
    document.getElementById('appConteudo').hidden = true;
    const rotulo = document.getElementById('utilizadorAtual');
    const btnSair = document.getElementById('btnSair');
    if (rotulo) rotulo.hidden = true;
    if (btnSair) btnSair.hidden = true;
}

async function verificarSessao() {
    const token = obterToken();
    if (!token) {
        mostrarAuth();
        return;
    }
    try {
        const resposta = await pedidoAutenticado('/api/auth/eu');
        if (!resposta.ok) throw new Error('Sessão inválida');
        const utilizador = await resposta.json();
        mostrarApp(utilizador.nome);
        iniciarApp();
    } catch (err) {
        mostrarAuth();
    }
}

function formatarMoeda(valor) {
    return new Intl.NumberFormat('pt-PT', { style: 'currency', currency: 'EUR' }).format(valor);
}

function formatarData(isoData) {
    const [ano, mes, dia] = isoData.split('-');
    return `${dia}/${mes}/${ano}`;
}

function preencherCategorias() {
    const tipoSelect = document.getElementById('tipo');
    const categoriaSelect = document.getElementById('categoria');

    function atualizar() {
        const lista = CATEGORIAS[tipoSelect.value] || [];
        categoriaSelect.innerHTML = lista.map(c => `<option value="${c}">${c}</option>`).join('');
    }

    tipoSelect.addEventListener('change', atualizar);
    atualizar();
}

async function carregarResumo() {
    const resposta = await pedidoAutenticado('/api/resumo');
    const dados = await resposta.json();

    document.getElementById('valorSaldo').textContent = formatarMoeda(dados.saldo);
    document.getElementById('valorReceitas').textContent = formatarMoeda(dados.total_receitas);
    document.getElementById('valorDespesas').textContent = formatarMoeda(dados.total_despesas);

    const container = document.getElementById('categoriasContainer');
    if (!dados.por_categoria.length) {
        container.innerHTML = '<p class="vazio">Sem despesas ainda.</p>';
        return;
    }
    const maiorTotal = Math.max(...dados.por_categoria.map(c => c.total));
    container.innerHTML = dados.por_categoria.map(c => `
        <div class="categoria-linha">
            <div class="categoria-topo">
                <span>${c.categoria}</span>
                <span>${formatarMoeda(c.total)}</span>
            </div>
            <div class="categoria-barra-fundo">
                <div class="categoria-barra" style="width:${(c.total / maiorTotal * 100).toFixed(0)}%"></div>
            </div>
        </div>
    `).join('');
}

async function carregarMovimentos() {
    const resposta = await pedidoAutenticado('/api/movimentos');
    const dados = await resposta.json();

    const container = document.getElementById('movimentosContainer');
    if (!dados.length) {
        container.innerHTML = '<p class="vazio">Ainda não há movimentos. Adiciona o primeiro!</p>';
        return;
    }

    container.innerHTML = dados.map(m => `
        <div class="movimento-item" data-id="${m.id}">
            <div class="movimento-info">
                <span class="movimento-desc">${m.descricao}</span>
                <span class="movimento-meta">${m.categoria} · ${formatarData(m.data)}</span>
            </div>
            <span class="movimento-valor ${m.tipo}">${m.tipo === 'despesa' ? '-' : '+'}${formatarMoeda(m.valor)}</span>
            <button class="btn-apagar" title="Apagar" data-id="${m.id}">×</button>
        </div>
    `).join('');

    container.querySelectorAll('.btn-apagar').forEach(btn => {
        btn.addEventListener('click', () => apagarMovimento(btn.dataset.id));
    });
}

async function apagarMovimento(id) {
    await pedidoAutenticado(`/api/movimentos/${id}`, { method: 'DELETE' });
    await Promise.all([carregarMovimentos(), carregarResumo()]);
}

function configurarFormulario() {
    const form = document.getElementById('formMovimento');
    const feedback = document.getElementById('feedback');
    const botao = form.querySelector('.btn-adicionar');

    // Data por omissão: hoje
    document.getElementById('data').value = new Date().toISOString().slice(0, 10);

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const payload = {
            descricao: document.getElementById('descricao').value.trim(),
            valor: parseFloat(document.getElementById('valor').value),
            tipo: document.getElementById('tipo').value,
            categoria: document.getElementById('categoria').value,
            data: document.getElementById('data').value
        };

        if (!payload.descricao || !payload.valor || payload.valor <= 0) {
            feedback.className = 'feedback erro';
            feedback.textContent = 'Preenche a descrição e um valor válido.';
            return;
        }

        botao.disabled = true;
        try {
            const resposta = await pedidoAutenticado('/api/movimentos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!resposta.ok) throw new Error('Falha ao guardar');

            feedback.className = 'feedback sucesso';
            feedback.textContent = 'Movimento adicionado!';
            form.reset();
            document.getElementById('data').value = new Date().toISOString().slice(0, 10);
            preencherCategorias();

            await Promise.all([carregarMovimentos(), carregarResumo()]);
        } catch (err) {
            feedback.className = 'feedback erro';
            feedback.textContent = 'Não foi possível guardar. Tenta novamente.';
        } finally {
            botao.disabled = false;
            setTimeout(() => { feedback.textContent = ''; }, 3000);
        }
    });
}

function iniciarApp() {
    const aviso = document.getElementById('avisoDemo');
    if (aviso) aviso.hidden = false;

    preencherCategorias();
    configurarFormulario();
    carregarMovimentos();
    carregarResumo();
}

function configurarAuth() {
    const abas = document.querySelectorAll('.auth-aba');
    const formLogin = document.getElementById('formLogin');
    const formRegisto = document.getElementById('formRegisto');

    abas.forEach(aba => {
        aba.addEventListener('click', () => {
            abas.forEach(a => a.classList.remove('ativa'));
            aba.classList.add('ativa');
            const alvo = aba.dataset.aba;
            formLogin.hidden = alvo !== 'login';
            formRegisto.hidden = alvo !== 'registo';
        });
    });

    formLogin.addEventListener('submit', async (e) => {
        e.preventDefault();
        const feedback = document.getElementById('feedbackLogin');
        feedback.textContent = '';

        const corpo = new URLSearchParams();
        corpo.set('username', document.getElementById('loginEmail').value.trim());
        corpo.set('password', document.getElementById('loginSenha').value);

        try {
            const resposta = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: corpo,
            });
            if (!resposta.ok) {
                const erro = await resposta.json().catch(() => ({}));
                throw new Error(erro.detail || 'Email ou palavra-passe incorretos');
            }
            const dados = await resposta.json();
            guardarToken(dados.access_token);
            formLogin.reset();
            await verificarSessao();
        } catch (err) {
            feedback.className = 'feedback erro';
            feedback.textContent = err.message;
        }
    });

    formRegisto.addEventListener('submit', async (e) => {
        e.preventDefault();
        const feedback = document.getElementById('feedbackRegisto');
        feedback.textContent = '';

        const payload = {
            nome: document.getElementById('registoNome').value.trim(),
            email: document.getElementById('registoEmail').value.trim(),
            senha: document.getElementById('registoSenha').value,
        };

        try {
            const resposta = await fetch('/api/auth/registar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!resposta.ok) {
                const erro = await resposta.json().catch(() => ({}));
                throw new Error(erro.detail || 'Não foi possível criar a conta');
            }
            const dados = await resposta.json();
            guardarToken(dados.access_token);
            formRegisto.reset();
            await verificarSessao();
        } catch (err) {
            feedback.className = 'feedback erro';
            feedback.textContent = err.message;
        }
    });

    document.getElementById('btnDemo').addEventListener('click', () => {
        document.getElementById('loginEmail').value = 'demo@controlo-de-gastos.app';
        document.getElementById('loginSenha').value = 'demo12345';
        formLogin.requestSubmit();
    });

    document.getElementById('btnSair').addEventListener('click', () => {
        limparToken();
        mostrarAuth();
    });
}

document.addEventListener('DOMContentLoaded', () => {
    configurarAuth();
    verificarSessao();
});