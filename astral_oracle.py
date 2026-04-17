#!/usr/bin/env python3
import base64, json, logging, re, sys, time, requests
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler("oracle.log"), logging.StreamHandler()]
)
log = logging.getLogger("solarisnews")

CONFIG_PATH   = Path("config.json")
CYCLE_SECONDS = 3600
RETRY_SECONDS = 30

# ── Helpers ───────────────────────────────────────────────────────────────────

def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50]

def _gh(token):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

# ── RSS / Trends ──────────────────────────────────────────────────────────────

def _fetch_rss(url):
    r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "xml")
    out  = []
    for item in soup.find_all("item"):
        title_tag = item.find("title")
        if not title_tag:
            continue
        title = title_tag.text.strip()
        desc_tag = item.find("description")
        desc = ""
        if desc_tag:
            desc = BeautifulSoup(desc_tag.text, "html.parser").get_text()[:400].strip()
        if not desc:
            desc = "Ampliando información sobre este suceso en España."
        link_tag = item.find("link")
        link = link_tag.text.strip() if link_tag else "#"
        out.append({"title": title, "slug": _slug(title), "body": desc, "link": link})
    return out

def get_trends():
    sources = [
        "https://www.abc.es/rss/2.0/espana/",
        "https://www.20minutos.es/rss/",
        "https://www.elconfidencial.com/rss/espana/",
        "https://trends.google.com/trends/trendingsearches/daily/rss?geo=ES",
    ]
    all_trends = []
    for url in sources:
        try:
            all_trends.extend(_fetch_rss(url))
        except Exception as exc:
            log.warning("RSS %s falló: %s", url, exc)
    if not all_trends:
        # Fallback garantizado
        return [
            {"title": "Precio Luz Hoy España",      "slug": "precio-luz-hoy",      "body": "Consulta el precio de la electricidad en tiempo real.", "link": "#"},
            {"title": "Resultado Real Madrid Hoy",   "slug": "resultado-real-madrid","body": "Últimas noticias y resultado del partido.",             "link": "#"},
            {"title": "Ofertas Amazon España",       "slug": "ofertas-amazon",       "body": "Las mejores ofertas del día seleccionadas para ti.",    "link": "#"},
        ]
    seen = set()
    return [x for x in all_trends if not (x["slug"] in seen or seen.add(x["slug"]))][:20]

# ── GitHub ────────────────────────────────────────────────────────────────────

def _push(path, content_bytes, cfg, retries=3):
    token = cfg["github_token"]
    api   = f"https://api.github.com/repos/{cfg['github_user']}/{cfg['repo_name']}/contents/{path}"
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(api, headers=_gh(token), timeout=15)
            payload = {
                "message": f"oracle: {path}",
                "content": base64.b64encode(content_bytes).decode(),
            }
            if r.status_code == 200:
                payload["sha"] = r.json()["sha"]
            r2 = requests.put(api, headers=_gh(token), json=payload, timeout=20)
            if r2.status_code in (200, 201):
                return True
            log.warning("push [%s] %s: %s", path, r2.status_code, r2.text[:100])
            return False
        except requests.RequestException as exc:
            if attempt < retries:
                time.sleep(5 * attempt)
            else:
                log.warning("push [%s] falló tras %d intentos: %s", path, retries, exc)
    return False

