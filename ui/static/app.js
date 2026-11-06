/**
 * PROJECT AVI // ALPHA COCKPIT CONTROLLER
 * Real-time connection to FTMO MT5 $100k Account, Agent 1 Chat, Agent 2 Thinking Stream, and Agent 3 Swarm.
 */

// ── Clock ──
const liveClock = document.getElementById('liveClock');
function updateClock() {
  const now = new Date();
  liveClock.textContent = now.toLocaleTimeString('en-US', { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

// ── Navigation Tabs ──
const titles = {
  tabThinking: { title: "Agent 2 // Multi-Timeframe Thinking Core", sub: "Enforcing 1-Hour Trend Alignment, ATR Volatility Discipline, and Breakeven Trailing Stops." },
  tabFTMO: { title: "FTMO $100,000 Challenge // Live MT5 Monitor", sub: "Real-time tracking of account equity, daily loss limit (5%), and pass target (+10%)." },
  tabChat: { title: "Agent 1 // Conversational Assistant", sub: "Natural language query engine integrated with live thinking, swarm champions, and FTMO account." },
  tabSwarm: { title: "Agent 3 // Swarm Strategy Tournament", sub: "Genetic chromosomes backtested on live Binance data with 0.05% taker fee friction." },
  tabMacro: { title: "Macro Catalyst Radar // Liquidation & Funding", sub: "Live Binance USD-M perpetual funding rates and systemic macro tail-risk filters." },
  tabMemory: { title: "Dual Neo4j Knowledge Graph // Associative Memory", sub: "Inspection view of Cypher nodes, hypotheses, and multi-hop market relationships." },
  tabSpecs: { title: "Alpha Architecture // Winning Edge Constraints", sub: "Specifications for multi-timeframe laws, friction modeling, and FTMO risk rules." },
  tabReports: { title: "30-Min Overnight Reports // Executive Ledger", sub: "Chronological 30-minute audit snapshots: live FTMO equity, micro-scalp executions, and cognitive decisions." }
};

document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));

    item.classList.add('active');
    const tabId = item.getAttribute('data-tab');
    const panel = document.getElementById(tabId);
    if (panel) panel.classList.add('active');

    const meta = titles[tabId];
    if (meta) {
      document.getElementById('currentViewTitle').textContent = meta.title;
      document.getElementById('currentViewSubtitle').textContent = meta.sub;
    }
  });
});

// ── FTMO MT5 Real-Time Polling ──
async function fetchFTMO() {
  try {
    const res = await fetch('/api/ftmo');
    if (!res.ok) return;
    const data = await res.json();

    const topEq = document.getElementById('ftmoTopEquity');
    if (topEq) topEq.textContent = `$${data.current_equity.toLocaleString('en-US', {minimumFractionDigits: 2})}`;

    const cardEq = document.getElementById('cardFtmoEquity');
    if (cardEq) cardEq.textContent = `$${data.current_equity.toLocaleString('en-US', {minimumFractionDigits: 2})}`;

    const cardDL = document.getElementById('cardFtmoDailyLoss');
    if (cardDL) {
      cardDL.textContent = `${data.daily_drawdown_pct.toFixed(2)}%`;
      cardDL.className = data.daily_drawdown_pct > 2.5 ? 'ribbon-value text-danger' : 'ribbon-value';
    }

    const cardTL = document.getElementById('cardFtmoTotalLoss');
    if (cardTL) {
      cardTL.textContent = `${data.total_drawdown_pct.toFixed(2)}%`;
      cardTL.className = data.total_drawdown_pct > 5.0 ? 'ribbon-value text-danger' : 'ribbon-value';
    }

    const cardTarg = document.getElementById('cardFtmoTarget');
    if (cardTarg) {
      const pfx = data.profit_progress_pct >= 0 ? '+' : '';
      cardTarg.textContent = `${pfx}${data.profit_progress_pct.toFixed(2)}% / +10%`;
      cardTarg.className = data.profit_progress_pct >= 0 ? 'ribbon-value text-success' : 'ribbon-value text-danger';
    }

    // View tab displays
    const dDisp = document.getElementById('ftmoDailyLossDisplay');
    if (dDisp) dDisp.textContent = `${data.daily_drawdown_pct.toFixed(2)}%`;

    const tDisp = document.getElementById('ftmoTotalLossDisplay');
    if (tDisp) tDisp.textContent = `${data.total_drawdown_pct.toFixed(2)}%`;

    const pDisp = document.getElementById('ftmoProfitDisplay');
    if (pDisp) {
      const pfx = data.profit_progress_pct >= 0 ? '+' : '';
      pDisp.textContent = `${pfx}${data.profit_progress_pct.toFixed(2)}%`;
    }

    const balText = document.getElementById('ftmoBalanceText');
    if (balText) balText.textContent = `$${data.current_balance.toLocaleString('en-US', {minimumFractionDigits: 2})} USD`;

    const loginText = document.getElementById('ftmoLoginText');
    if (loginText && data.login) loginText.textContent = `#${data.login}`;

    const govText = document.getElementById('ftmoGovStatus');
    if (govText) {
      govText.textContent = data.status;
      govText.className = data.circuit_breaker ? 'status-text text-danger' : 'status-text text-success';
    }

    const badge = document.getElementById('ftmoStatusBadge');
    if (badge) {
      badge.textContent = data.mt5_connected ? 'LIVE MT5' : 'STANDBY';
      badge.className = `badge ${data.mt5_connected ? 'success' : 'warning'}`;
    }
  } catch (err) {
    console.warn('FTMO fetch notice:', err);
  }
}

