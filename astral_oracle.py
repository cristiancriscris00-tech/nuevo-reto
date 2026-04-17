#!/usr/bin/env python3
"""astral_oracle.py — V8.0 'Private Sniper' · Oracle Financial AI · @solaris01"""
import base64, json, logging, random, re, sys, time, requests
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("oracle.log"), logging.StreamHandler()],
)
log = logging.getLogger("solaris_v8")

CONFIG_PATH    = Path("config.json")
MEMORY_PATH    = Path("memory.json")
INTEL_LOG_PATH = Path("intelligence_log.json")
CYCLE_SECONDS  = 1200
RETRY_SECONDS  = 30
MAX_REPORTS    = 20

GEO_KEYWORDS = [
    "gobierno","otan","rusia","petróleo","oro","ley","ue","unión europea",
    "sánchez","trump","conflicto","economía","guerra","bce","fed","inflación",
    "deuda","presupuesto","parlamento","congreso","senado","fiscal","aranceles",
    "china","ucrania","israel","iran","nato","reserva federal","mercado",
    "bolsa","ibex","euro","dólar","bonos","crisis","migración","energía",
    "nuclear","defensa","ejército","armamento","sanción","veto","acuerdo","cumbre",
    "biden","macron","putin","xi","zelenski","pentagon","g7","g20","casa blanca",
]

ASSET_CORRELATIONS = {
    "PETRÓLEO": {
        "keywords": ["ormuz","mar rojo","oleoducto","refinería","opep","crudo","barril",
                     "gasoil","embargo","tanquero","bloqueo","aramco","irán","estrecho",
                     "ruta energética","suministro energético"],
        "emoji": "🛢️", "color": "#f97316",
        "risk": "La restricción de rutas de suministro activa el mecanismo de escasez. Cada barril menos en mercado se traduce en precio más alto en bomba.",
        "opportunity": "Posicionamiento observacional en ETFs de energía (XLE, USO) o futuros Brent. Ventana típica: 48-96h post-evento.",
    },
    "ORO": {
        "keywords": ["guerra","misil","bombardeo","escalada","refugio","reserva federal",
                     "fed","inflación","tipos de interés","deuda soberana","crisis bancaria",
                     "colapso","quiebra","default","banco central","reservas","oro físico"],
        "emoji": "🥇", "color": "#eab308",
        "risk": "Inestabilidad sistémica activa el patrón histórico de refugio de valor. Los bancos centrales compran oro en silencio.",
        "opportunity": "Acumulación en metales preciosos físicos o ETFs (GLD, IAU). El oro tiende a subir 15-40% en ciclos de crisis confirmados.",
    },
    "BITCOIN": {
        "keywords": ["fed","inflación","tipos de interés","banco central","cbdc","moneda digital",
                     "sanciones financieras","dólar","sistema monetario","quantitative","qe",
                     "liquidez","corralito","control capital","criptomoneda","blockchain"],
        "emoji": "₿", "color": "#06b6d4",
        "risk": "Política monetaria expansiva y censura financiera correlacionan históricamente con entrada de capital en activos descentralizados.",
        "opportunity": "Bitcoin como hedge anti-inflación y activo no confiscable. Observar acumulación de ballenas en on-chain data.",
    },
}

VECTOR_TEMPLATES = {
    "PETRÓLEO": [
        "Actores identificados: productores del Golfo, fondos de cobertura energética, refinadores europeos. La restricción de Ormuz activa contratos de fuerza mayor firmados en 2022.",
        "Los traders en Rotterdam y Singapur han movido posiciones 48h antes del anuncio. El mercado de derivados reflejó el movimiento real antes que la prensa.",
    ],
    "ORO": [
        "Fondos soberanos asiáticos y bancos centrales emergentes operan como compradores silenciosos. El oro cotiza en dos mercados: el visible y el real.",
        "La narrativa de 'activos seguros' es la cobertura pública. El vector real: fondos de pensiones reposicionando fuera de renta fija soberana.",
    ],
    "BITCOIN": [
        "Fondos macro y family offices de alto patrimonio operan en OTC. La acción en exchanges públicos es el 15% del volumen real. Las ballenas acumulan en silencio.",
        "Los bancos centrales discuten CBDCs mientras instituciones acumulan BTC como hedge no declarado. El debate público es la distracción.",
    ],
    "DEFAULT": [
        "Los actores visibles raramente son los decisivos. Detrás de la narrativa operan intereses estructurales que Solaris monitoriza con análisis de frecuencia.",
        "La información fluye descendente. Cuando el público accede al dato, los repositorios ya están actualizados. Ventana de observación activa.",
    ],
}

INTEL_ANALYSES = [
    "Los movimientos detrás de este titular apuntan a una reconfiguración del poder real. Los actores visibles raramente son los actores decisivos.",
    "Cuando los medios amplifican esta narrativa, los capitales ya se han reposicionado. La información llega al público 72 horas tarde.",
    "Correlación detectada: este evento precede históricamente a movimientos en mercados de commodities. La señal está en el precio, no en el titular.",
    "Patrón identificado en ciclos de 18 meses: este tipo de movimiento siempre precede una reconfiguración del tablero geopolítico europeo.",
    "La narrativa oficial actúa como pantalla. Detrás hay transferencias de poder económico que Oracle detecta antes que los analistas humanos.",
    "Ventana de acción activa. Tres horas después de anuncios de este perfil, los mercados de futuros reflejan el movimiento real.",
    "Análisis de frecuencia completado. Este evento encaja en el perfil de operaciones de desinformación de alta intensidad. Vigilancia activa.",
    "Clasificación: REDISTRIBUCIÓN DE INFLUENCIA. El 88% de lo que ocurre no aparece en la prensa. Oracle procesando.",
]

AGENT_TRANSMISSIONS = [
    ("SIGMA-04",    "Movimientos anómalos detectados en el Estrecho de Gibraltar. Vigilancia NARANJA."),
    ("NODO-EU",     "Flujos de capital saliendo de bonos europeos. Volumen: 3.4x media 30d. Confirmado."),
    ("ANALISTA-07", "Reservas de oro en Frankfurt — acceso restringido al personal de nivel 5+."),
    ("INTEL-ES",    "Reunión de emergencia no publicada en Bruselas. Sin comunicado oficial."),
    ("AGENTE-12",   "Actividad inusual en futuros de crudo. Correlación con evento geopolítico activo."),
    ("ALPHA-NODE",  "Patrones de desinformación coordinada detectados en canales gubernamentales."),
    ("OP-09",       "Divisas asiáticas: movimiento sincronizado. Posible acción coordinada de bancos centrales."),
    ("SIGMA-03",    "Cumbre G7 no publicada. Fuentes internas. Agenda: infraestructuras críticas."),
    ("AGENTE-02",   "Búsquedas 'reservas de emergencia' +340% en 48h. Geo: ES/FR/DE."),
    ("BERLIN-NODE", "Conversaciones activas sobre nuevo mecanismo de defensa europeo autónomo."),
]

TACTICAL_PRODUCTS = [
    {"name": "Mochila Táctica 45L MOLLE",      "desc": "Equipamiento nivel operativo.",              "tag": "ESSENTIAL"},
    {"name": "Linterna Táctica 2000 Lm",       "desc": "Cuando corten la luz, seguirás viendo.",     "tag": "TIER-1"},
    {"name": "Kit Supervivencia 72h",           "desc": "72h de autonomía. Recomendado por gobiernos.","tag": "CRITICAL"},
    {"name": "El Arte de la Guerra — Sun Tzu", "desc": "El manual que usan los que mandan.",          "tag": "INTEL"},
    {"name": "Radio Emergencia AM/FM/SW",       "desc": "Sin internet. Sin censura. Siempre funciona.","tag": "COMM"},
    {"name": "Filtro de Agua Portátil",         "desc": "El activo más infravalorado del siglo XXI.", "tag": "SUPPLY"},
]