def ensure_github_setup(cfg):
    token = cfg["github_token"]
    user  = cfg["github_user"]
    repo  = cfg["repo_name"]
    base  = f"https://api.github.com/repos/{user}/{repo}"

    # Crear repo si no existe
    r = requests.get(base, headers=_gh(token), timeout=15)
    if r.status_code == 404:
        r2 = requests.post(
            "https://api.github.com/user/repos",
            headers=_gh(token),
            json={"name": repo, "private": False, "auto_init": True},
            timeout=15,
        )
        if r2.status_code in (200, 201):
            log.info("Repo creado. Esperando 8 s...")
            time.sleep(8)
        else:
            log.error("No se pudo crear el repo: %s", r2.text[:150])
            return False

    # Activar Pages
    rp = requests.post(
        f"{base}/pages",
        headers=_gh(token),
        json={"source": {"branch": "main", "path": "/"}},
        timeout=15,
    )
    if rp.status_code in (200, 201):
        log.info("GitHub Pages activado.")
    elif rp.status_code in (409, 422):
        log.info("GitHub Pages ya estaba activo.")
    else:
        log.warning("Pages API %s: %s", rp.status_code, rp.text[:100])

    # ads.txt — imprescindible para que Adsterra pague
    ads_api = f"{base}/contents/ads.txt"
    if requests.get(ads_api, headers=_gh(token), timeout=15).status_code != 200:
        content = f"adsterra.com, {cfg['ad_unit_id']}, DIRECT\n"
        r3 = requests.put(
            ads_api, headers=_gh(token), timeout=15,
            json={"message": "oracle: ads.txt", "content": base64.b64encode(content.encode()).decode()},
        )
        log.info("ads.txt %s", "✅ creado" if r3.status_code in (200, 201) else f"FALLÓ {r3.status_code}")

    return True

# ── HTML builders ─────────────────────────────────────────────────────────────

def build_article_html(trend, cfg):
    ad_id  = cfg["ad_unit_id"]
    cpa    = cfg["cpa_link"]
    title  = trend["title"].replace('"', "&quot;").replace("<", "&lt;")
    body   = trend["body"].replace("<", "&lt;")
    link   = trend["link"]
    canon  = f"https://{cfg['github_user']}.github.io/{cfg['repo_name']}/{trend['slug']}/"
    now    = datetime.now().strftime("%-d de %B de %Y · %H:%M")

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <meta name="description" content="{title}. Última hora en SolarisNews."/>
  <meta property="og:title" content="{title} | SolarisNews"/>
  <meta property="og:type" content="article"/>
  <link rel="canonical" href="{canon}"/>
  <title>{title} | SolarisNews</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-white font-sans min-h-screen">

  <header class="bg-slate-900 border-b border-slate-800 px-4 py-3 flex items-center justify-between">
    <a href="../" class="text-indigo-400 font-black text-xl">⚡ SolarisNews</a>
    <span class="text-slate-500 text-xs">{now}</span>
  </header>

  <!-- Adsterra Social Bar TOP -->
  <div class="flex justify-center py-2 bg-slate-900 border-b border-slate-800">
    <script type="text/javascript" src="//pl{ad_id}.highperformancegate.com/{ad_id}/invoke.js"></script>
  </div>

  <main class="max-w-2xl mx-auto px-4 py-8">
    <p class="text-indigo-400 text-xs font-bold uppercase tracking-widest mb-3">🔴 Última hora · España</p>
    <h1 class="text-3xl font-black text-white leading-tight mb-4">{title}</h1>
    <p class="text-slate-500 text-xs mb-6 pb-4 border-b border-slate-800">
      📰 SolarisNews · <span id="ts"></span>
    </p>

    <p class="text-slate-300 text-lg leading-relaxed mb-4">{body}</p>
    <p class="text-slate-400 leading-relaxed mb-6">
      Miles de personas buscan información sobre este tema ahora mismo en España.
      SolarisNews recopila automáticamente las noticias más relevantes del momento.
    </p>

    <a href="{link}" target="_blank" rel="noopener"
       class="text-indigo-400 font-bold hover:underline text-sm block mb-8">
      → Leer la crónica completa en la fuente original
    </a>

    <!-- Adsterra Social Bar MID -->
    <div class="flex justify-center my-6">
      <script type="text/javascript" src="//pl{ad_id}.highperformancegate.com/{ad_id}/invoke.js"></script>
    </div>

    <!-- CPA Amazon -->
    <div class="bg-gradient-to-r from-orange-500 to-yellow-500 p-px rounded-2xl mb-8">
      <div class="bg-slate-950 p-6 rounded-2xl text-center">
        <p class="font-bold text-lg mb-1">🛒 Ofertas del día en Amazon</p>
        <p class="text-slate-400 text-sm mb-4">Descuentos exclusivos seleccionados por SolarisNews</p>
        <a href="{cpa}" target="_blank" rel="noopener"
           class="bg-orange-500 hover:bg-orange-400 text-white px-8 py-3 rounded-xl font-bold text-lg transition inline-block">
          Ver ofertas →
        </a>
      </div>
    </div>

    <div class="border-t border-slate-800 pt-6">
      <a href="../" class="text-indigo-400 hover:text-indigo-300 text-sm">← Volver a todas las noticias</a>
    </div>
  </main>

  <footer class="text-center text-slate-700 text-xs py-8 mt-4 border-t border-slate-900">
    © {datetime.now().year} SolarisNews · Portal automatizado · España
  </footer>

  <!-- Adsterra Social Bar STICKY -->
  <script type="text/javascript" src="//pl{ad_id}.highperformancegate.com/{ad_id}/invoke.js"></script>
  <script>document.getElementById("ts").textContent = new Date().toLocaleString("es-ES");</script>
