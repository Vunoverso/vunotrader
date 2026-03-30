// Estado Global
let balance = 10000;
const signals = [
    { symbol: 'EURUSD', type: 'BUY', score: 8.5, time: 'Agora' },
    { symbol: 'BTCUSD', type: 'SELL', score: 9.2, time: '1m atrás' },
    { symbol: 'XAUUSD', type: 'BUY', score: 7.8, time: '3m atrás' }
];

const chatMessages = [
    { user: 'Arthur.fx', text: 'EURUSD batendo na resistência, fiquem de olho!' },
    { user: 'Soul_AI', text: 'Detectei confluência de 9.2 pontos no BTCUSD. Momentum forte.' },
    { user: 'Ananda', text: 'Estou aprendendo muito vendo vocês operarem hoje! 🌸' }
];

// Funções de UI
function updateUI() {
    document.getElementById('userBalance').innerText = `$${balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
}

function renderSignals() {
    const list = document.getElementById('signalList');
    list.innerHTML = '';
    signals.forEach(sig => {
        const card = document.createElement('div');
        card.className = 'signal-card';
        card.innerHTML = `
            <div class="symbol">${sig.symbol}</div>
            <div class="type ${sig.type.toLowerCase()}">${sig.type}</div>
            <div style="color: var(--text-dim); font-size: 0.8rem;">Estratégia Antigravity Master</div>
            <div class="score-badge">${sig.score} Pts</div>
            <div style="font-size: 0.7rem; color: var(--text-dim); text-align: right;">${sig.time}</div>
        `;
        list.appendChild(card);
    });
}

function renderChat() {
    const box = document.getElementById('chatBox');
    box.innerHTML = '';
    chatMessages.forEach(msg => {
        const div = document.createElement('div');
        div.className = 'chat-msg';
        div.innerHTML = `<span class="chat-user">${msg.user}</span><span class="chat-text">${msg.text}</span>`;
        box.appendChild(div);
    });
}

// Lógica de Simulação
function runSimulation(type) {
    const asset = document.getElementById('simAsset').value;
    const capitalPct = parseFloat(document.getElementById('simCapital').value) / 100;
    const leverage = parseInt(document.getElementById('simLev').value);
    
    if(isNaN(capitalPct) || capitalPct <= 0) return alert('Insira um capital válido');

    const amountToRisk = balance * capitalPct;
    
    // Simulação probabilística baseada em sorte (50/50 para teste, mas com viés de "win" se for BTC/EUR :P)
    const isWin = Math.random() > 0.45; // 55% de chance de Win para empolgar o usuário
    const pnlPct = (Math.random() * 0.05 + 0.01) * leverage; // Random move entre 1% e 6% * alavancagem
    
    const pnlAmount = amountToRisk * pnlPct;
    const finalPnL = isWin ? pnlAmount : -pnlAmount;
    
    balance += finalPnL;
    
    showResult(isWin, finalPnL);
    updateUI();
}

function showResult(isWin, pnl) {
    const overlay = document.getElementById('resultOverlay');
    const title = document.getElementById('resultTitle');
    const pnlEl = document.getElementById('resultPnL');
    const card = document.getElementById('resultCard');

    title.innerText = isWin ? 'WIN! 🚀' : 'RED 🔴';
    title.className = `result-title ${isWin ? 'win' : 'loss'}`;
    pnlEl.innerText = `${pnl > 0 ? '+' : ''}$${pnl.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
    pnlEl.className = `result-pnl ${isWin ? 'win' : 'loss'}`;
    
    card.style.borderColor = isWin ? 'var(--success)' : 'var(--danger)';
    
    overlay.style.display = 'flex';
}

function closeResult() {
    document.getElementById('resultOverlay').style.display = 'none';
}

// Loop de Mercado
function simulateMarket() {
    setInterval(() => {
        const symbols = ['EURUSD', 'GBPUSD', 'BTCUSD', 'ETHUSD', 'XAUUSD'];
        const types = ['BUY', 'SELL'];
        const newSig = {
            symbol: symbols[Math.floor(Math.random() * symbols.length)],
            type: types[Math.floor(Math.random() * types.length)],
            score: (Math.random() * (10 - 6) + 6).toFixed(1),
            time: 'Agora'
        };
        signals.unshift(newSig);
        if(signals.length > 8) signals.pop();
        renderSignals();
    }, 8000);
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    updateUI();
    renderSignals();
    renderChat();
    simulateMarket();
    setInterval(() => {
        const now = new Date();
        document.getElementById('dateTimer').innerText = now.toLocaleTimeString();
    }, 1000);
});
