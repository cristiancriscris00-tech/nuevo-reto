#!/usr/bin/env python3
"""SolarisNews Oracle Zero v5.0 — Global Intelligence & Financial Hub."""
import base64, json, logging, random, re, sys, time, requests
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("oracle.log"), logging.StreamHandler()],
)
log = logging.getLogger("solaris_v5")

CONFIG_PATH   = Path("config.json")
CYCLE_SECONDS = 1800
RETRY_SECONDS = 30

# ── Filtro geopolítico ────────────────────────────────────────────────────────

GEO_KEYWORDS = [
    "gobierno","otan","rusia","petróleo","oro","ley","ue","unión europea",
    "sánchez","trump","conflicto","economía","guerra","bce","fed","inflación",
    "deuda","presupuesto","parlamento","congreso","senado","fiscal","aranceles",
    "china","ucrania","israel","iran","nato","fed","reserva federal","mercado",
    "bolsa","ibex","euro","dólar","bonos","deuda","crisis","migración","energía",
    "nuclear","defensa","ejército","armamento","sanción","veto","acuerdo","cumbre",
]

AGENT_MSGS = [
    "Agente 04: Movimientos detectados en el Estrecho. Vigilancia activa.",
    "Nodo SIGMA: Flujos de capital saliendo de bonos europeos. Confirmado.",
    "Analista 07: Repositorio de oro en Frankfurt — nivel de alerta NARANJA.",
    "INTEL-ES: Reunión de emergencia en Bruselas. Sin comunicado oficial.",
    "Agente 12: Actividad inusual en mercados de futuros del crudo. Monitorizando.",
    "Nodo ALPHA: Patrones de desinformación detectados en canales oficiales.",
    "Operativo 09: Movimiento de divisas en mercados asiáticos. Correlación positiva.",
    "SIGMA-3: Cumbre no publicada entre líderes G7. Fuentes internas.",
    "Agente 02: Incremento del 340% en búsquedas de 'reservas de emergencia'.",
    "Nodo BERLIN: Conversaciones sobre nuevo mecanismo de defensa europeo.",
]

DECODE_TEMPLATES = [
    "La narrativa oficial oculta un movimiento de capitales. Solaris detecta redistribución de influencia en el sector estratégico. Los actores visibles no son los actores reales.",
    "Detrás del titular hay una transferencia de poder económico. Los mercados ya lo saben. La población, todavía no. Monitorización en curso.",
    "Patrón identificado: cuando los medios hablan de esto, los fondos soberanos ya se han reposicionado. Solaris registra el movimiento 72 horas antes que la prensa.",
    "La información publicada es el 12% de lo que ocurre. El 88% restante lo procesan los algoritmos de Solaris. Conclusión: preparación es ventaja.",
    "Correlación detectada entre este evento y movimientos en mercados de commodities. La narrativa es el ruido. El precio es la señal.",
    "Solaris clasifica este evento como: REDISTRIBUCIÓN DE INFLUENCIA. Los titulares son decorado. El movimiento real está en las cifras que no publican.",
    "Tres horas después de este anuncio, los mercados reaccionarán. Solaris ya ha procesado el vector. La ventana de acción es ahora.",
    "Análisis de frecuencia: este patrón se repite cada 18 meses en la historia contemporánea. Siempre precede a una reconfiguración del tablero geopolítico.",
]

TACTICAL_PRODUCTS = [
    {"name": "Mochila Táctica Militar 45L",    "desc": "Equipamiento nivel operativo. Para cuando el sistema falle.", "emoji": "🎒"},
    {"name": "Linterna Táctica 2000 Lúmenes",  "desc": "Cuando corten la luz, tú seguirás viendo.",                  "emoji": "🔦"},
    {"name": "Kit de Emergencia Supervivencia", "desc": "72 horas de autonomía. Lo que recomiendan los gobiernos.",   "emoji": "🧰"},
    {"name": "Libro: El Arte de la Guerra",     "desc": "Sun Tzu. El manual que usan los que mandan.",               "emoji": "📖"},
    {"name": "Radio AM/FM de Emergencia",       "desc": "Funciona sin internet. Sin censura de algoritmos.",          "emoji": "📻"},
    {"name": "Filtro de Agua Portátil",         "desc": "El activo más infravalorado del siglo XXI.",                 "emoji": "💧"},
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:55]

