#!/usr/bin/env python3
"""SolarisNews Intelligence Hub v4.0 — Autonomous geopolitical news network."""
import base64, json, logging, re, sys, time, requests
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler("oracle.log"), logging.StreamHandler()]
)
log = logging.getLogger("solaris_v4")

CONFIG_PATH   = Path("config.json")
CYCLE_SECONDS = 1800
RETRY_SECONDS = 30

SOLARIS_PREFIX = (
    "Análisis Solaris: Movimiento geopolítico detectado. Monitorización activa. "
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:55]

def _esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")

def _gh(token):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

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
        raw = desc_tag.text if desc_tag else ""
        desc = re.sub(r"\s+", " ", BeautifulSoup(raw, "html.parser").get_text(" ", strip=True))
        p1 = (desc[:420].rsplit(" ", 1)[0] + "…") if len(desc) > 420 else (desc or "Ampliando información…")
        p2_raw = desc[420:900]
        p2 = (p2_raw.rsplit(" ", 1)[0] + "…") if len(p2_raw) > 20 else ""
        link_tag = item.find("link")
        link = link_tag.text.strip() if link_tag else "#"
        out.append({"title": title, "slug": _slug(title), "p1": p1, "p2": p2, "link": link})
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
            {"title": "Precio Luz España Hoy",  "slug": "precio-luz-hoy",
             "p1": "El mercado eléctrico registra movimientos relevantes.", "p2": "", "link": "#"},
            {"title": "Resultado Real Madrid",   "slug": "resultado-real-madrid",
             "p1": "Novedades del equipo blanco.", "p2": "", "link": "#"},
            {"title": "Ofertas Amazon España",   "slug": "ofertas-amazon",
             "p1": "Las mejores ofertas del día.", "p2": "", "link": "#"},
        ]
    seen = set()
    return [x for x in all_items if not (x["slug"] in seen or seen.add(x["slug"]))][:20]

# ── GitHub ────────────────────────────────────────────────────────────────────