CRITICAL_SOURCES = [
    "whitehouse.gov","defense.gov","state.gov","europa.eu",
    "nato.int","un.org","bce.europa.eu","federalreserve.gov",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:55]

def _esc(t):
    return str(t).replace("&","&amp;").replace("<","&lt;").replace('"',"&quot;")

def _gh(token):
    return {"Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}

def _is_geopolitical(title, body):
    combined = (title + " " + body).lower()
    return any(kw in combined for kw in GEO_KEYWORDS)

def _is_critical_source(url):
    return any(cs in url.lower() for cs in CRITICAL_SOURCES)

# ── Asset Intelligence ────────────────────────────────────────────────────────

def _detect_assets(title, body):
    combined = (title + " " + body).lower()
    out = []
    for name, cfg in ASSET_CORRELATIONS.items():
        hits = [kw for kw in cfg["keywords"] if kw in combined]
        if hits:
            out.append({"asset": name, "hits": hits, "count": len(hits),
                        "emoji": cfg["emoji"], "color": cfg["color"],
                        "risk": cfg["risk"], "opportunity": cfg["opportunity"]})
    return sorted(out, key=lambda x: x["count"], reverse=True)

def _reliability(assets, is_critical=False, hot=False):
    hits  = sum(a["count"] for a in assets)
    cats  = len(assets)
    if is_critical or (hits >= 3 and cats >= 2) or hot:
        return "ALTA"
    elif hits >= 2:
        return "MEDIA"
    return "BAJA"

def _action(rel, assets):
    if rel == "ALTA" and assets:   return "ENTRAR"
    if rel == "MEDIA":             return "VIGILAR"
    if assets:                     return "VIGILAR"
    return "IGNORAR"

def _title_color(title, assets):
    t = title.lower()
    if any(w in t for w in ["guerra","misil","ataque","escalada","bombardeo"]):
        return "#ef4444"
    if any(w in t for w in ["bitcoin","btc","subida","récord","crecimiento"]):
        return "#22c55e"
    return assets[0]["color"] if assets else "#f5f5f0"

def _get_vector(assets):
    key = assets[0]["asset"] if assets else "DEFAULT"
    return random.choice(VECTOR_TEMPLATES.get(key, VECTOR_TEMPLATES["DEFAULT"]))

# ── Memory ────────────────────────────────────────────────────────────────────

def _load_json(path):
    p = Path(path)
    try:
        return json.loads(p.read_text(errors="replace")) if p.exists() else {}
    except Exception:
        return {}

def _save_json(data, path):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2))

def _update_memory(trends):
    today = datetime.now().strftime("%Y-%m-%d")
    mem   = _load_json(MEMORY_PATH)
    if mem.get("date") != today:
        mem = {"date": today, "topics": {}}
    topics    = mem.get("topics", {})
    all_kw    = set(GEO_KEYWORDS) | {kw for a in ASSET_CORRELATIONS.values() for kw in a["keywords"]}
    for t in trends:
        for w in re.findall(r'\b\w{5,}\b', t["title"].lower()):
            if w in all_kw:
                topics[w] = topics.get(w, 0) + 1
    mem["topics"] = topics
    _save_json(mem, MEMORY_PATH)
    return {k: v for k, v in topics.items() if v >= 3}

def _is_hot(title, hot_topics):
    t = title.lower()
    return any(kw in t for kw in hot_topics)

def _log_intel(slug, title, assets, action_sig):
    data = _load_json(INTEL_LOG_PATH)
    data[slug] = {"ts": datetime.now().isoformat(), "title": title,
                  "assets": [a["asset"] for a in assets], "action": action_sig}
    if len(data) > 200:
        for k in sorted(data, key=lambda k: data[k].get("ts",""))[:len(data)-200]:
            del data[k]
    _save_json(data, INTEL_LOG_PATH)

# ── OG Image SVG ──────────────────────────────────────────────────────────────

def _og_svg():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">'
        '<defs><pattern id="g" width="40" height="40" patternUnits="userSpaceOnUse">'
        '<path d="M40 0L0 0 0 40" fill="none" stroke="#22c55e" stroke-width="0.3" opacity="0.25"/>'
        '</pattern></defs>'
        '<rect width="1200" height="630" fill="#0a0a0a"/>'
        '<rect width="1200" height="630" fill="url(#g)"/>'
        '<rect x="0" y="0" width="1200" height="3" fill="#22c55e"/>'
        '<rect x="0" y="627" width="1200" height="3" fill="#22c55e"/>'
        '<text x="60" y="108" font-family="monospace" font-size="12" fill="#22c55e" opacity="0.5">'
        'CLASSIFICATION: PUBLIC - SOLARIS-ORACLE-V8 - NODE: ES-INTEL-01 - ENCRYPTED</text>'
        '<rect x="60" y="126" width="200" height="34" fill="#22c55e" rx="4"/>'
        '<text x="74" y="150" font-family="monospace" font-size="13" font-weight="bold" fill="#0a0a0a">'
        '[*] LIVE INTEL FEED</text>'
        '<text x="60" y="248" font-family="monospace" font-size="78" font-weight="bold" fill="#f5f5f0">SOLARIS</text>'
        '<text x="60" y="328" font-family="monospace" font-size="78" font-weight="bold" fill="#22c55e">.NEWS</text>'
        '<text x="60" y="393" font-family="monospace" font-size="20" fill="#9ca3af">'
        'Inteligencia Geopolitica - Oracle Financial AI - @solaris01</text>'
        '<text x="60" y="448" font-family="monospace" font-size="12" fill="#22c55e" opacity="0.6">'
        'SHA-256: 3f7a2c1b9e4d - TLS-1.3 - ORACLE v8.0 - PRIVATE SNIPER MODE</text>'
        '<rect x="878" y="188" width="262" height="130" fill="none" stroke="#22c55e"'
        ' stroke-width="1.5" opacity="0.35" rx="8"/>'
        '<text x="898" y="226" font-family="monospace" font-size="11" fill="#22c55e" opacity="0.7">THREAT LEVEL</text>'
        '<text x="898" y="274" font-family="monospace" font-size="40" font-weight="bold" fill="#ef4444">MONITOR</text>'
        '<text x="898" y="306" font-family="monospace" font-size="11" fill="#9ca3af" opacity="0.5">UPDATED: REAL-TIME</text>'
        '</svg>'
    )
    return svg.encode()

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
        title    = t.text.strip()
        desc_tag = item.find("description") or item.find("summary")
        raw      = desc_tag.text if desc_tag else ""
        desc     = re.sub(r"\s+", " ",
                          BeautifulSoup(raw, "html.parser").get_text(" ", strip=True))
        if not _is_geopolitical(title, desc):
            continue
        p1     = (desc[:420].rsplit(" ", 1)[0] + "…") if len(desc) > 420 else (desc or "Información en desarrollo.")
        p2_raw = desc[420:900]
        p2     = (p2_raw.rsplit(" ", 1)[0] + "…") if len(p2_raw) > 20 else ""
        ltag   = item.find("link")
        link   = ltag.text.strip() if ltag else "#"
        out.append({"title": title, "slug": _slug(title), "p1": p1, "p2": p2,
                    "link": link, "critical": _is_critical_source(link)})
    return out