def _esc(text):
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace('"', "&quot;"))

def _gh(token):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

def _is_geopolitical(title, body):
    combined = (title + " " + body).lower()
    return any(kw in combined for kw in GEO_KEYWORDS)

# ── RSS ───────────────────────────────────────────────────────────────────────

def _fetch_rss(url):
    r = requests.get(url, timeout=14, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "xml")
    out  = []
    for item in soup.find_all("item"):
        t = item.find("title")
        if not t:
            continue
        title = t.text.strip()
        desc_tag = item.find("description") or item.find("summary")
        raw  = desc_tag.text if desc_tag else ""
        desc = re.sub(r"\s+", " ",
                      BeautifulSoup(raw, "html.parser").get_text(" ", strip=True))
        if not _is_geopolitical(title, desc):
            continue
        p1 = (desc[:420].rsplit(" ", 1)[0] + "…") if len(desc) > 420 else (desc or "Información en desarrollo.")
        p2_raw = desc[420:900]
        p2 = (p2_raw.rsplit(" ", 1)[0] + "…") if len(p2_raw) > 20 else ""
        link_tag = item.find("link")
        link = link_tag.text.strip() if link_tag else "#"
        out.append({"title": title, "slug": _slug(title),
                    "p1": p1, "p2": p2, "link": link})
    return out

def get_trends():
    sources = [
        "https://www.abc.es/rss/2.0/espana/",
        "https://www.20minutos.es/rss/",
        "https://www.elconfidencial.com/rss/espana/",
        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
        "https://trends.google.com/trends/trendingsearches/daily/rss?geo=ES",
    ]
    all_items = []
    for url in sources:
        try:
            all_items.extend(_fetch_rss(url))
        except Exception as exc:
            log.warning("RSS %s: %s", url, exc)

    if not all_items:
        return [
            {"title": "Crisis Energética Europa",    "slug": "crisis-energetica-europa",
             "p1": "Los precios del gas y petróleo marcan nuevos máximos en los mercados europeos.",
             "p2": "", "link": "#"},
            {"title": "Reunión Emergencia UE Bruselas", "slug": "reunion-emergencia-ue",
             "p1": "Los líderes europeos se reúnen de urgencia para abordar la situación geopolítica.",
             "p2": "", "link": "#"},
            {"title": "Sánchez anuncia nuevas medidas económicas", "slug": "sanchez-medidas-economicas",
             "p1": "El Gobierno español presenta un nuevo paquete de medidas ante la presión inflacionaria.",
             "p2": "", "link": "#"},
        ]
    seen = set()
    filtered = [x for x in all_items if not (x["slug"] in seen or seen.add(x["slug"]))]
    log.info("Noticias geopolíticas filtradas: %d", len(filtered))
    return filtered[:20]

# ── GitHub ────────────────────────────────────────────────────────────────────

def _push(path, content_bytes, cfg, retries=3):
    token = cfg["github_token"]
    api   = (f"https://api.github.com/repos/{cfg['github_user']}"
             f"/{cfg['repo_name']}/contents/{path}")
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(api, headers=_gh(token), timeout=15)
            payload = {"message": f"v5: {path}",
                       "content": base64.b64encode(content_bytes).decode()}
            if r.status_code == 200:
                payload["sha"] = r.json()["sha"]
            r2 = requests.put(api, headers=_gh(token), json=payload, timeout=20)
            if r2.status_code in (200, 201):
                return True
        except requests.RequestException as exc:
            if attempt < retries:
                time.sleep(5 * attempt)
            else:
                log.warning("push [%s] falló: %s", path, exc)
    return False

