"""Simple admin dashboard for the VPN bot.

Mounted on the same aiohttp app as the Tribute webhook. Shows users, balances,
payments, transactions and live logs in plain language for the owner. Dark
"liquid glass" theme, purple + cyan accents.

Protect it by setting DASHBOARD_TOKEN in .env; then open /dashboard?token=...
"""
import logging
from collections import deque
from datetime import datetime, timezone

from aiohttp import web
from sqlalchemy import text

from config import config

logger = logging.getLogger(__name__)

SESSION_POOL_KEY = "session_pool"

# ---------------------------------------------------------------------------
# Live log capture: a ring buffer the dashboard can read from.
# ---------------------------------------------------------------------------
_LOG_BUFFER: deque[str] = deque(maxlen=500)


class _RingBufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            _LOG_BUFFER.append(self.format(record))
        except Exception:
            pass


def install_log_capture(level: int = logging.INFO) -> None:
    """Attach the ring-buffer handler to the root logger. Call once at startup."""
    handler = _RingBufferHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.setLevel(level)
    root = logging.getLogger()
    # avoid double-install
    if not any(isinstance(h, _RingBufferHandler) for h in root.handlers):
        root.addHandler(handler)


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------
def _authorized(request: web.Request) -> bool:
    if not config.dashboard_token:
        return False # Requires token to be explicitly set
    token = request.query.get("token") or request.headers.get("X-Dashboard-Token")
    return token == config.dashboard_token


def _deny() -> web.Response:
    return web.json_response({"ok": False, "error": "unauthorized"}, status=401)


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------
async def _rows(request: web.Request, sql: str, params: dict | None = None) -> list[dict]:
    pool = request.app[SESSION_POOL_KEY]
    async with pool() as session:
        result = await session.execute(text(sql), params or {})
        return [dict(r) for r in result.mappings().all()]


async def api_stats(request: web.Request) -> web.Response:
    if not _authorized(request):
        return _deny()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    pool = request.app[SESSION_POOL_KEY]
    async with pool() as session:
        async def scalar(sql, params=None):
            r = await session.execute(text(sql), params or {})
            return r.scalar() or 0

        users = await scalar("SELECT COUNT(*) FROM users")
        balance_total = await scalar("SELECT COALESCE(SUM(balance),0) FROM users")
        topups = await scalar("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='topup'")
        spent = await scalar("SELECT COALESCE(-SUM(amount),0) FROM transactions WHERE type='purchase'")
        active = await scalar(
            "SELECT COUNT(*) FROM users WHERE subscription_expires_at > :now", {"now": now}
        )
        pay_credited = await scalar("SELECT COUNT(*) FROM payment_events WHERE status='credited'")
        pay_problem = await scalar(
            "SELECT COUNT(*) FROM payment_events WHERE status IN ('quarantine','ignored','error')"
        )
    return web.json_response({
        "users": users,
        "balance_total": balance_total,
        "topups": topups,
        "spent": spent,
        "active_subs": active,
        "pay_credited": pay_credited,
        "pay_problem": pay_problem,
    })


async def api_users(request: web.Request) -> web.Response:
    if not _authorized(request):
        return _deny()
    rows = await _rows(request,
        "SELECT id, telegram_id, username, balance, trial_used, "
        "subscription_expires_at, created_at FROM users ORDER BY id DESC LIMIT 200")
    return web.json_response(_stringify(rows))


async def api_payments(request: web.Request) -> web.Response:
    if not _authorized(request):
        return _deny()
    rows = await _rows(request,
        "SELECT id, telegram_user_id, user_id, amount_kopecks, currency, status, "
        "event_name, created_at, processed_at FROM payment_events ORDER BY id DESC LIMIT 200")
    return web.json_response(_stringify(rows))