fetchFTMO();
setInterval(fetchFTMO, 3000);

// ── Agent 2: Real Live Thinking Stream Polling ──
const thinkingStreamContainer = document.getElementById('thinkingStreamContainer');
let lastThoughtCount = 0;

async function fetchLiveThinking() {
  try {
    const res = await fetch('/api/thinking');
    if (!res.ok) return;
    const data = await res.json();

    if (data.current_step) {
      document.getElementById('topbarStep').textContent = `Step ${data.current_step}`;
    }

    if (data.portfolio) {
      const p = data.portfolio;
      const openPosContainer = document.getElementById('openPositionsContainer');
      if (p.open_positions && p.open_positions.length > 0) {
        openPosContainer.innerHTML = p.open_positions.map(pos => {
          const statusBadge = pos.status === 'BREAKEVEN_LOCKED' ? '<span class="status-badge success">Breakeven Locked</span>' : (pos.status === 'TRAILING_PROFIT' ? '<span class="status-badge success">Trailing Profit</span>' : '<span class="status-badge warning">1R Risk Active</span>');
          return `
            <div class="position-item">
              <div class="pos-row-top">
                <span class="pos-symbol">${pos.symbol}</span>
                <span class="pos-side ${pos.side.toLowerCase()}">${pos.side}</span>
                ${statusBadge}
                <span class="pos-pnl ${pos.unrealized_pnl >= 0 ? 'text-success' : 'text-danger'}">
                  ${pos.unrealized_pnl >= 0 ? '+' : ''}$${pos.unrealized_pnl.toFixed(2)}
                </span>
              </div>
              <div class="pos-details">
                Entry: $${pos.entry_price.toFixed(2)} | Current SL: $${pos.sl.toFixed(2)} | TP: $${pos.tp.toFixed(2)}
              </div>
            </div>
          `;
        }).join('');
      } else {
        openPosContainer.innerHTML = '<div class="empty-state">No open positions. Risk Governor standing down in chop.</div>';
      }

      const closedTradesContainer = document.getElementById('recentTradesContainer');
      if (p.recent_trades && p.recent_trades.length > 0) {
        closedTradesContainer.innerHTML = p.recent_trades.map(t => `
          <div class="position-item">
            <div class="pos-row-top">
              <span class="pos-symbol">${t.symbol}</span>
              <span class="pos-side ${t.side.toLowerCase()}">${t.side}</span>
              <span class="pos-pnl ${t.realized_pnl >= 0 ? 'text-success' : 'text-danger'}">
                ${t.realized_pnl >= 0 ? '+' : ''}$${t.realized_pnl.toFixed(2)}
              </span>
            </div>
            <div class="pos-details">
              Exit: ${t.exit_reason} | Net: $${t.realized_pnl.toFixed(2)}
            </div>
          </div>
        `).join('');
      } else {
        closedTradesContainer.innerHTML = '<div class="empty-state">No closed trades yet.</div>';
      }
    }

    if (data.thoughts && data.thoughts.length > 0) {
      if (data.thoughts.length !== lastThoughtCount) {
        lastThoughtCount = data.thoughts.length;

        thinkingStreamContainer.innerHTML = [...data.thoughts].reverse().map(t => {
          const isExec = t.takeaway.includes('Conviction Triggered');
          const takeawayClass = isExec ? '' : 'stand-down';

          return `
            <div class="thought-card">
              <div class="thought-card-header">
                <div class="thought-card-title">
                  <span class="step-num-pill">Step ${t.step}</span>
                  <span>${t.symbol} // ${t.regime}</span>
                </div>
                <div class="thought-card-meta">${t.timestamp} UTC</div>
              </div>
              <div class="thought-monologue-content">${escapeHtml(t.monologue || t.desc)}</div>
              <div class="thought-takeaway-bar ${takeawayClass}">
                ${t.takeaway}
              </div>
            </div>
          `;
        }).join('');
      }
    }
  } catch (err) {
    console.warn('Thinking fetch notice:', err);
  }
}