def ensure_setup(cfg):
    token = cfg["github_token"]
    user  = cfg["github_user"]
    repo  = cfg["repo_name"]
    base  = f"https://api.github.com/repos/{user}/{repo}"

    r = requests.get(base, headers=_gh(token), timeout=15)
    if r.status_code == 404:
        r2 = requests.post(
            "https://api.github.com/user/repos", headers=_gh(token), timeout=15,
            json={"name": repo, "private": False, "auto_init": True},
        )
        if r2.status_code in (200, 201):
            log.info("Repo creado — esperando 8 s…")
            time.sleep(8)
        else:
            log.error("No se pudo crear repo: %s", r2.text[:150])
            return False

    rp = requests.post(f"{base}/pages", headers=_gh(token), timeout=15,
                       json={"source": {"branch": "main", "path": "/"}})
    if rp.status_code in (200, 201):     log.info("Pages activado.")
    elif rp.status_code in (409, 422):   log.info("Pages ya activo.")

    ensure_ads_txt(cfg)
    return True

def ensure_ads_txt(cfg):
    token   = cfg["github_token"]
    api     = (f"https://api.github.com/repos/{cfg['github_user']}"
               f"/{cfg['repo_name']}/contents/ads.txt")
    correct = f"adsterra.com, {cfg['ad_unit_id']}, DIRECT\n"
    r = requests.get(api, headers=_gh(token), timeout=15)
    if r.status_code == 200:
        existing = base64.b64decode(r.json()["content"]).decode().strip()
        if cfg["ad_unit_id"] in existing:
            log.info("ads.txt ✅ (ID %s)", cfg["ad_unit_id"])
            return
        payload = {"message": "v5: fix ads.txt", "sha": r.json()["sha"],
                   "content": base64.b64encode(correct.encode()).decode()}
    else:
        payload = {"message": "v5: create ads.txt",
                   "content": base64.b64encode(correct.encode()).decode()}
    r2 = requests.put(api, headers=_gh(token), json=payload, timeout=15)
    log.info("ads.txt %s", "✅ OK" if r2.status_code in (200, 201)
             else f"FALLÓ {r2.status_code}")

# ── Componentes HTML reutilizables ────────────────────────────────────────────