async def api_transactions(request: web.Request) -> web.Response:
    if not _authorized(request):
        return _deny()
    rows = await _rows(request,
        "SELECT t.id, t.user_id, u.username, t.amount, t.type, t.comment, t.created_at "
        "FROM transactions t LEFT JOIN users u ON u.id = t.user_id "
        "ORDER BY t.id DESC LIMIT 200")
    return web.json_response(_stringify(rows))


async def api_logs(request: web.Request) -> web.Response:
    if not _authorized(request):
        return _deny()
    return web.json_response({"lines": list(_LOG_BUFFER)[-300:]})


def _stringify(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        out.append({k: (str(v) if v is not None else None) for k, v in r.items()})
    return out


async def dashboard_page(request: web.Request) -> web.Response:
    if not _authorized(request):
        return web.Response(
            text="<h1 style='font-family:sans-serif'>🔒 Нужен токен доступа</h1>"
                 "<p>В конфигурации задан токен доступа, но он не передан.</p>"
                 "<p>Откройте страницу как <code>/dashboard?token=ВАШ_ТОКЕН</code></p>",
            content_type="text/html", status=401)
    return web.Response(text=_HTML, content_type="text/html")


def setup_dashboard(app: web.Application) -> None:
    """Register dashboard routes on an existing aiohttp app."""
    from web.support_api import get_chats, get_messages, reply_message

    app.router.add_get("/", lambda r: web.HTTPFound("/dashboard"))
    app.router.add_get("/dashboard", dashboard_page)
    app.router.add_get("/api/stats", api_stats)
    app.router.add_get("/api/users", api_users)
    app.router.add_get("/api/payments", api_payments)
    app.router.add_get("/api/transactions", api_transactions)
    app.router.add_get("/api/logs", api_logs)

    # Support chat endpoints
    app.router.add_get("/api/support/chats", get_chats)
    app.router.add_get("/api/support/messages", get_messages)
    app.router.add_post("/api/support/reply", reply_message)


# ---------------------------------------------------------------------------
# The page (self-contained: HTML + CSS + JS).
# ---------------------------------------------------------------------------
_HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VPN бот — Панель управления</title>
<style>
  :root{
    --primary:#10b981; --primary-hover:#059669; --cyan:#0ea5e9;
    --bg0:#050c12; --bg1:#0b151e; --txt:#f1f5f9; --muted:#94a3b8;
    --glass:rgba(255,255,255,.03); --glass-brd:rgba(255,255,255,.08);
  }
  *{box-sizing:border-box}
  body{
    margin:0; min-height:100vh; color:var(--txt);
    font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
    background:
      radial-gradient(1200px 600px at 10% -10%, rgba(14,165,233,.15), transparent 60%),
      radial-gradient(900px 500px at 110% 10%, rgba(16,185,129,.15), transparent 55%),
      linear-gradient(160deg,var(--bg0),var(--bg1));
    background-attachment:fixed;
  }
  header{padding:28px 24px 8px; display:flex; align-items:center; gap:14px; flex-wrap:wrap}
  header h1{font-size:22px; margin:0; font-weight:700; letter-spacing:.3px}
  header .dot{width:10px;height:10px;border-radius:50%;background:var(--cyan);box-shadow:0 0 12px var(--cyan)}
  .sub{color:var(--muted); font-size:13px; margin:2px 0 0}
  .wrap{padding:16px 24px 60px; max-width:1200px; margin:0 auto}
  .grid{display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); margin-bottom:22px}
  .card{
    background:var(--glass); border:1px solid var(--glass-brd); border-radius:18px;
    padding:18px; backdrop-filter:blur(16px) saturate(140%); -webkit-backdrop-filter:blur(16px) saturate(140%);
    box-shadow:0 8px 30px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.08);
  }
  .stat .label{color:var(--muted); font-size:13px; margin-bottom:8px}
  .stat .value{font-size:28px; font-weight:750}
  .stat .value.accent{color:var(--primary)}
  .stat .value.cyan{color:var(--cyan)}
  .panel{margin-top:20px}
  .panel h2{font-size:15px; margin:0 0 12px; font-weight:650; display:flex; gap:8px; align-items:center}
  .panel h2 .hint{color:var(--muted); font-weight:400; font-size:12px}
  .tablewrap{overflow:auto; border-radius:14px; border:1px solid var(--glass-brd)}
  table{width:100%; border-collapse:collapse; font-size:13px; min-width:560px}
  th,td{padding:10px 12px; text-align:left; white-space:nowrap}
  thead th{background:rgba(255,255,255,.05); color:var(--muted); font-weight:600; position:sticky; top:0}
  tbody tr{border-top:1px solid rgba(255,255,255,.06)}
  tbody tr:hover{background:rgba(14,165,233,.08)}
  .badge{padding:3px 9px; border-radius:999px; font-size:11px; font-weight:600}
  .b-ok{background:rgba(34,211,238,.16); color:#7ce9fb}
  .b-bad{background:rgba(255,90,120,.16); color:#ff9fb1}
  .b-mut{background:rgba(255,255,255,.08); color:var(--muted)}
  .pos{color:#7ce9fb} .neg{color:#ff9fb1}
  .logs{background:rgba(0,0,0,.4); border-radius:14px; border:1px solid var(--glass-brd);
    padding:14px; font-family:ui-monospace,Menlo,Consolas,monospace; font-size:12px;
    line-height:1.55; max-height:300px; overflow:auto; white-space:pre-wrap; color:#cfc7e6}
  .tabs{display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px}
  .tab{cursor:pointer; padding:8px 14px; border-radius:12px; font-size:13px;
    background:var(--glass); border:1px solid var(--glass-brd); color:var(--muted)}
  .tab.active{color:#fff; border-color:var(--primary); box-shadow:0 0 0 1px var(--primary), 0 6px 20px rgba(16,185,129,.2);
    background:linear-gradient(135deg, rgba(16,185,129,.2), rgba(14,165,233,.1))}
  .support-container { display: flex; height: 500px; gap: 16px; }
  .chat-list { width: 300px; background: var(--glass); border: 1px solid var(--glass-brd); border-radius: 14px; overflow-y: auto; }
  .chat-item { padding: 12px 16px; border-bottom: 1px solid var(--glass-brd); cursor: pointer; transition: background .2s; }
  .chat-item:hover, .chat-item.active { background: rgba(14,165,233,.1); }
  .chat-name { font-weight: 600; font-size: 14px; }
  .chat-uid { font-size: 11px; color: var(--muted); }
  .chat-box { flex: 1; display: flex; flex-direction: column; background: var(--glass); border: 1px solid var(--glass-brd); border-radius: 14px; }
  .chat-messages { flex: 1; padding: 16px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
  .msg { max-width: 80%; padding: 10px 14px; border-radius: 12px; font-size: 13px; line-height: 1.4; }
  .msg-user { align-self: flex-start; background: rgba(255,255,255,.05); border-bottom-left-radius: 2px; }
  .msg-admin { align-self: flex-end; background: rgba(16,185,129,.15); color: #a7f3d0; border-bottom-right-radius: 2px; }
  .msg-time { font-size: 10px; color: var(--muted); margin-top: 4px; text-align: right; }
  .chat-input-area { padding: 12px; border-top: 1px solid var(--glass-brd); display: flex; gap: 8px; }
  .chat-input-area input { flex: 1; background: rgba(0,0,0,.2); border: 1px solid var(--glass-brd); color: #fff; padding: 10px 14px; border-radius: 8px; outline: none; }
  .chat-input-area input:focus { border-color: var(--primary); }
  .chat-input-area button { background: var(--primary); color: #fff; border: none; padding: 0 16px; border-radius: 8px; cursor: pointer; font-weight: 600; }
  .chat-input-area button:hover { background: var(--primary-hover); }
  .updated{color:var(--muted); font-size:12px; margin-left:auto}
  a{color:var(--cyan)}
</style>
</head>
<body>
<header>
  <span class="dot"></span>
  <div>
    <h1>VPN бот — Панель управления</h1>
    <p class="sub">Здесь видно всё, что происходит в вашем боте: люди, деньги и события. Обновляется само.</p>
  </div>
  <span class="updated" id="updated">загрузка…</span>
</header>

<div class="wrap">
  <div class="grid" id="stats"></div>

  <div class="panel">
    <div class="tabs">
      <div class="tab active" data-tab="payments">💳 Платежи</div>
      <div class="tab" data-tab="users">👥 Пользователи</div>
      <div class="tab" data-tab="transactions">📒 Операции</div>
      <div class="tab" data-tab="support">💬 Поддержка</div>
      <div class="tab" data-tab="logs">📃 Журнал (логи)</div>
    </div>
    <div id="view"></div>
  </div>
</div>

<script>
const token = new URLSearchParams(location.search).get('token');
const q = p => token ? p + (p.includes('?')?'&':'?') + 'token=' + encodeURIComponent(token) : p;
let activeTab = 'payments';
let activeChatUserId = null;

async function getJSON(p){ const r = await fetch(q(p)); return r.json(); }

function money(v){ return (Number(v)||0).toLocaleString('ru-RU') + ' ₽'; }

async function loadStats(){
  const s = await getJSON('/api/stats');
  const cards = [
    ['Всего пользователей', s.users, ''],
    ['Активных подписок', s.active_subs, 'cyan'],
    ['Денег на балансах', money(s.balance_total), 'accent'],
    ['Пополнили всего', money(s.topups), 'accent'],
    ['Потрачено на подписки', money(s.spent), ''],
    ['Платежей зачтено', s.pay_credited, 'cyan'],
    ['Платежей с проблемой', s.pay_problem, s.pay_problem>0?'':''],
  ];
  document.getElementById('stats').innerHTML = cards.map(c=>`
    <div class="card stat">
      <div class="label">${c[0]}</div>
      <div class="value ${c[2]}">${c[1]}</div>
    </div>`).join('');
}

function badge(status){
  const ok = ['credited'];
  const bad = ['quarantine','ignored','error'];
  let cls = 'b-mut';
  if(ok.includes(status)) cls='b-ok';
  else if(bad.includes(status)) cls='b-bad';
  const ru = {credited:'зачтено', quarantine:'карантин', ignored:'пропущено', error:'ошибка', received:'получено'}[status]||status;
  return `<span class="badge ${cls}">${ru}</span>`;
}

function table(cols, rows){
  return `<div class="tablewrap"><table><thead><tr>${cols.map(c=>`<th>${c.h}</th>`).join('')}</tr></thead>
    <tbody>${rows.map(r=>`<tr>${cols.map(c=>`<td>${c.f?c.f(r[c.k],r):(r[c.k]??'')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}

async function render(){
  const v = document.getElementById('view');
  if(activeTab==='payments'){
    const rows = await getJSON('/api/payments');
    v.innerHTML = table([
      {h:'#',k:'id'},
      {h:'Telegram ID',k:'telegram_user_id'},
      {h:'Сумма',k:'amount_kopecks',f:x=>money((Number(x)||0)/100)},
      {h:'Валюта',k:'currency'},
      {h:'Статус',k:'status',f:badge},
      {h:'Когда',k:'created_at'},
    ], rows);
  } else if(activeTab==='users'){
    const rows = await getJSON('/api/users');
    v.innerHTML = table([
      {h:'#',k:'id'},
      {h:'Telegram ID',k:'telegram_id'},
      {h:'Username',k:'username',f:x=>x?'@'+x:'—'},
      {h:'Баланс',k:'balance',f:money},
      {h:'Пробный',k:'trial_used',f:x=>x==='1'||x===1?'да':'нет'},
      {h:'Подписка до',k:'subscription_expires_at',f:x=>x?x.split('.')[0]:'—'},
    ], rows);
  } else if(activeTab==='transactions'){
    const rows = await getJSON('/api/transactions');
    const tname = {topup:'пополнение', purchase:'покупка', trial:'пробный', referral_reward:'реф. награда', referral_bonus:'реф. бонус'};
    v.innerHTML = table([
      {h:'#',k:'id'},
      {h:'Кто',k:'username',f:x=>x?'@'+x:'—'},
      {h:'Сумма',k:'amount',f:x=>`<span class="${Number(x)<0?'neg':'pos'}">${money(x)}</span>`},
      {h:'Тип',k:'type',f:x=>tname[x]||x},
      {h:'Комментарий',k:'comment'},
      {h:'Когда',k:'created_at'},
    ], rows);
  } else if(activeTab==='support'){
    const chats = await getJSON('/api/support/chats');
    v.innerHTML = `<div class="support-container">
      <div class="chat-list" id="chatList">
        ${chats.map(c=>`<div class="chat-item ${c.id===activeChatUserId?'active':''}" onclick="openChat(${c.id})">
          <div class="chat-name">${escapeHtml(c.name)}</div>
          <div class="chat-uid">ID: ${c.id} | tg: ${c.telegram_id}</div>
        </div>`).join('')}
      </div>
      <div class="chat-box">
        <div class="chat-messages" id="chatMessages">
          <div style="margin:auto; color:var(--muted)">Выберите диалог слева</div>
        </div>
        <div class="chat-input-area" id="chatInputArea" style="display:none">
          <input type="text" id="chatInput" placeholder="Введите ответ..." onkeypress="if(event.key==='Enter') sendReply()">
          <button onclick="sendReply()">Отправить</button>
        </div>
      </div>
    </div>`;
    if(activeChatUserId) await openChat(activeChatUserId, false);
  } else if(activeTab==='logs'){
    const d = await getJSON('/api/logs');
    v.innerHTML = `<div class="logs" id="logbox">${(d.lines||[]).map(escapeHtml).join('\n')||'журнал пуст'}</div>`;
    const box = document.getElementById('logbox'); if(box) box.scrollTop = box.scrollHeight;
  }
}

async function openChat(userId, updateList=true){
  activeChatUserId = userId;
  if(updateList) {
    document.querySelectorAll('.chat-item').forEach(el=>el.classList.remove('active'));
    event.currentTarget.classList.add('active');
  }
  const msgs = await getJSON(`/api/support/messages?user_id=${userId}`);
  const mb = document.getElementById('chatMessages');
  if(mb){
    mb.innerHTML = msgs.map(m=>`<div class="msg ${m.is_from_user?'msg-user':'msg-admin'}">
      <div>${escapeHtml(m.text).replace(/\n/g,'<br>')}</div>
      <div class="msg-time">${new Date(m.created_at+'Z').toLocaleString('ru-RU')}</div>
    </div>`).join('');
    mb.scrollTop = mb.scrollHeight;
    document.getElementById('chatInputArea').style.display = 'flex';
  }
}

async function sendReply(){
  if(!activeChatUserId) return;
  const inp = document.getElementById('chatInput');
  const text = inp.value.trim();
  if(!text) return;
  inp.disabled = true;
  await fetch(q('/api/support/reply'), {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({user_id: activeChatUserId, text})
  });
  inp.value = ''; inp.disabled = false; inp.focus();
  await openChat(activeChatUserId, false);
}

function escapeHtml(s){ return String(s).replace(/[&<>]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }

document.querySelectorAll('.tab').forEach(t=>t.addEventListener('click',()=>{
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
  t.classList.add('active'); activeTab = t.dataset.tab; render();
}));

async function refresh(){
  try{ await Promise.all([loadStats(), render()]);
    document.getElementById('updated').textContent = 'обновлено ' + new Date().toLocaleTimeString('ru-RU');
  }catch(e){ document.getElementById('updated').textContent = 'нет связи с сервером'; }
}
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>"""