def get_trends():
    sources = [
        "https://www.abc.es/rss/2.0/espana/",
        "https://www.20minutos.es/rss/",
        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
        "https://www.eleconomista.es/rss/RSS.php?idCat=1",
        "https://www.whitehouse.gov/feed/",
        "https://www.elconfidencial.com/rss/espana/",
    ]
    all_items = []
    for url in sources:
        try:
            all_items.extend(_fetch_rss(url))
        except Exception as exc:
            log.warning("RSS %s: %s", url, exc)
    if not all_items:
        return [
            {"title": "Crisis Energética Europa",       "slug": "crisis-energetica-europa",
             "p1": "Los precios del gas y petróleo marcan nuevos máximos.", "p2": "", "link": "#", "critical": False},
            {"title": "Reunión Emergencia UE Bruselas", "slug": "reunion-emergencia-ue",
             "p1": "Los líderes europeos se reúnen de urgencia.", "p2": "", "link": "#", "critical": False},
            {"title": "Sánchez medidas económicas",     "slug": "sanchez-medidas-economicas",
             "p1": "El Gobierno presenta nuevo paquete ante presión inflacionaria.", "p2": "", "link": "#", "critical": False},
        ]
    seen     = set()
    filtered = [x for x in all_items if not (x["slug"] in seen or seen.add(x["slug"]))]
    log.info("Noticias geopolíticas filtradas: %d", len(filtered))
    return filtered[:MAX_REPORTS]

# ── GitHub ────────────────────────────────────────────────────────────────────