</body>
</html>"""


def build_home_html(trends, cfg):
    ad_id = cfg["ad_unit_id"]
    cards = "".join([
        f'<li><a href="./{t["slug"]}/" '
        f'class="flex items-start gap-3 bg-slate-900 border border-slate-800 p-4 '
        f'rounded-2xl hover:border-indigo-500 hover:bg-slate-800 transition">'
        f'<span class="text-indigo-400 text-lg mt-0.5 shrink-0">📰</span>'
        f'<span class="text-slate-200 text-sm font-medium leading-snug">{t["title"]}</span>'
        f'</a></li>'
        for t in trends
    ])
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <meta name="description" content="SolarisNews — Noticias de última hora en España, actualizadas automáticamente 24/7."/>
  <title>SolarisNews | Última Hora España</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-white font-sans min-h-screen">

  <!-- Adsterra Social Bar TOP -->
  <div class="flex justify-center py-2 bg-slate-900 border-b border-slate-800">
    <script type="text/javascript" src="//pl{ad_id}.highperformancegate.com/{ad_id}/invoke.js"></script>
  </div>

  <header class="text-center py-10 px-4">
    <h1 class="text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400 mb-2">
      ⚡ SolarisNews
    </h1>
    <p class="text-slate-500 text-sm">Última hora en España · Actualizado automáticamente 24/7</p>
    <p class="text-slate-600 text-xs mt-1">Actualizado: <span id="ts"></span></p>
  </header>

  <div class="flex justify-center mb-6">
    <script type="text/javascript" src="//pl{ad_id}.highperformancegate.com/{ad_id}/invoke.js"></script>
  </div>

  <main class="max-w-2xl mx-auto px-4 pb-16">
    <p class="text-xs font-bold uppercase tracking-widest text-slate-500 mb-4">🔴 En directo ahora</p>
    <ul class="space-y-3">{cards}</ul>
  </main>

  <footer class="text-center text-slate-700 text-xs py-8 border-t border-slate-900">
    © {datetime.now().year} SolarisNews · Noticias automatizadas · España
  </footer>

  <script type="text/javascript" src="//pl{ad_id}.highperformancegate.com/{ad_id}/invoke.js"></script>
  <script>document.getElementById("ts").textContent = new Date().toLocaleString("es-ES");</script>
</body>
</html>"""

# ── GitHub Actions workflow (24/7 sin ordenador) ──────────────────────────────

