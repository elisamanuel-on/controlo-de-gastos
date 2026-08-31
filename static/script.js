// ============================================
// CONTROLO DE GASTOS — script.js
// Fala com a API (/api/movimentos, /api/resumo) via fetch.
// ============================================

const CATEGORIAS = {
    despesa: ['Alimentação', 'Transporte', 'Casa', 'Saúde', 'Lazer', 'Educação', 'Outros'],
    receita: ['Salário', 'Freelance', 'Outros']
};

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
    const resposta = await fetch('/api/resumo');
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
    const resposta = await fetch('/api/movimentos');
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
    await fetch(`/api/movimentos/${id}`, { method: 'DELETE' });
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
            const resposta = await fetch('/api/movimentos', {
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

document.addEventListener('DOMContentLoaded', () => {
    const aviso = document.getElementById('avisoDemo');
    if (aviso) aviso.hidden = false;

    preencherCategorias();
    configurarFormulario();
    carregarMovimentos();
    carregarResumo();
});