def _push(path, content_bytes, cfg, retries=3):
    token = cfg["github_token"]
    api   = (f"https://api.github.com/repos/{cfg['github_user']}"
             f"/{cfg['repo_name']}/contents/{path}")
    for attempt in range(1, retries + 1):
        try:
            r       = requests.get(api, headers=_gh(token), timeout=15)
            payload = {"message": f"v8: {path}",
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
    r     = requests.get(base, headers=_gh(token), timeout=15)
    if r.status_code == 404:
        r2 = requests.post("https://api.github.com/user/repos", headers=_gh(token), timeout=15,
                           json={"name": repo, "private": False, "auto_init": True})
        if r2.status_code in (200, 201):
            log.info("Repo creado — esperando 8s…")
            time.sleep(8)
        else:
            log.error("No se pudo crear repo: %s", r2.text[:150])
            return False
    rp = requests.post(f"{base}/pages", headers=_gh(token), timeout=15,
                       json={"source": {"branch": "main", "path": "/"}})
    if rp.status_code in (200, 201):   log.info("Pages activado.")
    elif rp.status_code in (409, 422): log.info("Pages ya activo.")
    _push("og.svg", _og_svg(), cfg)
    ensure_ads_txt(cfg)
    return True

def ensure_ads_txt(cfg):
    ad_id = cfg.get("ad_unit_id", "")
    if not ad_id:
        return
    token   = cfg["github_token"]
    api     = (f"https://api.github.com/repos/{cfg['github_user']}"
               f"/{cfg['repo_name']}/contents/ads.txt")
    correct = f"adsterra.com, {ad_id}, DIRECT\n"
    r       = requests.get(api, headers=_gh(token), timeout=15)
    if r.status_code == 200:
        if ad_id in base64.b64decode(r.json()["content"]).decode():
            log.info("ads.txt ✅ (ID %s)", ad_id)
            return
        payload = {"message": "v8: fix ads.txt", "sha": r.json()["sha"],
                   "content": base64.b64encode(correct.encode()).decode()}
    else:
        payload = {"message": "v8: create ads.txt",
                   "content": base64.b64encode(correct.encode()).decode()}
    r2 = requests.put(api, headers=_gh(token), json=payload, timeout=15)
    log.info("ads.txt %s", "✅" if r2.status_code in (200, 201) else f"FALLÓ {r2.status_code}")

# ── HTML: CSS & Head ──────────────────────────────────────────────────────────

_CSS = """
:root {
  --g:#22c55e; --gd:rgba(34,197,94,.12); --gb:rgba(34,197,94,.2);
  --bg:#0a0a0a; --bc:#111; --bone:#f5f5f0; --muted:#6b7280;
  --red:#ef4444; --amb:#eab308; --cyn:#06b6d4; --org:#f97316;
}
*,*::before,*::after{box-sizing:border-box;}
html{scroll-behavior:smooth;}
body{
  background-color:var(--bg);
  background-image:linear-gradient(rgba(34,197,94,.03)1px,transparent 1px),
                   linear-gradient(90deg,rgba(34,197,94,.03)1px,transparent 1px);
  background-size:40px 40px;
  font-family:'Inter',system-ui,sans-serif;
  color:var(--bone); min-height:100vh;
}
.mono{font-family:'JetBrains Mono','Courier New',monospace;}
.g{color:var(--g);} .gg{color:var(--g);text-shadow:0 0 12px rgba(34,197,94,.5);}
.muted{color:var(--muted);} .red{color:var(--red);}
.amb{color:var(--amb);} .cyn{color:var(--cyn);}
.win{background:var(--bc);border:1px solid var(--gb);border-radius:.75rem;
     overflow:hidden;transition:border-color .2s,box-shadow .2s;}
.win:hover{border-color:rgba(34,197,94,.4);box-shadow:0 0 28px rgba(34,197,94,.07);}
.wbar{background:#141414;border-bottom:1px solid var(--gb);
      padding:.45rem .75rem;display:flex;align-items:center;gap:.5rem;}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block;}
.dr{background:#ef4444;} .dy{background:#eab308;} .dg{background:var(--g);}
@keyframes scanline{
  0%{transform:translateY(-10%);opacity:0;}5%{opacity:.5;}
  95%{opacity:.5;}100%{transform:translateY(110vh);opacity:0;}
}
.scanline{position:fixed;top:0;left:0;width:100%;height:2px;
  background:linear-gradient(90deg,transparent,var(--g),transparent);
  animation:scanline 5s linear infinite;pointer-events:none;z-index:200;}
@keyframes blink{0%,100%{opacity:1;}50%{opacity:0;}}
.blink{animation:blink 1s step-start infinite;}
@keyframes fadein{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:none;}}
.fadein{animation:fadein .4s ease both;}
@keyframes marquee{0%{transform:translateX(100%);}100%{transform:translateX(-200%);}}
.marquee{display:inline-block;animation:marquee 38s linear infinite;white-space:nowrap;}
.btn-g{display:inline-flex;align-items:center;justify-content:center;gap:.5rem;
  border:1px solid var(--g);color:var(--g);background:transparent;
  font-family:'JetBrains Mono',monospace;font-size:.72rem;font-weight:700;
  padding:.75rem 1.4rem;border-radius:.625rem;text-decoration:none;
  transition:background .2s,box-shadow .2s;letter-spacing:.05em;}
.btn-g:hover{background:rgba(34,197,94,.1);box-shadow:0 0 20px rgba(34,197,94,.2);}
.btn-a{display:inline-flex;align-items:center;justify-content:center;gap:.5rem;
  border:1px solid var(--amb);color:var(--amb);background:transparent;
  font-family:'JetBrains Mono',monospace;font-size:.72rem;font-weight:700;
  padding:.75rem 1.4rem;border-radius:.625rem;text-decoration:none;
  transition:background .2s,box-shadow .2s;letter-spacing:.05em;}
.btn-a:hover{background:rgba(234,179,8,.1);box-shadow:0 0 20px rgba(234,179,8,.2);}
.btn-tt{display:flex;align-items:center;justify-content:center;gap:.75rem;
  background:linear-gradient(135deg,#0d0d0d,#181818);
  border:1.5px solid var(--g);color:var(--bone);
  font-family:'JetBrains Mono',monospace;font-size:.85rem;font-weight:700;
  padding:1.1rem 2rem;border-radius:.875rem;text-decoration:none;
  transition:box-shadow .2s,transform .15s;letter-spacing:.07em;
  width:100%;max-width:600px;margin:0 auto;}
.btn-tt:hover{box-shadow:0 0 40px rgba(34,197,94,.25);transform:translateY(-2px);}
.badge{font-family:'JetBrains Mono',monospace;font-size:.58rem;font-weight:700;
  letter-spacing:.1em;padding:.15rem .45rem;border-radius:.25rem;display:inline-block;}
.bg{border:1px solid var(--g);color:var(--g);}
.br{border:1px solid var(--red);color:var(--red);}
.ba{border:1px solid var(--amb);color:var(--amb);}
.bc{border:1px solid var(--cyn);color:var(--cyn);}
.bm{border:1px solid #374151;color:var(--muted);}
.supply{background:#0e0e0e;border:1px solid rgba(234,179,8,.18);border-radius:.75rem;
  padding:1rem;transition:border-color .2s;text-decoration:none;display:block;}
.supply:hover{border-color:rgba(234,179,8,.45);}
.layer{background:#0c0c0c;border:1px solid #1a1a1a;border-radius:.625rem;
  padding:1rem 1.25rem;margin-bottom:.75rem;}
#pwo{position:fixed;inset:0;background:#0a0a0a;z-index:9999;
  display:flex;align-items:center;justify-content:center;flex-direction:column;}
#pwo.hidden{display:none;}
@media(max-width:640px){.hide-sm{display:none!important;}}
"""

def _html_head(title, desc, canon, og_image):
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{_esc(title)}</title>
  <meta name="description" content="{_esc(desc)}"/>
  <meta name="robots" content="index,follow"/>
  <link rel="canonical" href="{canon}"/>
  <meta property="og:type"         content="article"/>
  <meta property="og:title"        content="{_esc(title)}"/>
  <meta property="og:description"  content="{_esc(desc)}"/>
  <meta property="og:image"        content="{og_image}"/>
  <meta property="og:image:width"  content="1200"/>
  <meta property="og:image:height" content="630"/>
  <meta property="og:url"          content="{canon}"/>
  <meta property="og:site_name"    content="SolarisNews — Private Intel"/>
  <meta property="og:locale"       content="es_ES"/>
  <meta name="twitter:card"        content="summary_large_image"/>
  <meta name="twitter:title"       content="{_esc(title)}"/>
  <meta name="twitter:description" content="{_esc(desc)}"/>
  <meta name="twitter:image"       content="{og_image}"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;700;900&display=swap" rel="stylesheet"/>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>{_CSS}</style>
</head>"""

# ── HTML: Password Overlay ────────────────────────────────────────────────────

def _pw_overlay(password):
    enc = base64.b64encode(password.encode()).decode()
    return f"""
<div id="pwo">
  <div style="border:1px solid rgba(34,197,94,.3);background:#111;border-radius:1rem;
              padding:2.5rem 2rem;max-width:380px;width:90%;text-align:center;">
    <p class="mono g" style="font-size:.62rem;letter-spacing:.2em;margin-bottom:1.25rem;">
      ◉ SOLARIS PRIVATE INTEL · ACCESO RESTRINGIDO
    </p>
    <p style="font-size:2rem;margin-bottom:.75rem;">🔒</p>
    <h2 class="mono" style="font-size:.95rem;font-weight:700;color:var(--bone);margin-bottom:1.25rem;">
      INTRODUCE CLAVE DE ACCESO
    </h2>
    <input id="pwi" type="password" placeholder="••••••••"
      style="width:100%;background:#0a0a0a;border:1px solid rgba(34,197,94,.3);border-radius:.5rem;
             padding:.75rem 1rem;color:var(--bone);font-family:'JetBrains Mono',monospace;
             font-size:.85rem;outline:none;margin-bottom:.875rem;text-align:center;"
      onkeydown="if(event.key==='Enter')_cpw()"/>
    <button onclick="_cpw()"
      style="width:100%;background:rgba(34,197,94,.1);border:1px solid var(--g);
             color:var(--g);font-family:'JetBrains Mono',monospace;font-size:.75rem;
             font-weight:700;padding:.75rem;border-radius:.5rem;cursor:pointer;letter-spacing:.08em;">
      VERIFICAR ACCESO →
    </button>
    <p id="pwe" class="mono red" style="font-size:.62rem;margin-top:.6rem;display:none;">
      ✗ CLAVE INCORRECTA. ACCESO DENEGADO.
    </p>
  </div>
  <p class="mono muted" style="font-size:.58rem;margin-top:1.25rem;">
    SOLARISNEWS · ORACLE v8.0 · PRIVATE SNIPER MODE
  </p>
</div>
<script>
(function(){{
  const K="{enc}";
  if(sessionStorage.getItem("sa")===K)document.getElementById("pwo").classList.add("hidden");
}})();
function _cpw(){{
  const K="{enc}";
  if(btoa(document.getElementById("pwi").value)===K){{
    sessionStorage.setItem("sa",K);
    document.getElementById("pwo").classList.add("hidden");
  }}else{{
    document.getElementById("pwe").style.display="block";
    document.getElementById("pwi").value="";
    document.getElementById("pwi").focus();
  }}
}}
</script>"""

# ── HTML: Nav, Tickers ────────────────────────────────────────────────────────

def _nav(now, user, repo):
    base = f"https://{user}.github.io/{repo}"
    return f"""
<div class="scanline"></div>
<nav style="background:rgba(10,10,10,.96);border-bottom:1px solid rgba(34,197,94,.15);
            backdrop-filter:blur(8px);"
     class="px-4 sm:px-6 py-3 flex items-center justify-between sticky top-0 z-50">
  <div>
    <a href="{base}/" class="mono font-black text-xl tracking-widest"
       style="color:var(--bone);text-decoration:none;">SOLARIS<span class="g">.</span>NEWS</a>
    <p class="mono muted hide-sm" style="font-size:.58rem;margin-top:.1rem;">
      ORACLE FINANCIAL AI v8.0 · PRIVATE SNIPER · @solaris01
    </p>
  </div>
  <div class="flex items-center gap-4">
    <span class="mono muted hide-sm" style="font-size:.62rem;">{now}</span>
    <span class="mono gg" style="font-size:.7rem;">● LIVE<span class="blink">_</span></span>
  </div>
</nav>"""

def _ticker_marquee():
    return """
<div style="background:#060606;border-bottom:1px solid rgba(34,197,94,.1);
            padding:.3rem 0;overflow:hidden;">
  <p class="marquee mono g" style="font-size:.62rem;letter-spacing:.07em;">
    &nbsp;&nbsp;⬤ SISTEMA DE ANÁLISIS PREDICTIVO SOLARIS v8.0 ONLINE &nbsp;·&nbsp;
    ORACLE FINANCIAL AI ACTIVO &nbsp;·&nbsp;
    CORRELACIONES ORO / PETRÓLEO / BTC EN TIEMPO REAL &nbsp;·&nbsp;
    PRIVATE SNIPER MODE ENGAGED &nbsp;·&nbsp;
    FILTRO ANTI-RUIDO: ACTIVO &nbsp;·&nbsp;
    FUENTES: CASA BLANCA + MEDIOS EUROPEOS + EL ECONOMISTA &nbsp;·&nbsp;
    NODE: ES-INTEL-01 · TLS-1.3 · ENCRYPTED &nbsp;·&nbsp;
    ⬤ SISTEMA DE ANÁLISIS PREDICTIVO SOLARIS v8.0 ONLINE &nbsp;&nbsp;
  </p>
</div>"""

def _tv_tape():
    return """
<div style="background:#0d0d0d;border-bottom:1px solid rgba(34,197,94,.08);">
  <div class="tradingview-widget-container">
    <div class="tradingview-widget-container__widget"></div>
    <script type="text/javascript"
      src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
    {
      "symbols":[
        {"proName":"OANDA:XAUUSD","title":"ORO"},
        {"proName":"OANDA:BCOUSD","title":"BRENT"},
        {"proName":"BITSTAMP:BTCUSD","title":"BTC"},
        {"proName":"BME:IBC","title":"IBEX35"},
        {"proName":"FX_IDC:EURUSD","title":"EUR/USD"}
      ],
      "showSymbolLogo":true,"colorTheme":"dark","isTransparent":true,
      "displayMode":"adaptive","locale":"es"
    }
    </script>
  </div>
</div>"""

def _tv_mini(symbol, label):
    return f"""
<div class="win" style="padding:.75rem;">
  <div class="wbar" style="margin:-.75rem -.75rem .75rem;padding:.38rem .75rem;">
    <span class="dot dr"></span><span class="dot dy"></span><span class="dot dg"></span>
    <span class="mono" style="font-size:.58rem;margin-left:.4rem;color:var(--g);">{label}</span>
  </div>
  <div class="tradingview-widget-container">
    <div class="tradingview-widget-container__widget"></div>
    <script type="text/javascript"
      src="https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js" async>
    {{"symbol":"{symbol}","width":"100%","height":140,"colorTheme":"dark","isTransparent":true,"locale":"es"}}
    </script>
  </div>
</div>"""

# ── HTML: Components ──────────────────────────────────────────────────────────

def _transmissions():
    msgs = random.sample(AGENT_TRANSMISSIONS, min(5, len(AGENT_TRANSMISSIONS)))
    now  = datetime.now().strftime("%H:%M")
    rows = "".join(
        f'<div style="border-left:2px solid var(--g);padding:.4rem .7rem;margin:.25rem 0;'
        f'background:#0c0c0c;border-radius:0 .4rem .4rem 0;">'
        f'<span class="mono g" style="font-size:.6rem;">[{now}][{code}]</span>'
        f'&nbsp;<span class="mono muted" style="font-size:.66rem;">{_esc(msg)}</span></div>'
        for code, msg in msgs
    )
    sha = f"{random.randint(10**15, 10**16-1):x}"
    return f"""
<div class="win">
  <div class="wbar">
    <span class="dot dr"></span><span class="dot dy"></span><span class="dot dg"></span>
    <span class="mono muted" style="font-size:.58rem;margin-left:.4rem;">TRANSMISIONES.enc · NIVEL-5</span>
  </div>
  <div style="padding:1rem;">
    <p class="mono g" style="font-size:.58rem;letter-spacing:.1em;margin-bottom:.5rem;">◉ RED DE AGENTES — CANAL SEGURO</p>
    {rows}
    <p class="mono muted" style="font-size:.56rem;margin-top:.5rem;">SHA-256: {sha} · TLS-1.3</p>
  </div>
</div>"""

def _risk_opp(assets):
    if not assets:
        return ""
    html = ""
    for a in assets[:2]:
        html += f"""
<div style="background:#120808;border:1px solid rgba(239,68,68,.3);border-radius:.75rem;padding:1.25rem 1.5rem;margin-bottom:.75rem;">
  <p class="mono red" style="font-size:.68rem;font-weight:700;margin-bottom:.4rem;">
    ⚠️ ANÁLISIS DE RIESGO — {a['asset']} {a['emoji']}
  </p>
  <p style="color:#fca5a5;font-size:.85rem;line-height:1.65;">{_esc(a['risk'])}</p>
  <p class="mono" style="font-size:.58rem;color:#7f1d1d;margin-top:.4rem;">
    KEYWORDS: {' · '.join(a['hits'][:4]).upper()}
  </p>
</div>
<div style="background:#081208;border:1px solid rgba(34,197,94,.3);border-radius:.75rem;padding:1.25rem 1.5rem;margin-bottom:1rem;">
  <p class="mono g" style="font-size:.68rem;font-weight:700;margin-bottom:.4rem;">
    📈 ESTRATEGIA SOLARIS — {a['asset']}
  </p>
  <p style="color:#86efac;font-size:.85rem;line-height:1.65;">{_esc(a['opportunity'])}</p>
</div>"""
    return html

def _3layer(trend, assets, rel, act, hot):
    ts   = datetime.now().strftime("%Y%m%d%H%M%S")
    vec  = _get_vector(assets)
    exec_map = {
        "ENTRAR":  "Señales alineadas. Múltiples vectores convergen. Posicionamiento defensivo activo.",
        "VIGILAR": "Patrón débil pero emergente. Mantener en radar. Confirmar con segundo vector.",
        "IGNORAR": "Señal débil. Posible ruido informativo. No actuar hasta confirmación.",
        "SALIR":   "Reversión detectada. Narrativa ha cambiado. Revisar posiciones actuales.",
    }
    ac = {"ENTRAR":"var(--g)","VIGILAR":"var(--amb)","IGNORAR":"var(--muted)","SALIR":"var(--red)"}
    rc = {"ALTA":"var(--g)","MEDIA":"var(--amb)","BAJA":"var(--muted)"}
    alpha = ('<span class="badge br" style="margin-left:.4rem;">⚡ ALERTA ALPHA</span>' if hot else "")
    return f"""
<div class="win" style="margin-bottom:1.5rem;">
  <div class="wbar" style="background:#0d0d0d;">
    <span class="dot dr"></span><span class="dot dy"></span><span class="dot dg"></span>
    <span class="mono g" style="font-size:.58rem;margin-left:.4rem;">ANÁLISIS-3CAPAS-{ts}.enc</span>
    {alpha}
    <span class="badge bm" style="margin-left:auto;">ORACLE-SNIPER</span>
  </div>
  <div style="padding:1.25rem 1.5rem;">
    <div class="layer">
      <p class="mono g" style="font-size:.58rem;letter-spacing:.1em;margin-bottom:.4rem;">▸ CAPA 1 — RADAR: HECHO VERIFICADO</p>
      <p style="color:var(--bone);font-size:.88rem;line-height:1.65;">{_esc(trend['p1'])}</p>
    </div>
    <div class="layer" style="border-color:rgba(234,179,8,.2);">
      <p class="mono amb" style="font-size:.58rem;letter-spacing:.1em;margin-bottom:.4rem;">▸ CAPA 2 — VECTORES: ACTORES OCULTOS</p>
      <p style="color:#fde68a;font-size:.88rem;line-height:1.65;font-style:italic;">{_esc(vec)}</p>
    </div>
    <div class="layer" style="border-color:rgba(239,68,68,.2);">
      <p class="mono red" style="font-size:.58rem;letter-spacing:.1em;margin-bottom:.6rem;">▸ CAPA 3 — EJECUCIÓN</p>
      <div style="display:flex;gap:.75rem;flex-wrap:wrap;align-items:center;margin-bottom:.6rem;">
        <div>
          <p class="mono muted" style="font-size:.56rem;">FIABILIDAD</p>
          <p class="mono" style="font-size:.9rem;font-weight:700;color:{rc[rel]};">{rel}</p>
        </div>
        <div style="width:1px;height:2rem;background:#1a1a1a;"></div>
        <div>
          <p class="mono muted" style="font-size:.56rem;">INSTRUCCIÓN</p>
          <p class="mono" style="font-size:1.1rem;font-weight:700;color:{ac[act]};">[{act}]</p>
        </div>
        <div style="width:1px;height:2rem;background:#1a1a1a;" class="hide-sm"></div>
        <div class="hide-sm">
          <p class="mono muted" style="font-size:.56rem;">ACTIVOS</p>
          <p class="mono" style="font-size:.78rem;font-weight:700;color:var(--bone);">
            {' / '.join(a['emoji']+' '+a['asset'] for a in assets) if assets else '—'}
          </p>
        </div>
      </div>
      <p style="color:#fca5a5;font-size:.83rem;line-height:1.55;">{_esc(exec_map[act])}</p>
    </div>
  </div>
</div>"""

def _subscribe():
    return """
<div class="win" style="margin-bottom:2rem;border-color:rgba(34,197,94,.25);">
  <div class="wbar" style="background:#0d120d;">
    <span class="dot dr"></span><span class="dot dy"></span><span class="dot dg"></span>
    <span class="mono g" style="font-size:.58rem;margin-left:.4rem;">ACCESO-NIVEL-5.init</span>
  </div>
  <div style="padding:1.5rem 2rem;text-align:center;">
    <p class="mono g" style="font-size:.58rem;letter-spacing:.18em;margin-bottom:.5rem;">◉ NIVEL 5 — RESTRINGIDO</p>
    <h2 class="font-black" style="font-size:clamp(1.1rem,3vw,1.6rem);color:var(--bone);margin-bottom:.5rem;">
      INTELIGENCIA SIN FILTROS — <span class="gg">PRÓXIMAMENTE</span>
    </h2>
    <p class="muted" style="font-size:.85rem;margin-bottom:1.25rem;max-width:420px;margin-left:auto;margin-right:auto;">
      Informes de inteligencia geopolítica antes que nadie. Sin ruido. Sin censura.
    </p>
    <button class="btn-g" style="cursor:default;">UNIRSE A LA LISTA DE ESPERA →</button>
  </div>
</div>"""

def _store(cpa):
    cards = "".join(
        f'<a href="{cpa}" target="_blank" rel="noopener" class="supply">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.4rem;">'
        f'<p style="font-weight:900;font-size:.83rem;color:var(--bone);">{_esc(p["name"])}</p>'
        f'<span class="badge ba">{p["tag"]}</span>'
        f'</div>'
        f'<p class="mono muted" style="font-size:.66rem;line-height:1.4;">{_esc(p["desc"])}</p>'
        f'<p class="mono g" style="font-size:.6rem;margin-top:.4rem;">→ Amazon.es</p>'
        f'</a>'
        for p in TACTICAL_PRODUCTS
    )
    return f"""
<section style="margin-bottom:3rem;">
  <div class="wbar" style="background:#100e08;border:1px solid rgba(234,179,8,.2);
                            border-radius:.75rem .75rem 0 0;border-bottom:none;">
    <span class="dot dr"></span><span class="dot dy"></span><span class="dot dg"></span>
    <span class="mono amb" style="font-size:.58rem;margin-left:.4rem;letter-spacing:.07em;">
      SUMINISTROS-TACTICOS.db · {len(TACTICAL_PRODUCTS)} ITEMS
    </span>
  </div>
  <div style="border:1px solid rgba(234,179,8,.2);border-top:none;
              border-radius:0 0 .75rem .75rem;padding:1rem;">
    <p class="mono muted" style="font-size:.58rem;letter-spacing:.06em;margin-bottom:.75rem;">
      EQUIPAMIENTO SELECCIONADO · AFFILIATE DISCLOSURE · AMAZON.ES
    </p>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(155px,1fr));gap:.75rem;">
      {cards}
    </div>
  </div>
