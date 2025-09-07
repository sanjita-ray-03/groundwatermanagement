# faq.py
from __future__ import annotations
import os, time, json, math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict

import requests
from bs4 import BeautifulSoup
import numpy as np
from flask import Blueprint, jsonify, request

bp = Blueprint("faq", __name__, url_prefix="/api/faq")

# ---------------------------
# Config
# ---------------------------

# External content sources we’ll ingest to build the FAQ dynamically.
USGS_QA_HUB = "https://www.usgs.gov/water-science-school/science/groundwater-questions-answers"
CGWB_FAQ_URL = "https://cgwb.gov.in/en/faq"   # Fallback: https://www.cgwb.gov.in/en/faq-general

# Optional API sources (numeric → templated Q&A)
USGS_GWLEVELS_API_DOCS = "https://waterservices.usgs.gov/docs/groundwater-levels/"
USGS_GWLEVELS_ENDPOINT = "https://waterservices.usgs.gov/nwis/gwlevels/"

# India data.gov.in — requires API key; set env: DATA_GOV_IN_API_KEY
# To use this, find a resourceId for a groundwater-level dataset and paste below.
DATAGOV_API_KEY = os.getenv("DATA_GOV_IN_API_KEY", "")
DATAGOV_RESOURCE_ID = os.getenv("DATAGOV_GWL_RESOURCE_ID", "")  # e.g., from Atal Bhujal Yojana dataset
DATAGOV_ENDPOINT = "https://api.data.gov.in/resource/{resource_id}"

# Embedding model (lazy-loaded)
_MODEL = None

# In-memory store
_FAQ: List[Dict[str, Any]] = []
_EMB: Optional[np.ndarray] = None
_META = {
    "last_refresh_epoch": None,
    "source_counts": {},
    "using_datagov": bool(DATAGOV_API_KEY and DATAGOV_RESOURCE_ID),
    "usgs_numeric_examples": 0
}

# ---------------------------
# Utilities
# ---------------------------

def _http_get(url: str, params: Dict[str, Any] = None, timeout: int = 20) -> requests.Response:
    r = requests.get(url, params=params or {}, timeout=timeout, headers={"User-Agent": "groundwater-faq/1.0"})
    r.raise_for_status()
    return r

def _clean_text(t: str) -> str:
    return " ".join((t or "").replace("\xa0", " ").split())