def upload_actions_workflow(cfg):
    workflow = b"""\
name: SolarisNews 24/7

on:
  schedule:
    - cron: '0 */3 * * *'
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

      - name: Crear config.json
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
            "github_token":  os.environ["ORACLE_TOKEN"],
            "github_user":   os.environ["ORACLE_USER"],
            "repo_name":     os.environ["ORACLE_REPO"],
            "webhook_url":   os.environ["ORACLE_WEBHOOK"],
            "ad_unit_id":    os.environ["ORACLE_AD_ID"],
            "cpa_link":      os.environ["ORACLE_CPA"],
            "paypal_email":  os.environ["ORACLE_PAYPAL"],
            "payout_method": "paypal",
          }
          open("config.json", "w").write(json.dumps(cfg))
          PYEOF

      - run: python astral_oracle.py --once
"""
    path = ".github/workflows/solarisnews.yml"
    api  = f"https://api.github.com/repos/{cfg['github_user']}/{cfg['repo_name']}/contents/{path}"
    r    = requests.get(api, headers=_gh(cfg["github_token"]), timeout=15)
    payload = {"message": "oracle: 24/7 Actions workflow", "content": base64.b64encode(workflow).decode()}
    if r.status_code == 200:
        payload["sha"] = r.json()["sha"]
    r2 = requests.put(api, headers=_gh(cfg["github_token"]), json=payload, timeout=15)
    if r2.status_code in (200, 201):
        log.info("✅ Workflow 24/7 subido. GitHub Actions correrá el bot sin tu ordenador.")
        log.info("   Añade los Secrets en: https://github.com/%s/%s/settings/secrets/actions",
                 cfg["github_user"], cfg["repo_name"])
    else:
        log.warning("Workflow upload %s: %s", r2.status_code, r2.text[:150])

def upload_script_to_repo(cfg):
    content = Path(__file__).read_bytes()
    _push("astral_oracle.py", content, cfg)
    log.info("✅ astral_oracle.py subido al repo.")

# ── Ciclo principal ───────────────────────────────────────────────────────────

def run_once(cfg):
    log.info("=== SOLARIS NEWS CYCLE START ===")
    if not ensure_github_setup(cfg):
        log.error("Setup GitHub falló — abortando ciclo.")
        return
    trends = get_trends()
    log.info("Tendencias obtenidas: %d", len(trends))
    _push("index.html", build_home_html(trends, cfg).encode(), cfg)
    publicadas = 0
    for t in trends:
        try:
            ok = _push(f"{t['slug']}/index.html", build_article_html(t, cfg).encode(), cfg)
            cpa = cfg["cpa_link"]
            redir = (
                f'<!DOCTYPE html><html><head><meta charset="UTF-8"/>'
                f'<meta http-equiv="refresh" content="0;url={cpa}"/>'
                f'</head><body><script>window.location.replace("{cpa}");</script></body></html>'
            )
            _push(f"{t['slug']}/go/index.html", redir.encode(), cfg)
            if ok:
                publicadas += 1
                log.info("✅ PUBLICADO: %s", t["slug"])
        except Exception as exc:
            log.warning("Error en '%s': %s", t["slug"], exc)
        time.sleep(1)
    log.info("Ciclo completado. %d/%d publicadas.", publicadas, len(trends))


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

    # Modo local: sube workflow+script al repo y arranca bucle
    log.info("=== SOLARIS NEWS 24/7 MODE ===")
    upload_script_to_repo(cfg)
    upload_actions_workflow(cfg)
    log.info("Bot configurado en GitHub Actions. Desde ahora corre sin este ordenador.")

    while True:
        try:
            run_once(cfg)
            log.info("Durmiendo %ds...", CYCLE_SECONDS)
            time.sleep(CYCLE_SECONDS)
        except KeyboardInterrupt:
            log.info("Detenido.")
            sys.exit(0)
        except Exception as exc:
            log.error("Error inesperado: %s — reintentando en %ds", exc, RETRY_SECONDS)
            time.sleep(RETRY_SECONDS)


if __name__ == "__main__":
    main()