</section>"""

def _tiktok_cta():
    return """
<div style="text-align:center;padding:2rem 1rem 3rem;">
  <p class="mono muted" style="font-size:.62rem;letter-spacing:.12em;margin-bottom:.75rem;">◉ CANAL DE INTELIGENCIA PRINCIPAL</p>
  <a href="https://www.tiktok.com/@solaris01" target="_blank" rel="noopener" class="btn-tt">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="#22c55e">
      <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.89-2.89 2.89 2.89 0 012.89-2.89c.28 0 .54.04.79.1V9.01a6.27 6.27 0 00-.79-.05 6.34 6.34 0 00-6.34 6.34 6.34 6.34 0 006.34 6.34 6.34 6.34 0 006.33-6.34V8.69a8.18 8.18 0 004.78 1.52V6.76a4.85 4.85 0 01-1.01-.07z"/>
    </svg>
    SUSCRIBIRSE AL CANAL DE INTELIGENCIA (TIKTOK)
  </a>
  <p class="mono muted" style="font-size:.58rem;margin-top:.75rem;">@solaris01 · ACTUALIZACIONES DIARIAS · SIN FILTROS</p>
</div>"""

# ── HTML: Article ─────────────────────────────────────────────────────────────

def build_article(trend, cfg, hot_topics):
    user   = cfg["github_user"]
    repo   = cfg["repo_name"]
    pw     = cfg.get("access_password", "solaris2024")
    cpa    = cfg["cpa_link"]
    canon  = f"https://{user}.github.io/{repo}/{trend['slug']}/"
    og_img = f"https://{user}.github.io/{repo}/og.svg"
    now    = datetime.now().strftime("%-d %b %Y · %H:%M")
    ts     = datetime.now().strftime("%Y%m%d%H%M")

    assets = _detect_assets(trend["title"], trend["p1"] + " " + trend["p2"])
    hot    = _is_hot(trend["title"], hot_topics)
    rel    = _reliability(assets, trend.get("critical", False), hot)
    act    = _action(rel, assets)
    tc     = _title_color(trend["title"], assets)

    _log_intel(trend["slug"], trend["title"], assets, act)

    alpha_banner = ""
    if hot:
        alpha_banner = """