def _dedupe(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for it in items:
        key = (_clean_text(it.get("q","")).lower(), _clean_text(it.get("a","")).lower())
        if key not in seen and it.get("q") and it.get("a"):
            seen.add(key)
            out.append(it)
    return out

# ---------------------------
# Scrapers → Q/A
# ---------------------------

def fetch_usgs_qas() -> List[Dict[str, Any]]:
    """
    Crawl the USGS Groundwater Q&A hub and pull each question page’s title + main text.
    Turns each into a {q, a, source} item.
    """
    items = []
    try:
        hub = _http_get(USGS_QA_HUB).text
    except Exception as e:
        return items

    soup = BeautifulSoup(hub, "html.parser")
    # Collect links to question pages within the hub main content
    links = []
    for a in soup.select("a"):
        href = a.get("href", "")
        if href and "/faqs/" in href or (href and href.startswith("https://www.usgs.gov/faqs/")):
            links.append(href if href.startswith("http") else f"https://www.usgs.gov{href}")
    links = list(dict.fromkeys(links))[:120]  # cap to be polite

    for href in links:
        try:
            html = _http_get(href).text
            pg = BeautifulSoup(html, "html.parser")
            # Title is the question
            title_el = pg.select_one("h1, h2")
            question = _clean_text(title_el.get_text()) if title_el else None
            # Answer: grab the main content paragraphs
            content = pg.select_one("main") or pg
            paras = [p.get_text(" ", strip=True) for p in content.select("p")]
            answer = _clean_text(" ".join(paras[:6]))  # concise
            if question and answer:
                items.append({
                    "q": question,
                    "a": answer,
                    "source": href,
                    "meta": {"origin": "USGS Water Science School"}
                })
        except Exception:
            continue
    return items

def fetch_cgwb_faqs() -> List[Dict[str, Any]]:
    """
    Parse CGWB FAQ page(s). The markup uses 'Q' and 'Ans' text blocks.
    """
    items = []
    for url in [CGWB_FAQ_URL, "https://www.cgwb.gov.in/en/faq-general"]:
        try:
            html = _http_get(url).text
        except Exception:
            continue
        soup = BeautifulSoup(html, "html.parser")
        # Strategy: look for Q/A text patterns.
        text = soup.get_text("\n", strip=True)
        lines = [l for l in text.split("\n") if l.strip()]
        q, a = None, []
        def flush():
            if q and a:
                items.append({
                    "q": _clean_text(q),
                    "a": _clean_text(" ".join(a)),
                    "source": url,
                    "meta": {"origin": "CGWB"}
                })
        for ln in lines:
            low = ln.lower()
            if low.startswith("q") and ":" in ln:
                flush()
                q = ln.split(":", 1)[1].strip()
                a = []
            elif low.startswith("ans") or low.startswith("answer"):
                # start collecting answer content; skip the label itself
                ans_text = ln.split(":", 1)[1].strip() if ":" in ln else ln
                if ans_text: a.append(ans_text)
            else:
                # keep appending to answer until next question
                if q is not None:
                    a.append(ln)
        flush()
        if items:
            break
    return items

# ---------------------------
# Numeric → templated Q/A
# ---------------------------

def fetch_usgs_latest_levels(site_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Pull recent USGS manual groundwater levels for given site numbers and template into Q/A.
    Note: This is a demo pathway; tweak for your targets (bbox, state, etc.)
    """
    if not site_ids:
        return []
    params = {
        "format": "json",
        "sites": ",".join(site_ids),
        "parameterCd": "72019",   # depth to water level below land surface
        "siteStatus": "all"
    }
    try:
        js = _http_get(USGS_GWLEVELS_ENDPOINT, params=params).json()
    except Exception:
        return []
    items = []
    for series in js.get("value", {}).get("timeSeries", []):
        site = series.get("sourceInfo", {}).get("siteCode", [{}])[0].get("value")
        vals = series.get("values", [])
        if not vals: 
            continue
        pts = vals[0].get("value", [])
        if not pts:
            continue
        latest = pts[-1]
        val = latest.get("value")
        dt = latest.get("dateTime")
        q = f"What is the latest groundwater level (depth to water) at USGS site {site}?"
        a = f"The latest reported depth to water level is {val} (feet below land surface) as of {dt}."
        items.append({"q": q, "a": a, "source": USGS_GWLEVELS_ENDPOINT, "meta": {"site": site, "paramCd": "72019"}})
    return items

def fetch_datagov_india_levels(limit:int=2000) -> List[Dict[str, Any]]:
    """
    Example of pulling India groundwater levels via data.gov.in and templating to Q/A.
    Requires:
      - env DATA_GOV_IN_API_KEY
      - env DATAGOV_GWL_RESOURCE_ID (dataset resource id)
    """
    if not (DATAGOV_API_KEY and DATAGOV_RESOURCE_ID):
        return []
    items = []
    # Paginate through records
    page = 0
    got = 0
    while True:
        params = {
            "api-key": DATAGOV_API_KEY,
            "format": "json",
            "limit": min(1000, limit - got),
            "offset": got
        }
        url = DATAGOV_ENDPOINT.format(resource_id=DATAGOV_RESOURCE_ID)
        try:
            js = _http_get(url, params=params).json()
        except Exception:
            break
        records = js.get("records", [])
        if not records:
            break
        for r in records:
            # Try common field names; adapt to your resource schema
            site = r.get("station_id") or r.get("well_id") or r.get("site") or r.get("location")
            dt = r.get("date") or r.get("observation_date") or r.get("datetime") or r.get("month_year")
            lvl = r.get("depth_m") or r.get("depth_mbgl") or r.get("water_level") or r.get("gwl_value")
            if site and lvl:
                q = f"What is the reported groundwater level at station {site}?"
                a = f"The reported groundwater level is {lvl} (mbgl) on {dt}."
                items.append({"q": q, "a": a, "source": url, "meta": {"station": site, "date": dt}})
        got += len(records)
        if got >= limit or len(records) == 0:
            break
    return items

# ---------------------------
# Embeddings & search
# ---------------------------

def _load_model():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL

def build_index(rows: List[Dict[str, Any]]):
    global _EMB
    if not rows:
        _EMB = None
        return
    model = _load_model()
    corpus = [r["q"] + " " + r["a"] for r in rows]
    _EMB = model.encode(corpus, convert_to_tensor=False, normalize_embeddings=True)

def _semantic_search(query: str, topk: int = 5) -> List[Tuple[int, float]]:
    if _EMB is None or not _FAQ:
        return []
    model = _load_model()
    qv = model.encode([query], convert_to_tensor=False, normalize_embeddings=True)[0]
    # cosine because vectors are normalized
    sims = np.dot(_EMB, qv)
    idxs = np.argsort(-sims)[:topk]
    return [(int(i), float(sims[i])) for i in idxs]

# ---------------------------
# Refresh pipeline
# ---------------------------

def refresh_dataset() -> Dict[str, Any]:
    global _FAQ, _META
    collected: List[Dict[str, Any]] = []

    # 1) Static Q&A sources (big bulk, evergreen)
    cgwb = fetch_cgwb_faqs()
    usgs = fetch_usgs_qas()
    collected.extend(cgwb)
    collected.extend(usgs)

    # 2) Optional numeric → Q/A (you can disable by leaving envs blank)
    usgs_numeric = fetch_usgs_latest_levels(site_ids=[
        # demo site ids – replace with your targets
        "381744083110601", "325848082480901"
    ])
    collected.extend(usgs_numeric)

    datagov = fetch_datagov_india_levels(limit=2000)
    collected.extend(datagov)

    # Clean & de-dup
    collected = _dedupe(collected)

    # Update globals
    _FAQ = collected
    _META = {
        "last_refresh_epoch": int(time.time()),
        "source_counts": {
            "CGWB_FAQ": len(cgwb),
            "USGS_QA": len(usgs),
            "USGS_numeric": len(usgs_numeric),
            "DATAGOV_IN": len(datagov),
        },
        "using_datagov": bool(DATAGOV_API_KEY and DATAGOV_RESOURCE_ID),
    }

    # Build vector index
    build_index(_FAQ)
    return _META

# ---------------------------
# Routes
# ---------------------------

@bp.route("/", methods=["GET"])
def get_faq():
    """
    List all Q/As currently in memory.
    Tip: call /api/faq/refresh on startup or via a cron so this stays current.
    """
    return jsonify({
        "meta": _META,
        "count": len(_FAQ),
        "data": _FAQ,
    })

@bp.route("/ask", methods=["GET", "POST"])
def ask_faq():
    # Read query from ?q= or JSON {query}
    if request.method == "POST":
        query = (request.json or {}).get("query", "").strip()
    else:
        query = (request.args.get("q") or "").strip()
    if not query:
        return jsonify({"a": "No question provided."}), 400

    # First, quick keyword match (fast path)
    qlow = query.lower()
    for i, faq in enumerate(_FAQ):
        if qlow in faq["q"].lower():
            return jsonify({"match": "keyword", "rank": i, "faq": faq})

    # Then semantic search
    hits = _semantic_search(query, topk=5)
    if not hits:
        return jsonify({"a": "Sorry, I don’t know the answer."})
    best_idx, score = hits[0]
    payload = _FAQ[best_idx].copy()
    payload["score"] = score
    payload["candidates"] = [
        {"idx": int(i), "score": sc, "q": _FAQ[int(i)]["q"], "source": _FAQ[int(i)]["source"]}
        for (i, sc) in hits
    ]
    return jsonify({"match": "semantic", "faq": payload})

@bp.route("/refresh", methods=["POST"])
def refresh():
    """
    Re-ingest from the web/APIs and rebuild the vector index.
    """
    meta = refresh_dataset()
    return jsonify({"status": "ok", "meta": meta, "count": len(_FAQ)})

@bp.route("/sources", methods=["GET"])
def sources():
    return jsonify({
        "CGWB_FAQ_URL": CGWB_FAQ_URL,
        "USGS_QA_HUB": USGS_QA_HUB,
        "USGS_GWLEVELS_ENDPOINT": USGS_GWLEVELS_ENDPOINT,
        "DATAGOV_IN": {
            "enabled": bool(DATAGOV_API_KEY and DATAGOV_RESOURCE_ID),
            "resource_id": DATAGOV_RESOURCE_ID[:8] + "..." if DATAGOV_RESOURCE_ID else None
        }
    })