def _push(path, content_bytes, cfg, retries=3):
    token = cfg["github_token"]
    api   = (f"https://api.github.com/repos/{cfg['github_user']}"
             f"/{cfg['repo_name']}/contents/{path}")
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(api, headers=_gh(token), timeout=15)
            payload = {"message": f"v4: {path}",
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
    if rp.status_code in (200, 201):   log.info("GitHub Pages activado.")
    elif rp.status_code in (409, 422): log.info("GitHub Pages ya activo.")

    ensure_ads_txt(cfg)
    return True


def ensure_ads_txt(cfg):
    """Verifica y garantiza ads.txt en cada ciclo. Sin este archivo Adsterra no paga."""
    token   = cfg["github_token"]
    base    = f"https://api.github.com/repos/{cfg['github_user']}/{cfg['repo_name']}"
    api     = f"{base}/contents/ads.txt"
    correct = f"adsterra.com, {cfg['ad_unit_id']}, DIRECT\n"

    r = requests.get(api, headers=_gh(token), timeout=15)
    if r.status_code == 200:
        # Verificar que el contenido tiene el ID correcto
        existing = base64.b64decode(r.json()["content"]).decode().strip()
        if cfg["ad_unit_id"] in existing:
            log.info("ads.txt ✅ verificado (ID %s presente).", cfg["ad_unit_id"])
            return
        # Contenido incorrecto — sobreescribir
        payload = {"message": "v4: fix ads.txt", "sha": r.json()["sha"],
                   "content": base64.b64encode(correct.encode()).decode()}
        log.warning("ads.txt tenía contenido incorrecto — corrigiendo…")
    else:
        payload = {"message": "v4: create ads.txt",
                   "content": base64.b64encode(correct.encode()).decode()}

    r2 = requests.put(api, headers=_gh(token), json=payload, timeout=15)
    if r2.status_code in (200, 201):
        log.info("ads.txt ✅ creado/actualizado con ID %s.", cfg["ad_unit_id"])
    else:
        log.error("ads.txt FALLÓ (%s) — Adsterra no podrá validar el dominio.", r2.status_code)

# ── HTML Article ──────────────────────────────────────────────────────────────

def build_article(trend, cfg):
    ad   = cfg["ad_unit_id"]
    cpa  = cfg["cpa_link"]
    t    = _esc(trend["title"])
    p1   = _esc(SOLARIS_PREFIX + trend["p1"])
    p2   = _esc(trend["p2"]) if trend["p2"] else ""
    link = trend["link"]
    canon = f"https://{cfg['github_user']}.github.io/{cfg['repo_name']}/{trend['slug']}/"
    now  = datetime.now().strftime("%-d %b %Y · %H:%M UTC")
    ts   = datetime.now().strftime("%Y%m%d%H%M")

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <meta name="description" content="{t} — Análisis SolarisNews Intelligence Hub."/>
  <meta property="og:title" content="{t} | SolarisNews"/>
  <meta property="og:type" content="article"/>
  <link rel="canonical" href="{canon}"/>
  <title>{t} | SolarisNews Intelligence Hub</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body{{background:#050505;}}
    .mono{{font-family:'Courier New',Courier,monospace;}}
    .neon{{color:#6366f1;text-shadow:0 0 12px #6366f188;}}
    .card-border{{border:1px solid #1e1b4b;box-shadow:0 0 20px #6366f115;}}
  </style>
</head>
<body class="text-white min-h-screen font-sans">

  <nav style="background:#08080f;border-bottom:1px solid #1e1b4b"
       class="px-4 py-3 flex items-center justify-between sticky top-0 z-50">
    <a href="../" class="neon font-black text-lg mono tracking-widest">◈ SOLARIS<span class="text-white">NEWS</span></a>
    <span class="mono text-xs text-indigo-400 hidden sm:block">SISTEMA ACTIVO · {now}</span>
    <span class="mono text-xs text-green-400 animate-pulse">● LIVE</span>
  </nav>

  <div class="flex justify-center py-3" style="background:#08080f;border-bottom:1px solid #1e1b4b;">
    <script type="text/javascript" src="//pl{ad}.highperformancegate.com/{ad}/invoke.js"></script>
  </div>

  <main class="max-w-3xl mx-auto px-4 py-10">
    <div class="flex items-center gap-3 mb-4">
      <span class="mono text-xs text-red-400 border border-red-800 px-2 py-0.5 rounded">◉ ALERTA ACTIVA</span>
      <span class="mono text-xs text-indigo-400">#{ts} · ESP</span>
    </div>
    <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight mb-3">{t}</h1>
    <div class="mono text-xs text-indigo-300 mb-8 pb-6" style="border-bottom:1px solid #1e1b4b;">
      SOLARISNEWS INTELLIGENCE HUB · CLASIFICACIÓN: PÚBLICA · <span id="ts2"></span>
    </div>

    <div class="card-border rounded-2xl p-6 mb-6" style="background:#0d0d1a;">
      <p class="mono text-xs text-indigo-400 mb-4 uppercase tracking-widest">▸ Informe de situación</p>
      <p class="text-slate-200 text-base leading-relaxed mb-4">{p1}</p>
      {"<p class='text-slate-400 text-base leading-relaxed'>" + p2 + "</p>" if p2 else ""}
    </div>

    <div class="flex justify-center my-6">
      <script type="text/javascript" src="//pl{ad}.highperformancegate.com/{ad}/invoke.js"></script>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-10">
      <a href="{link}" target="_blank" rel="noopener"
         class="flex items-center justify-center gap-2 rounded-xl py-4 px-6 font-bold text-white transition hover:scale-105"
         style="background:#1e1b4b;border:1px solid #6366f1;">
        <span>📡</span><span>Informe Original</span>
      </a>
      <a href="{cpa}" target="_blank" rel="noopener"
         class="flex items-center justify-center gap-2 rounded-xl py-4 px-6 font-bold text-white transition hover:scale-105"
         style="background:#78350f;border:1px solid #f59e0b;">
        <span>🛒</span><span>Suministros Tácticos</span>
      </a>
    </div>

    <div class="mono text-xs card-border rounded-xl p-4 mb-8" style="background:#08080f;color:#4f46e5;">
      <p>◈ SOURCE_VERIFIED: TRUE &nbsp;|&nbsp; THREAT_LEVEL: MONITOR</p>
      <p>◈ LAST_UPDATE: <span id="ts3"></span> &nbsp;|&nbsp; NODE: ES-INTEL-01</p>
    </div>
    <a href="../" class="mono text-xs text-indigo-400 hover:text-indigo-300 transition">← VOLVER AL HUB</a>
  </main>

  <footer class="mono text-center text-xs py-8 mt-4" style="border-top:1px solid #1e1b4b;color:#2d2b55;">
    © {datetime.now().year} SOLARISNEWS INTELLIGENCE HUB · SISTEMA AUTÓNOMO · ESPAÑA
  </footer>

  <script type="text/javascript" src="//pl{ad}.highperformancegate.com/{ad}/invoke.js"></script>
  <script>
    const n = new Date().toLocaleString("es-ES");
    ["ts2","ts3"].forEach(id => {{ const el=document.getElementById(id); if(el) el.textContent=n; }});
  </script>
</body>
</html>"""

# ── HTML Home ─────────────────────────────────────────────────────────────────

def build_home(trends, cfg):
    ad  = cfg["ad_unit_id"]
    now = datetime.now().strftime("%-d %b %Y · %H:%M")
    cards = ""
    for i, t in enumerate(trends):
        title = _esc(t["title"])
        p1    = _esc(t["p1"][:110]) + "…"
        badge = "🔴 BREAKING" if i < 3 else ("🟡 MONITOR" if i < 8 else "⚪ ARCHIVO")
        cards += (
            f'<li><a href="./{t["slug"]}/" '
            f'class="block card-border rounded-2xl p-5 transition hover:scale-[1.02]" '
            f'style="background:#0d0d1a;">'
            f'<div class="flex items-center justify-between mb-2">'
            f'<span class="mono text-xs text-indigo-400">#{str(i+1).zfill(2)} · ESP</span>'
            f'<span class="mono text-xs">{badge}</span></div>'
            f'<h2 class="font-black text-white text-base leading-snug mb-2">{title}</h2>'
            f'<p class="mono text-xs text-slate-500 leading-relaxed">{p1}</p>'
            f'</a></li>'
        )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <meta name="description" content="SolarisNews Intelligence Hub — Noticias geopolíticas de España en tiempo real, 24/7."/>
  <title>SolarisNews Intelligence Hub | Última Hora España</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body{{background:#050505;}}
    .mono{{font-family:'Courier New',Courier,monospace;}}
    .neon{{color:#6366f1;text-shadow:0 0 12px #6366f188;}}
    .card-border{{border:1px solid #1e1b4b;box-shadow:0 0 20px #6366f110;}}
    .grid-dash{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:1rem;}}
  </style>
</head>
<body class="text-white font-sans min-h-screen">

  <nav style="background:#08080f;border-bottom:1px solid #1e1b4b;"
       class="px-6 py-4 flex items-center justify-between sticky top-0 z-50">
    <div>
      <span class="neon font-black text-2xl mono tracking-widest">◈ SOLARIS<span class="text-white">NEWS</span></span>
      <p class="mono text-xs text-slate-600 mt-0.5">INTELLIGENCE HUB · ESPAÑA</p>
    </div>
    <div class="text-right hidden sm:block">
      <p class="mono text-xs text-indigo-400">{now}</p>
      <p class="mono text-xs text-green-400 animate-pulse">● SISTEMA ACTIVO</p>
    </div>
  </nav>

  <div class="flex justify-center py-3" style="background:#08080f;border-bottom:1px solid #1e1b4b;">
    <script type="text/javascript" src="//pl{ad}.highperformancegate.com/{ad}/invoke.js"></script>
  </div>

  <header class="text-center py-12 px-4" style="background:linear-gradient(180deg,#0d0d1a 0%,#050505 100%);">
    <p class="mono text-xs text-indigo-400 tracking-widest mb-3 animate-pulse">◉ MONITORIZACIÓN EN TIEMPO REAL ACTIVADA</p>
    <h1 class="text-5xl sm:text-6xl font-black mb-3"
        style="background:linear-gradient(90deg,#6366f1,#a5b4fc,#fff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">
      SolarisNews
    </h1>
    <p class="text-slate-400 text-sm mono">Portal de inteligencia geopolítica · {len(trends)} eventos activos</p>
    <p class="mono text-xs text-slate-600 mt-2">ACTUALIZADO: <span id="ts"></span></p>
  </header>

  <div class="flex justify-center my-4">
    <script type="text/javascript" src="//pl{ad}.highperformancegate.com/{ad}/invoke.js"></script>
  </div>

  <main class="max-w-6xl mx-auto px-4 pb-16">
    <div class="flex items-center gap-3 mb-6">
      <span class="mono text-xs text-red-400 border border-red-900 px-2 py-1 rounded">◉ EN DIRECTO</span>
      <span class="mono text-xs text-slate-600">{len(trends)} INFORMES ACTIVOS · NODO ES-INTEL-01</span>
    </div>
    <ul class="grid-dash">{cards}</ul>
  </main>

  <footer class="mono text-center text-xs py-8" style="border-top:1px solid #1e1b4b;color:#2d2b55;">
    © {datetime.now().year} SOLARISNEWS INTELLIGENCE HUB · SISTEMA AUTÓNOMO · ESPAÑA
  </footer>

  <script type="text/javascript" src="//pl{ad}.highperformancegate.com/{ad}/invoke.js"></script>
  <script>document.getElementById("ts").textContent = new Date().toLocaleString("es-ES");</script>
</body>
</html>"""

# ── GitHub Actions 24/7 ───────────────────────────────────────────────────────

def upload_workflow(cfg):
    workflow = b"""\
name: SolarisNews 24/7
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
        with:
          python-version: '3.11'
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
          import json, os
          cfg = {
            "github_token": os.environ["ORACLE_TOKEN"],
            "github_user":  os.environ["ORACLE_USER"],
            "repo_name":    os.environ["ORACLE_REPO"],
            "webhook_url":  os.environ["ORACLE_WEBHOOK"],
            "ad_unit_id":   os.environ["ORACLE_AD_ID"],
            "cpa_link":     os.environ["ORACLE_CPA"],
            "paypal_email": os.environ["ORACLE_PAYPAL"],
            "payout_method":"paypal",
          }
          open("config.json","w").write(json.dumps(cfg))
          PYEOF
      - run: python astral_oracle.py --once
"""
    path = ".github/workflows/solarisnews.yml"
    api  = (f"https://api.github.com/repos/{cfg['github_user']}"
            f"/{cfg['repo_name']}/contents/{path}")
    r = requests.get(api, headers=_gh(cfg["github_token"]), timeout=15)
    payload = {"message": "v4: 24/7 workflow",
               "content": base64.b64encode(workflow).decode()}
    if r.status_code == 200:
        payload["sha"] = r.json()["sha"]
    r2 = requests.put(api, headers=_gh(cfg["github_token"]), json=payload, timeout=15)
    if r2.status_code in (200, 201):
        log.info("✅ Workflow 24/7 subido — Actions cada 30 min sin tu ordenador.")
    else:
        log.warning("Workflow: %s %s", r2.status_code, r2.text[:100])

def upload_self(cfg):
    if _push("astral_oracle.py", Path(__file__).read_bytes(), cfg):
        log.info("✅ astral_oracle.py v4 subido al repo.")

# ── Ciclo ─────────────────────────────────────────────────────────────────────

def rotate_log(max_lines=100):
    """Mantiene oracle.log con máximo 100 líneas para no saturar el disco."""
    log_path = Path("oracle.log")
    if not log_path.exists():
        return
    lines = log_path.read_text(errors="replace").splitlines()
    if len(lines) > max_lines:
        log_path.write_text("\n".join(lines[-max_lines:]) + "\n")


def run_once(cfg):
    rotate_log()
    log.info("═══ SOLARIS v4.0 — CYCLE START ═══")
    if not ensure_setup(cfg):
        log.error("Setup falló — abortando.")
        return
    ensure_ads_txt(cfg)   # blindaje por ciclo
    trends = get_trends()
    log.info("Tendencias: %d", len(trends))
    _push("index.html", build_home(trends, cfg).encode(), cfg)
    publicadas = 0
    for t in trends:
        try:
            ok = _push(f"{t['slug']}/index.html", build_article(t, cfg).encode(), cfg)
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
    log.info("═══ CICLO COMPLETADO: %d/20 ═══", publicadas)

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
    log.info("═══ SOLARIS v4.0 — MODO LOCAL — CONFIGURANDO 24/7 ═══")
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