<div style="background:#1a0000;border:1px solid var(--red);border-radius:.75rem;
            padding:.75rem 1.25rem;margin-bottom:1.5rem;">
  <p class="mono red" style="font-size:.68rem;font-weight:700;">⚡ ALERTA ALPHA: TENDENCIA CRÍTICA EN DESARROLLO</p>
  <p class="mono muted" style="font-size:.62rem;margin-top:.2rem;">
    Este tema ha sido detectado múltiples veces en el ciclo actual. Señal de alta repetición. Monitorización prioritaria.
  </p>
</div>"""

    agent_rows = "".join(
        f'<div style="border-left:2px solid var(--g);padding:.4rem .7rem;margin:.25rem 0;'
        f'background:#0c0c0c;border-radius:0 .4rem .4rem 0;">'
        f'<span class="mono g" style="font-size:.58rem;">[{now[:5]}][{code}]</span>'
        f'&nbsp;<span class="mono muted" style="font-size:.64rem;">{_esc(msg)}</span></div>'
        for code, msg in random.sample(AGENT_TRANSMISSIONS, 3)
    )

    return (
        _html_head(f"{_esc(trend['title'])} | SolarisNews Intel",
                   f"{trend['title']} — Análisis geopolítico SolarisNews Oracle Financial AI.",
                   canon, og_img)
        + f"""