function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return text.replace(/[&<>"']/g, m => map[m]);
}

fetchLiveThinking();
setInterval(fetchLiveThinking, 2500);

// ── Agent 3: Swarm Population Polling ──
async function fetchLiveSwarm() {
  try {
    const res = await fetch('/api/swarm');
    if (!res.ok) return;
    const data = await res.json();

    const badge = document.getElementById('swarmGenBadge');
    if (badge && data.generation) badge.textContent = `Gen ${data.generation}`;

    const tbody = document.getElementById('swarmTableBody');
    if (!tbody || !data.population || !data.population.length) return;

    tbody.innerHTML = data.population.map(p => {
      const isWinner = p.status === 'passed_gate' || p.expectancy > 0.10;
      const isCulled = p.status === 'culled';
      const badgeClass = isWinner ? 'success' : (isCulled ? 'danger' : 'warning');
      const badgeText = isWinner ? 'Passed Gate' : (isCulled ? 'Culled' : `Testing (Gen ${p.generation})`);
      const expColor = p.expectancy > 0 ? 'text-success font-bold' : (p.expectancy < 0 ? 'text-danger font-bold' : 'text-muted');

      return `
        <tr>
          <td><strong>${p.agent_id}</strong></td>
          <td>${p.symbol}</td>
          <td><span class="status-badge" style="background: rgba(59,130,246,0.15); color: #3b82f6;">${p.strategy_type || 'ALPHA'}</span></td>
          <td>${p.dna}</td>
          <td>${p.trades_count}</td>
          <td>${p.win_rate}%</td>
          <td>${p.profit_factor}</td>
          <td class="${expColor}">$${p.expectancy.toFixed(2)}/t</td>
          <td><span class="status-badge ${badgeClass}">${badgeText}</span></td>
        </tr>
      `;
    }).join('');

    const meta = document.getElementById('swarmPopMeta');
    if (meta) meta.textContent = `${data.population.length} Agents Active (Gen ${data.generation})`;
  } catch (err) {
    console.warn('Swarm fetch notice:', err);
  }
}

fetchLiveSwarm();
setInterval(fetchLiveSwarm, 4000);

// ── Macro Catalyst Radar Polling ──
async function fetchMacroRadar() {
  try {
    const res = await fetch('/api/macro');
    if (!res.ok) return;
    const data = await res.json();

    const riskEl = document.getElementById('macroRiskText');
    if (riskEl) {
      riskEl.textContent = `${data.risk_level}`;
      riskEl.className = data.risk_level === 'LOW_RISK' ? 'text-success' : 'text-danger';
    }

    if (data.funding_rates) {
      const btc = document.getElementById('rateBTC');
      const eth = document.getElementById('rateETH');
      const sol = document.getElementById('rateSOL');
      if (btc) btc.textContent = data.funding_rates['BTCUSDT'] || '+0.010%';
      if (eth) eth.textContent = data.funding_rates['ETHUSDT'] || '+0.005%';
      if (sol) sol.textContent = data.funding_rates['SOLUSDT'] || '+0.010%';
    }

    const scoreDisplay = document.getElementById('macroScoreDisplay');
    const verdictDisplay = document.getElementById('macroVerdictDisplay');
    const levelDisplay = document.getElementById('macroRiskLevelDisplay');
    const statusDisplay = document.getElementById('macroEventStatus');

    if (scoreDisplay) scoreDisplay.textContent = data.risk_score;
    if (verdictDisplay) verdictDisplay.textContent = data.verdict;
    if (levelDisplay) levelDisplay.textContent = data.risk_level;
    if (statusDisplay) statusDisplay.textContent = data.event_status;
  } catch (err) {
    console.warn('Macro fetch notice:', err);
  }
}

fetchMacroRadar();
setInterval(fetchMacroRadar, 6000);

// ── Agent 1: Live API Chat Interaction ──
const chatHistory = document.getElementById('chatHistory');
const chatInput = document.getElementById('chatInput');
const sendChatBtn = document.getElementById('sendChatBtn');

function appendMessage(author, text, isUser = false) {
  const row = document.createElement('div');
  row.className = `message-row ${isUser ? 'user' : 'avi'}`;
  row.innerHTML = `
    <div class="msg-avatar">${author}</div>
    <div class="msg-content"><p>${escapeHtml(text).replace(/\n/g, '<br>')}</p></div>
  `;
  chatHistory.appendChild(row);
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

async function handleSend() {
  const text = chatInput.value.trim();
  if (!text) return;

  appendMessage('YOU', text, true);
  chatInput.value = '';

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: text })
    });
    if (res.ok) {
      const data = await res.json();
      appendMessage('AVI', data.reply, false);
      return;
    }
  } catch {
  }

  appendMessage('AVI', 'Agent 1 Assistant is processing live telemetry across FTMO MT5, Agent 2, and Agent 3.', false);
}