def _html_head(title, desc, canon, ad):
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <meta name="description" content="{_esc(desc)}"/>
  <meta property="og:title" content="{_esc(title)}"/>
  <meta property="og:type" content="website"/>
  <link rel="canonical" href="{canon}"/>
  <title>{_esc(title)}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    *{{box-sizing:border-box;}}
    body{{background:#020202;font-family:'Inter',sans-serif;}}
    .mono{{font-family:'Courier New',Courier,monospace;}}
    .neon{{color:#6366f1;text-shadow:0 0 14px #6366f199;}}
    .amber{{color:#f59e0b;text-shadow:0 0 10px #f59e0b66;}}
    .card{{background:#0a0a0f;border:1px solid #1e1b4b;border-radius:1rem;
           box-shadow:0 0 24px #6366f10d;transition:transform .15s,box-shadow .15s;}}
    .card:hover{{transform:translateY(-2px);box-shadow:0 0 32px #6366f122;}}
    .ticker-bar{{background:#060610;border-bottom:1px solid #1e1b4b;}}
    .intel-block{{background:#0d0b2a;border:1px solid #3730a3;border-radius:.875rem;}}
    .store-card{{background:#0a0805;border:1px solid #92400e;border-radius:1rem;}}
    .chat-msg{{background:#08080f;border-left:2px solid #6366f1;padding:.5rem .75rem;
               margin:.4rem 0;border-radius:0 .5rem .5rem 0;font-size:.7rem;}}
    .pulse{{animation:pulse 2s infinite;}}
    @keyframes pulse{{0%,100%{{opacity:1;}}50%{{opacity:.4;}}}}
    @media(max-width:640px){{.hide-mobile{{display:none!important;}}}}
  </style>
  <!-- Adsterra Social Bar -->
  <script type="text/javascript"
    src="//pl{ad}.highperformancegate.com/{ad}/invoke.js" async defer></script>
</head>"""

def _html_nav(now):
    return f"""
<nav style="background:#060610;border-bottom:1px solid #1e1b4b;"
     class="px-4 sm:px-6 py-3 flex items-center justify-between sticky top-0 z-50">
  <div>
    <a href="/" class="neon font-black text-xl mono tracking-widest">◈ SOLARIS<span style="color:#fff">NEWS</span></a>
    <p class="mono text-slate-600 text-xs mt-0.5 hide-mobile">ORACLE ZERO · GLOBAL INTELLIGENCE HUB</p>
  </div>
  <div class="flex items-center gap-3">
    <span class="mono text-xs text-indigo-400 hide-mobile">{now}</span>
    <span class="mono text-xs" style="color:#22c55e;">● <span class="pulse">LIVE</span></span>
  </div>
</nav>"""

def _tradingview_ticker():
    return """
<!-- TradingView Ticker Widget -->
<div class="ticker-bar py-2 px-2 overflow-hidden">
  <div class="tradingview-widget-container">
    <div class="tradingview-widget-container__widget"></div>
    <script type="text/javascript"
      src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
    {
      "symbols":[
        {"proName":"OANDA:XAUUSD","title":"Oro XAU/USD"},
        {"proName":"OANDA:BCOUSD","title":"Brent Crudo"},
        {"proName":"BITSTAMP:BTCUSD","title":"Bitcoin"},
        {"proName":"BME:IBC","title":"IBEX 35"},
        {"proName":"FX_IDC:EURUSD","title":"EUR/USD"}
      ],
      "showSymbolLogo":true,
      "colorTheme":"dark",
      "isTransparent":true,
      "displayMode":"adaptive",
      "locale":"es"
    }
    </script>
  </div>
</div>"""

def _agent_chat_html():
    msgs = random.sample(AGENT_MSGS, min(5, len(AGENT_MSGS)))
    items = "".join(f'<div class="chat-msg mono text-indigo-300">'
                    f'<span style="color:#f59e0b">[{datetime.now().strftime("%H:%M")}]</span> '
                    f'{_esc(m)}</div>' for m in msgs)
    return f"""
<div class="card p-4 mb-6">
  <p class="mono text-xs text-indigo-400 uppercase tracking-widest mb-3">
    ◈ RED DE AGENTES — LOG ENCRIPTADO
  </p>
  {items}
  <p class="mono text-xs text-slate-700 mt-3">
    SHA-256: {random.randint(10**15,10**16-1):x} · CANAL SEGURO · TLS 1.3
  </p>
</div>"""

def _subscribe_banner():
    return """
<div style="background:linear-gradient(135deg,#0d0b2a,#020202);border:1px solid #3730a3;"
     class="rounded-2xl p-6 mb-8 text-center">
  <p class="mono text-xs text-indigo-400 uppercase tracking-widest mb-2">◉ NIVEL DE ACCESO 5</p>
  <h2 class="text-xl sm:text-2xl font-black text-white mb-2">
    INTELIGENCIA SIN FILTROS — <span class="neon">PRÓXIMAMENTE</span>
  </h2>
  <p class="text-slate-400 text-sm mb-4 max-w-lg mx-auto">
    Recibe los informes de inteligencia geopolítica antes que nadie.
    Acceso directo a los análisis de alto nivel. Sin ruido. Sin censura.
  </p>
  <button class="mono text-xs px-6 py-3 rounded-xl font-bold text-white cursor-default"
          style="background:#1e1b4b;border:1px solid #6366f1;">
    UNIRSE A LA LISTA DE ESPERA →
  </button>
</div>"""

def _tactical_store(cpa):
    cards = ""
    for p in TACTICAL_PRODUCTS:
        cards += (
            f'<a href="{cpa}" target="_blank" rel="noopener" class="store-card p-4 block hover:scale-[1.02] transition">'
            f'<span class="text-3xl mb-2 block">{p["emoji"]}</span>'
            f'<p class="font-black text-white text-sm mb-1">{_esc(p["name"])}</p>'
            f'<p class="mono text-xs text-amber-400 leading-snug">{_esc(p["desc"])}</p>'
            f'<p class="mono text-xs text-slate-600 mt-2">→ Ver en Amazon</p>'
            f'</a>'
        )
    return f"""
<section class="mb-12">
  <div class="flex items-center gap-3 mb-4">
    <span class="amber font-black text-lg">⚡</span>
    <h2 class="font-black text-white text-lg uppercase tracking-wider">TIENDA DE SUMINISTROS TÁCTICOS</h2>
    <span class="mono text-xs text-amber-400 border border-amber-800 px-2 py-0.5 rounded">END-TIMES READY</span>
  </div>
  <p class="mono text-xs text-slate-500 mb-4">Equipamiento para cuando el sistema falle. Selección Solaris.</p>
  <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">{cards}</div>
</section>"""

# ── HTML Article ──────────────────────────────────────────────────────────────

def build_article(trend, cfg):
    ad    = cfg["ad_unit_id"]
    cpa   = cfg["cpa_link"]
    title = _esc(trend["title"])
    p1    = _esc(trend["p1"])
    p2    = _esc(trend["p2"]) if trend["p2"] else ""
    link  = trend["link"]
    canon = (f"https://{cfg['github_user']}.github.io"
             f"/{cfg['repo_name']}/{trend['slug']}/")
    now   = datetime.now().strftime("%-d %b %Y · %H:%M UTC")
    ts    = datetime.now().strftime("%Y%m%d%H%M")
    decode = random.choice(DECODE_TEMPLATES)
    agents = random.sample(AGENT_MSGS, 3)
    agent_items = "".join(
        f'<div class="chat-msg mono text-indigo-300">'
        f'<span style="color:#f59e0b">[{datetime.now().strftime("%H:%M")}]</span> {_esc(m)}</div>'
        for m in agents
    )

    return (
        _html_head(f"{title} | SolarisNews",
                   f"{title} — Análisis SolarisNews Oracle Zero.",
                   canon, ad)
        + f"""
<body class="text-white min-h-screen">
{_html_nav(now)}
{_tradingview_ticker()}

<main class="max-w-3xl mx-auto px-4 py-8">

  <!-- Categoría -->
  <div class="flex flex-wrap items-center gap-2 mb-4">
    <span class="mono text-xs text-red-400 border border-red-900 px-2 py-0.5 rounded">◉ ALERTA ACTIVA</span>
    <span class="mono text-xs text-indigo-400">#{ts} · NODO-ES</span>
    <span class="mono text-xs text-slate-600">{now}</span>
  </div>

  <h1 class="text-2xl sm:text-4xl font-black text-white leading-tight mb-3">{title}</h1>
  <p class="mono text-xs text-indigo-300 mb-8 pb-5" style="border-bottom:1px solid #1e1b4b;">
    SOLARISNEWS ORACLE ZERO · CLASIFICACIÓN: PÚBLICA
  </p>

  <!-- Cuerpo noticia -->
  <div class="card p-6 mb-6">
    <p class="mono text-xs text-indigo-400 mb-3 uppercase tracking-widest">▸ Informe de situación</p>
    <p class="text-slate-200 text-base leading-relaxed mb-3">
      <strong class="text-white">Análisis Solaris:</strong> Movimiento geopolítico detectado.
      Monitorización activa. {p1}
    </p>
    {"<p class='text-slate-400 text-base leading-relaxed'>" + p2 + "</p>" if p2 else ""}
  </div>

  <!-- Bloque DECODIFICACIÓN SOLARIS -->
  <div class="intel-block p-6 mb-6">
    <div class="flex items-center gap-2 mb-3">
      <span class="text-indigo-400 text-lg">◈</span>
      <h3 class="mono font-black text-indigo-300 uppercase tracking-widest text-sm">
        DECODIFICACIÓN SOLARIS
      </h3>
      <span class="mono text-xs text-red-400 border border-red-900 px-1.5 py-0.5 rounded">CLASIFICADO</span>
    </div>
    <p class="text-slate-300 text-sm leading-relaxed italic">"{_esc(decode)}"</p>
    <p class="mono text-xs text-indigo-600 mt-3">
      VECTOR: GEOPOLÍTICO · CONFIANZA: 94% · PROCESADO POR ORACLE ZERO
    </p>
  </div>

  <!-- Adsterra mid -->
  <div class="flex justify-center my-5">
    <script type="text/javascript"
      src="//pl{ad}.highperformancegate.com/{ad}/invoke.js"></script>
  </div>

  <!-- Botones -->
  <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
    <a href="{link}" target="_blank" rel="noopener"
       class="flex items-center justify-center gap-2 rounded-xl py-4 px-5 font-bold text-white transition hover:scale-105 text-sm"
       style="background:#1e1b4b;border:1px solid #6366f1;">
      📡 Informe Original
    </a>
    <a href="{cpa}" target="_blank" rel="noopener"
       class="flex items-center justify-center gap-2 rounded-xl py-4 px-5 font-bold text-white transition hover:scale-105 text-sm"
       style="background:#78350f;border:1px solid #f59e0b;">
      🛒 Suministros Tácticos
    </a>
  </div>

  <!-- Log de agentes -->
  <div class="card p-4 mb-8">
    <p class="mono text-xs text-indigo-400 uppercase tracking-widest mb-3">◈ LOG DE AGENTES</p>
    {agent_items}
  </div>

  {_subscribe_banner()}

  <!-- Metadata -->
  <div class="mono text-xs p-4 mb-6" style="background:#08080f;border:1px solid #1e1b4b;border-radius:.75rem;color:#3730a3;">
    SOURCE_VERIFIED: TRUE · THREAT_LEVEL: MONITOR · NODE: ES-INTEL-01 · <span id="ts2"></span>
  </div>

  <a href="../" class="mono text-xs text-indigo-400 hover:text-indigo-300">← VOLVER AL HUB GLOBAL</a>
</main>

<footer class="mono text-center text-xs py-6 mt-4" style="border-top:1px solid #1e1b4b;color:#2d2b55;">
  © {datetime.now().year} SOLARISNEWS ORACLE ZERO · SISTEMA AUTÓNOMO · GLOBAL HUB
</footer>

<script type="text/javascript"
  src="//pl{ad}.highperformancegate.com/{ad}/invoke.js"></script>
<script>
  const n=new Date().toLocaleString("es-ES");
  const el=document.getElementById("ts2");
  if(el) el.textContent=n;
</script>
</body></html>"""
    )

# ── HTML Home ─────────────────────────────────────────────────────────────────

def build_home(trends, cfg):
    ad  = cfg["ad_unit_id"]
    cpa = cfg["cpa_link"]
    now = datetime.now().strftime("%-d %b %Y · %H:%M")

    cards = ""
    for i, t in enumerate(trends):
        title = _esc(t["title"])
        p1    = _esc(t["p1"][:120]) + "…"
        badge = ("🔴 BREAKING" if i < 3
                 else ("🟡 MONITOR" if i < 8 else "⚪ ARCHIVO"))
        cards += (
            f'<li><a href="./{t["slug"]}/" class="card block p-5">'
            f'<div class="flex items-center justify-between mb-2">'
            f'<span class="mono text-xs text-indigo-400">#{str(i+1).zfill(2)} · ESP</span>'
            f'<span class="mono text-xs">{badge}</span></div>'
            f'<h2 class="font-black text-white text-sm sm:text-base leading-snug mb-2">{title}</h2>'
            f'<p class="mono text-xs text-slate-500 leading-relaxed">{p1}</p>'
            f'</a></li>'
        )

    return (
        _html_head("SolarisNews Oracle Zero | Inteligencia Geopolítica Global",
                   "Portal de inteligencia geopolítica y financiera. Noticias filtradas, análisis profundo, commodities en tiempo real.",
                   f"https://{cfg['github_user']}.github.io/{cfg['repo_name']}/",
                   ad)
        + f"""
<body class="text-white min-h-screen">
{_html_nav(now)}
{_tradingview_ticker()}

<!-- Hero -->
<header class="text-center py-10 px-4" style="background:linear-gradient(180deg,#0d0b1a 0%,#020202 100%);">
  <p class="mono text-xs text-indigo-400 tracking-widest mb-3 pulse">◉ SISTEMA ORACLE ZERO — MONITORIZACIÓN GLOBAL ACTIVA</p>
  <h1 class="text-4xl sm:text-6xl font-black mb-2"
      style="background:linear-gradient(90deg,#6366f1,#a5b4fc,#fff);
             -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
    SolarisNews
  </h1>
  <p class="mono text-slate-500 text-xs sm:text-sm">
    ORACLE ZERO · {len(trends)} ALERTAS GEOPOLÍTICAS ACTIVAS · <span id="ts"></span>
  </p>
</header>

<div class="max-w-6xl mx-auto px-4 pb-16">

  <!-- Subscribe banner -->
  {_subscribe_banner()}

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

    <!-- Columna principal: noticias -->
    <div class="lg:col-span-2">
      <div class="flex items-center gap-3 mb-4">
        <span class="mono text-xs text-red-400 border border-red-900 px-2 py-1 rounded">◉ EN DIRECTO</span>
        <span class="mono text-xs text-slate-600">{len(trends)} INFORMES · FILTRO GEOPOLÍTICO ACTIVO</span>
      </div>
      <ul class="space-y-3">{cards}</ul>
    </div>

    <!-- Sidebar derecho -->
    <div class="space-y-4">
      {_agent_chat_html()}

      <!-- TradingView mini chart Oro -->
      <div class="card p-3">
        <p class="mono text-xs text-indigo-400 mb-2 uppercase tracking-widest">◈ XAU/USD — ORO</p>
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript"
            src="https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js" async>
          {{
            "symbol":"OANDA:XAUUSD","width":"100%","height":150,
            "colorTheme":"dark","isTransparent":true,"locale":"es"
          }}
          </script>
        </div>
      </div>

      <!-- TradingView mini chart Brent -->
      <div class="card p-3">
        <p class="mono text-xs text-amber-400 mb-2 uppercase tracking-widest">◈ BRENT CRUDO</p>
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript"
            src="https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js" async>
          {{
            "symbol":"OANDA:BCOUSD","width":"100%","height":150,
            "colorTheme":"dark","isTransparent":true,"locale":"es"
          }}
          </script>
        </div>
      </div>
    </div>
  </div>

  <!-- Tienda táctica -->
  {_tactical_store(cpa)}

</div>

<footer class="mono text-center text-xs py-6" style="border-top:1px solid #1e1b4b;color:#2d2b55;">
  © {datetime.now().year} SOLARISNEWS ORACLE ZERO · SISTEMA AUTÓNOMO · GLOBAL HUB
</footer>

<script type="text/javascript"
  src="//pl{ad}.highperformancegate.com/{ad}/invoke.js"></script>
<script>document.getElementById("ts").textContent=new Date().toLocaleString("es-ES");</script>
</body></html>"""
    )

# ── GitHub Actions 24/7 ───────────────────────────────────────────────────────

def upload_workflow(cfg):
    workflow = b"""\
name: SolarisNews Oracle Zero 24/7
on:
  schedule:
    - cron: '*/30 * * * *'
  workflow_dispatch:
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.11'}
      - run: pip install requests beautifulsoup4 lxml
      - name: Config
        env:
          ORACLE_TOKEN:   ${{ secrets.ORACLE_TOKEN }}
          ORACLE_USER:    ${{ secrets.ORACLE_USER }}
          ORACLE_REPO:    ${{ secrets.ORACLE_REPO }}
          ORACLE_WEBHOOK: ${{ secrets.ORACLE_WEBHOOK }}
          ORACLE_AD_ID:   ${{ secrets.ORACLE_AD_ID }}
          ORACLE_CPA:     ${{ secrets.ORACLE_CPA }}
          ORACLE_PAYPAL:  ${{ secrets.ORACLE_PAYPAL }}
        run: |
          python - <<'PYEOF'
          import json,os
          cfg={"github_token":os.environ["ORACLE_TOKEN"],"github_user":os.environ["ORACLE_USER"],
               "repo_name":os.environ["ORACLE_REPO"],"webhook_url":os.environ["ORACLE_WEBHOOK"],
               "ad_unit_id":os.environ["ORACLE_AD_ID"],"cpa_link":os.environ["ORACLE_CPA"],
               "paypal_email":os.environ["ORACLE_PAYPAL"],"payout_method":"paypal"}
          open("config.json","w").write(json.dumps(cfg))
          PYEOF
      - run: python astral_oracle.py --once
"""
    path = ".github/workflows/solarisnews.yml"
    api  = (f"https://api.github.com/repos/{cfg['github_user']}"
            f"/{cfg['repo_name']}/contents/{path}")
    r = requests.get(api, headers=_gh(cfg["github_token"]), timeout=15)
    payload = {"message": "v5: Oracle Zero workflow",
               "content": base64.b64encode(workflow).decode()}
    if r.status_code == 200:
        payload["sha"] = r.json()["sha"]
    r2 = requests.put(api, headers=_gh(cfg["github_token"]), json=payload, timeout=15)
    log.info("Workflow 24/7 %s", "✅ subido" if r2.status_code in (200,201)
             else f"FALLÓ {r2.status_code}")

def upload_self(cfg):
    if _push("astral_oracle.py", Path(__file__).read_bytes(), cfg):
        log.info("✅ astral_oracle.py v5 subido al repo.")

# ── Ciclo ─────────────────────────────────────────────────────────────────────

def rotate_log(max_lines=100):
    p = Path("oracle.log")
    if not p.exists():
        return
    lines = p.read_text(errors="replace").splitlines()
    if len(lines) > max_lines:
        p.write_text("\n".join(lines[-max_lines:]) + "\n")

def run_once(cfg):
    rotate_log()
    log.info("═══ ORACLE ZERO v5.0 — CYCLE START ═══")
    if not ensure_setup(cfg):
        log.error("Setup falló.")
        return
    ensure_ads_txt(cfg)
    trends = get_trends()
    _push("index.html", build_home(trends, cfg).encode(), cfg)
    publicadas = 0
    for t in trends:
        try:
            ok  = _push(f"{t['slug']}/index.html",
                        build_article(t, cfg).encode(), cfg)
            cpa = cfg["cpa_link"]
            redir = (f'<!DOCTYPE html><html><head><meta charset="UTF-8"/>'
                     f'<meta http-equiv="refresh" content="0;url={cpa}"/>'
                     f'</head><body><script>window.location.replace("{cpa}");</script></body></html>')
            _push(f"{t['slug']}/go/index.html", redir.encode(), cfg)
            if ok:
                publicadas += 1
                log.info("✅ %s", t["slug"])
        except Exception as exc:
            log.warning("Error '%s': %s", t["slug"], exc)
        time.sleep(1)
    log.info("═══ CICLO COMPLETADO: %d/%d ═══", publicadas, len(trends))

def main():
    once_mode = "--once" in sys.argv
    if not CONFIG_PATH.exists():
        log.error("config.json no encontrado.")
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    if once_mode:
        run_once(cfg)
        return
    log.info("═══ ORACLE ZERO v5.0 — MODO LOCAL ═══")
    upload_self(cfg)
    upload_workflow(cfg)
    while True:
        try:
            run_once(cfg)
            log.info("Durmiendo %ds…", CYCLE_SECONDS)
            time.sleep(CYCLE_SECONDS)
        except KeyboardInterrupt:
            log.info("Detenido.")
            sys.exit(0)
        except Exception as exc:
            log.error("Error: %s — reintentando en %ds", exc, RETRY_SECONDS)
            time.sleep(RETRY_SECONDS)

if __name__ == "__main__":
    main()