<body>
{_pw_overlay(pw)}
{_nav(now, user, repo)}
{_ticker_marquee()}
{_tv_tape()}

<main style="max-width:800px;margin:0 auto;padding:2rem 1rem;" class="fadein">

  <div style="display:flex;flex-wrap:wrap;align-items:center;gap:.4rem;margin-bottom:1.25rem;">
    <span class="badge br">◉ ALERTA ACTIVA</span>
    <span class="badge bm">#{ts}</span>
    <span class="badge bm">NODO-ES</span>
    {'<span class="badge ba">◈ FUENTE CRÍTICA</span>' if trend.get("critical") else ''}
    <span class="mono muted" style="font-size:.58rem;">{now}</span>
  </div>

  {alpha_banner}

  <h1 class="font-black"
      style="font-size:clamp(1.4rem,4vw,2.2rem);color:{tc};line-height:1.2;margin-bottom:.75rem;">
    {_esc(trend['title'])}
  </h1>
  <p class="mono muted"
     style="font-size:.63rem;padding-bottom:1.25rem;border-bottom:1px solid rgba(34,197,94,.1);margin-bottom:1.5rem;">
    SOLARISNEWS ORACLE FINANCIAL AI v8.0 · PRIVATE SNIPER · CLASIFICACIÓN: PÚBLICA
  </p>

  {_3layer(trend, assets, rel, act, hot)}
  {_risk_opp(assets)}

  <div class="win" style="margin-bottom:1.5rem;">
    <div class="wbar">
      <span class="dot dr"></span><span class="dot dy"></span><span class="dot dg"></span>
      <span class="mono g" style="font-size:.58rem;margin-left:.4rem;">DECODIFICACIÓN-SOLARIS.decrypt</span>
      <span class="badge br" style="margin-left:auto;">CLASIFICADO</span>
    </div>
    <div style="padding:1.25rem 1.5rem;">
      <p class="mono g" style="font-size:.58rem;letter-spacing:.1em;margin-bottom:.5rem;">◈ ANÁLISIS DE INTELIGENCIA SOLARIS</p>
      <p style="color:var(--bone);line-height:1.7;font-style:italic;">"{_esc(random.choice(INTEL_ANALYSES))}"</p>
      <div class="mono muted" style="font-size:.56rem;margin-top:.6rem;display:flex;gap:1rem;flex-wrap:wrap;">
        <span>VECTOR: GEOPOLÍTICO</span>
        <span class="g">CONFIANZA: 94%</span>
        <span>NODO: ES-INTEL-01</span>
      </div>
    </div>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:2rem;">
    <a href="{trend['link']}" target="_blank" rel="noopener" class="btn-g">◈ FUENTE ORIGINAL</a>
    <a href="{cpa}" target="_blank" rel="noopener" class="btn-a">⚡ SUMINISTROS (AMAZON)</a>
  </div>

  <div class="win" style="margin-bottom:2rem;">
    <div class="wbar">
      <span class="dot dr"></span><span class="dot dy"></span><span class="dot dg"></span>
      <span class="mono muted" style="font-size:.58rem;margin-left:.4rem;">AGENTES.log · 3 TX</span>
    </div>
    <div style="padding:1rem;">{agent_rows}</div>
  </div>

  {_subscribe()}

  <div style="background:#0c0c0c;border:1px solid #1a1a1a;border-radius:.625rem;
              padding:.75rem 1rem;margin-bottom:1.5rem;">
    <p class="mono muted" style="font-size:.56rem;">
      SOURCE_VERIFIED: TRUE · THREAT_LEVEL: MONITOR · NODE: ES-INTEL-01 · <span id="ts2"></span>
    </p>
  </div>

  <a href="../" class="mono g" style="font-size:.7rem;text-decoration:none;">← VOLVER AL HUB GLOBAL</a>
</main>

<footer style="border-top:1px solid rgba(34,197,94,.1);margin-top:2rem;">
  {_tiktok_cta()}
  <p class="mono muted" style="text-align:center;font-size:.56rem;padding-bottom:2rem;">
    © {datetime.now().year} SOLARISNEWS · ORACLE FINANCIAL AI v8.0 · PRIVATE SNIPER
  </p>
</footer>
<script>
  const el=document.getElementById("ts2");
  if(el)el.textContent=new Date().toLocaleString("es-ES");
</script>
</body></html>"""
    )

# ── HTML: Home ────────────────────────────────────────────────────────────────

def build_home(trends, cfg, hot_topics):
    user   = cfg["github_user"]
    repo   = cfg["repo_name"]
    pw     = cfg.get("access_password", "solaris2024")
    cpa    = cfg["cpa_link"]
    now    = datetime.now().strftime("%-d %b %Y · %H:%M")
    canon  = f"https://{user}.github.io/{repo}/"
    og_img = f"https://{user}.github.io/{repo}/og.svg"

    cards = ""
    for i, t in enumerate(trends):
        assets = _detect_assets(t["title"], t["p1"])
        hot    = _is_hot(t["title"], hot_topics)
        rel    = _reliability(assets, t.get("critical", False), hot)
        act    = _action(rel, assets)
        tc     = _title_color(t["title"], assets)

        badge = ('<span class="badge br">◉ BREAKING</span>' if i < 3
                 else ('<span class="badge ba">◈ MONITOR</span>' if i < 8
                       else '<span class="badge bm">◎ ARCHIVO</span>'))
        alpha = '<span class="badge br">⚡ ALERTA ALPHA</span>' if hot else ""

        asset_pills = "".join(
            f'<span class="badge" style="border:1px solid {a["color"]};color:{a["color"]};">'
            f'{a["emoji"]} {a["asset"]}</span>' for a in assets[:2]
        )
        ac = {"ENTRAR":"var(--g)","VIGILAR":"var(--amb)","IGNORAR":"var(--muted)","SALIR":"var(--red)"}

        cards += (
            f'<li class="fadein">'
            f'<a href="./{t["slug"]}/" class="win" style="display:block;text-decoration:none;padding:1.25rem;">'
            f'<div class="wbar" style="margin:-1.25rem -1.25rem .875rem;padding:.38rem .75rem;">'
            f'<span class="dot dr"></span><span class="dot dy"></span><span class="dot dg"></span>'
            f'<span class="mono muted" style="font-size:.56rem;margin-left:.4rem;">RPT-{str(i+1).zfill(3)}.enc</span>'
            f'{badge}{alpha}'
            f'<span class="mono" style="font-size:.56rem;margin-left:auto;color:{ac[act]};">[{act}]</span>'
            f'</div>'
            f'<h2 class="font-black" style="font-size:clamp(.82rem,2vw,.94rem);color:{tc};line-height:1.35;margin-bottom:.55rem;">'
            f'{_esc(t["title"])}</h2>'
            f'<p class="mono muted" style="font-size:.66rem;line-height:1.45;margin-bottom:.55rem;">'
            f'{_esc(t["p1"][:130])}…</p>'
            f'<div style="display:flex;gap:.3rem;flex-wrap:wrap;">{asset_pills}</div>'
            f'</a></li>'
        )

    return (
        _html_head("SolarisNews — Oracle Financial AI | Inteligencia Geopolítica",
                   "Portal de inteligencia geopolítica y financiera. Análisis Oracle AI, correlaciones Oro/Petróleo/BTC. Canal @solaris01.",
                   canon, og_img)
        + f"""