sendChatBtn.addEventListener('click', handleSend);
chatInput.addEventListener('keydown', e => { if (e.key === 'Enter') handleSend(); });


// ── 30-Min Overnight Reports Real-Time Poller ──
async function fetchReports() {
  try {
    const res = await fetch('/api/reports');
    if (!res.ok) return;
    const data = await res.json();
    const reports = data.reports || [];

    const totalCountEl = document.getElementById('repTotalCount');
    if (totalCountEl) totalCountEl.textContent = reports.length;

    const sidebarBadge = document.getElementById('sidebarReportsBadge');
    if (sidebarBadge) sidebarBadge.textContent = `${reports.length} Snapshots`;

    const topEq = document.getElementById('repLiveEquity');
    if (topEq && data.ftmo_account && data.ftmo_account.current_equity) {
      topEq.textContent = `$${data.ftmo_account.current_equity.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    }

    const container = document.getElementById('reportsTimelineContainer');
    if (!container) return;

    if (reports.length === 0) {
      container.innerHTML = '<div class="empty-state">No overnight snapshots recorded yet. Next snapshot will log automatically at the 30-min mark.</div>';
      return;
    }

    let html = '';
    reports.forEach((snap, idx) => {
      const isLatest = idx === 0;
      const netPnl = snap.net_pnl || 0;
      const pnlClass = netPnl >= 0 ? 'text-success' : 'text-danger';
      const pnlSign = netPnl >= 0 ? '+' : '';
      const ddPct = (snap.daily_drawdown_pct || 0).toFixed(2);
      const btc = snap.prices?.BTCUSD ? `$${snap.prices.BTCUSD.toLocaleString('en-US', {minimumFractionDigits: 2})}` : 'N/A';
      const eth = snap.prices?.ETHUSD ? `$${snap.prices.ETHUSD.toLocaleString('en-US', {minimumFractionDigits: 2})}` : 'N/A';
      const sol = snap.prices?.SOLUSD ? `$${snap.prices.SOLUSD.toLocaleString('en-US', {minimumFractionDigits: 2})}` : 'N/A';
      const eur = snap.prices?.EURUSD ? `${snap.prices.EURUSD.toFixed(5)}` : 'N/A';
      const gbp = snap.prices?.GBPUSD ? `${snap.prices.GBPUSD.toFixed(5)}` : 'N/A';
      const jpy = snap.prices?.USDJPY ? `${snap.prices.USDJPY.toFixed(3)}` : 'N/A';

      const deals = snap.deals || [];
      const positions = snap.positions || [];

      html += `
        <div class="report-snapshot-card ${isLatest ? 'latest-card' : ''}">
          <div class="snap-card-header">
            <div class="snap-header-title">
              <span class="snap-badge ${isLatest ? 'badge-primary' : 'badge-neutral'}">Snapshot #${reports.length - idx}</span>
              <span class="snap-time">🕒 ${snap.timestamp_ist}</span>
              <span class="snap-utc">(${snap.timestamp_utc})</span>
              ${isLatest ? '<span class="badge live pulsing">LATEST</span>' : ''}
            </div>
            <div class="snap-header-badges">
              <span class="metric-pill">Equity: <strong>$${(snap.equity || 100000).toLocaleString('en-US', {minimumFractionDigits: 2})}</strong></span>
              <span class="metric-pill">Balance: <strong>$${(snap.balance || 100000).toLocaleString('en-US', {minimumFractionDigits: 2})}</strong></span>
              <span class="metric-pill ${pnlClass}">Net PnL: <strong>${pnlSign}$${netPnl.toFixed(2)}</strong></span>
              <span class="metric-pill">Daily DD: <strong>${ddPct}%</strong></span>
              <span class="metric-pill badge-success">${snap.governor_status || 'ARMED'}</span>
            </div>
          </div>

          <div class="snap-card-body">
            <!-- Market Prices Row: 3 Crypto + 3 Forex -->
            <div class="snap-market-row">
              <div class="market-pill">
                <span class="pill-sym">BTC/USD</span>
                <span class="pill-val">${btc}</span>
              </div>
              <div class="market-pill">
                <span class="pill-sym">ETH/USD</span>
                <span class="pill-val">${eth}</span>
              </div>
              <div class="market-pill">
                <span class="pill-sym">SOL/USD</span>
                <span class="pill-val">${sol}</span>
              </div>
              <div class="market-pill">
                <span class="pill-sym">EUR/USD</span>
                <span class="pill-val">${eur}</span>
              </div>
              <div class="market-pill">
                <span class="pill-sym">GBP/USD</span>
                <span class="pill-val">${gbp}</span>
              </div>
              <div class="market-pill">
                <span class="pill-sym">USD/JPY</span>
                <span class="pill-val">${jpy}</span>
              </div>
              <div class="market-pill scalp-pill">
                <span class="pill-sym">Scalp Profile</span>
                <span class="pill-val text-warning">Dynamic 5m ATR (+$60 TP / -$35 SL)</span>
              </div>
            </div>

            <!-- Cognitive Audit Box -->
            <div class="snap-cog-box">
              <div class="cog-box-header">
                <span class="cog-title">🧠 Agent 2 Cognitive & Dialectical Audit:</span>
                <span class="cog-asset">${snap.agent2?.symbol || 'BTCUSDT'} in <strong>${snap.agent2?.regime || '1h_MACRO_BULL'}</strong> (Step #${snap.agent2?.step || 0})</span>
              </div>
              <div class="cog-verdict">${snap.agent2?.takeaway || 'Standing by.'}</div>
            </div>

            <!-- Execution Logs -->
            <div class="snap-trade-section">
              <div class="trade-sec-title">FTMO MT5 Trade Execution Log (30-Minute Window):</div>
      `;

      if (deals.length === 0 && positions.length === 0) {
        html += `
              <div class="clean-trade-banner">
                <span class="banner-icon">🛡️</span>
                <span>Zero trades triggered in this window. Agent 2 preserved capital / stood down on noise. Open positions: <strong>0</strong>.</span>
              </div>
        `;
      } else {
        if (positions.length > 0) {
          html += `<div class="positions-subhead">Current Open Positions:</div>`;
          positions.forEach(p => {
            html += `
              <div class="deal-row position-row">
                <span class="deal-tag">OPEN POS #${p.ticket}</span>
                <span class="deal-sym">${p.symbol} (${p.type} ${p.volume} lots)</span>
                <span class="deal-price">Entry: $${p.price_open?.toLocaleString('en-US', {minimumFractionDigits: 2})}</span>
                <span class="deal-stops">SL: $${p.sl?.toFixed(2)} | TP: $${p.tp?.toFixed(2)}</span>
                <span class="deal-pnl ${p.profit >= 0 ? 'text-success' : 'text-danger'}">Float: $${p.profit?.toFixed(2)}</span>
              </div>
            `;
          });
        }

        if (deals.length > 0) {
          html += `<div class="positions-subhead">Executed Deals:</div>`;
          deals.forEach(d => {
            html += `
              <div class="deal-row">
                <span class="deal-tag">DEAL #${d.ticket} (Order #${d.order})</span>
                <span class="deal-sym">${d.symbol} ${d.side} ${d.volume} lots</span>
                <span class="deal-price">Fill: $${d.price?.toLocaleString('en-US', {minimumFractionDigits: 2})}</span>
                <span class="deal-pnl ${d.profit >= 0 ? 'text-success' : 'text-danger'}">PnL: $${d.profit?.toFixed(2)}</span>
                <span class="deal-fee">Fee: $${d.commission?.toFixed(2)}</span>
                <span class="deal-comment">${d.comment || ''}</span>
              </div>
            `;
          });
        }
      }

      html += `
            </div>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  } catch (err) {
    console.error("Error fetching reports:", err);
  }
}

fetchReports();
setInterval(fetchReports, 10000);