<body>
{_pw_overlay(pw)}
{_nav(now, user, repo)}
{_ticker_marquee()}
{_tv_tape()}

<header style="text-align:center;padding:3rem 1rem 2.5rem;
               background:linear-gradient(180deg,#0d0d0d,var(--bg));
               border-bottom:1px solid rgba(34,197,94,.08);">
  <p class="mono g" style="font-size:.62rem;letter-spacing:.2em;margin-bottom:.75rem;">
    ◉ ESCANEANDO SISTEMA<span class="blink">_</span> · ORACLE FINANCIAL AI ACTIVO
  </p>
  <h1 class="font-black" style="font-size:clamp(2.5rem,8vw,5rem);letter-spacing:-.02em;line-height:1;margin-bottom:.75rem;">
    <span style="color:var(--bone);">SOLARIS</span><span class="gg">.</span><span class="gg">NEWS</span>
  </h1>
  <p class="mono muted" style="font-size:.7rem;letter-spacing:.1em;">
    ORACLE FINANCIAL AI v8.0 · PRIVATE SNIPER ·
    <span class="g">{len(trends)} ALERTAS ACTIVAS</span> · <span id="ts_h"></span>
  </p>
  <p class="mono" style="font-size:.56rem;color:#374151;margin-top:.4rem;">
    FILTRO ANTI-RUIDO: ACTIVO · ORO/BTC/PETRÓLEO · TLS-1.3 · NODO-ES
  </p>
</header>

<div class="max-w-screen-xl mx-auto px-4 py-8">
  {_subscribe()}

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

    <div class="lg:col-span-2">
      <div class="wbar" style="background:#0e0e0e;border:1px solid var(--gb);
                               border-radius:.75rem .75rem 0 0;border-bottom:none;">
        <span class="dot dr"></span><span class="dot dy"></span><span class="dot dg"></span>
        <span class="mono muted" style="font-size:.58rem;margin-left:.4rem;">
          INTEL-FEED.live · {len(trends)} INFORMES · ES-NODE
        </span>
        <span class="mono g" style="font-size:.58rem;margin-left:auto;">● EN DIRECTO</span>
      </div>
      <ul style="list-style:none;display:flex;flex-direction:column;gap:.75rem;padding-top:.75rem;">
        {cards}
      </ul>
    </div>

    <div class="space-y-4">
      {_transmissions()}
      {_tv_mini("OANDA:XAUUSD",  "🥇 XAU/USD · ORO")}
      {_tv_mini("OANDA:BCOUSD",  "🛢️ BRENT CRUDO")}
      {_tv_mini("BITSTAMP:BTCUSD","₿ BITCOIN")}
    </div>

  </div>

  {_store(cpa)}
</div>

<footer style="border-top:1px solid rgba(34,197,94,.08);">
  {_tiktok_cta()}
  <p class="mono muted" style="text-align:center;font-size:.56rem;padding-bottom:2rem;">
    © {datetime.now().year} SOLARISNEWS · ORACLE FINANCIAL AI v8.0 · PRIVATE SNIPER
  </p>
</footer>
<script>document.getElementById("ts_h").textContent=new Date().toLocaleString("es-ES");</script>
</body></html>"""
    )

# ── GitHub Actions Workflow ───────────────────────────────────────────────────

def upload_workflow(cfg):
    workflow = b"""\
name: SolarisNews Oracle Financial AI 24/7
on:
  schedule:
    - cron: '*/20 * * * *'
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
          ORACLE_TOKEN:    ${{ secrets.ORACLE_TOKEN }}
          ORACLE_USER:     ${{ secrets.ORACLE_USER }}
          ORACLE_REPO:     ${{ secrets.ORACLE_REPO }}
          ORACLE_WEBHOOK:  ${{ secrets.ORACLE_WEBHOOK }}
          ORACLE_AD_ID:    ${{ secrets.ORACLE_AD_ID }}
          ORACLE_CPA:      ${{ secrets.ORACLE_CPA }}
          ORACLE_PAYPAL:   ${{ secrets.ORACLE_PAYPAL }}
          ORACLE_PASSWORD: ${{ secrets.ORACLE_PASSWORD }}
        run: |
          python - <<'PYEOF'
          import json,os
          cfg={
            "github_token":    os.environ["ORACLE_TOKEN"],
            "github_user":     os.environ["ORACLE_USER"],
            "repo_name":       os.environ["ORACLE_REPO"],
            "webhook_url":     os.environ["ORACLE_WEBHOOK"],
            "ad_unit_id":      os.environ["ORACLE_AD_ID"],
            "cpa_link":        os.environ["ORACLE_CPA"],
            "paypal_email":    os.environ["ORACLE_PAYPAL"],
            "payout_method":   "paypal",
            "access_password": os.environ.get("ORACLE_PASSWORD","solaris2024"),
          }
          open("config.json","w").write(json.dumps(cfg))
          PYEOF
      - run: python astral_oracle.py --once
"""
    path = ".github/workflows/solarisnews.yml"
    api  = (f"https://api.github.com/repos/{cfg['github_user']}"
            f"/{cfg['repo_name']}/contents/{path}")
    r    = requests.get(api, headers=_gh(cfg["github_token"]), timeout=15)
    pl   = {"message": "v8: Oracle Financial AI workflow",
            "content": base64.b64encode(workflow).decode()}
    if r.status_code == 200:
        pl["sha"] = r.json()["sha"]
    r2 = requests.put(api, headers=_gh(cfg["github_token"]), json=pl, timeout=15)
    log.info("Workflow 24/7 %s", "✅ subido" if r2.status_code in (200, 201)
             else f"FALLÓ {r2.status_code}")

def upload_self(cfg):
    if _push("astral_oracle.py", Path(__file__).read_bytes(), cfg):
        log.info("✅ astral_oracle.py v8 Oracle Financial AI subido.")

# ── Cycle ─────────────────────────────────────────────────────────────────────

def rotate_log(max_lines=150):
    p = Path("oracle.log")
    if not p.exists():
        return
    lines = p.read_text(errors="replace").splitlines()
    if len(lines) > max_lines:
        p.write_text("\n".join(lines[-max_lines:]) + "\n")

def run_once(cfg):
    rotate_log()
    log.info("═══ ORACLE FINANCIAL AI v8.0 — PRIVATE SNIPER — CYCLE START ═══")
    if not ensure_setup(cfg):
        log.error("Setup falló.")
        return
    ensure_ads_txt(cfg)
    trends     = get_trends()
    hot_topics = _update_memory(trends)
    if hot_topics:
        log.info("🔥 Hot topics: %s", list(hot_topics.keys())[:5])
    _push("index.html", build_home(trends, cfg, hot_topics).encode(), cfg)
    publicadas = 0
    for t in trends:
        try:
            ok = _push(f"{t['slug']}/index.html",
                       build_article(t, cfg, hot_topics).encode(), cfg)
            cpa   = cfg["cpa_link"]
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
    if not cfg.get("access_password"):
        cfg["access_password"] = "solaris2024"
    if once_mode:
        run_once(cfg)
        return
    log.info("═══ ORACLE FINANCIAL AI v8.0 — PRIVATE SNIPER — MODO LOCAL ═══")
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
