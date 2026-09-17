


# =============================================================================
# The Mountain Path Academy — India–US 10Y Bond Yield Spread
# Educational Streamlit App  |  Prof. V. Ravichandran
# https://themountainpathacademy.com
# =============================================================================
import io
import json
import random
import math
import time
from urllib.parse import quote as urlquote
from html import escape
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    import requests
    _HAS_REQUESTS = True
except Exception:
    _HAS_REQUESTS = False

# -----------------------------------------------------------------------------
# PAGE CONFIG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="India–US 10Y Bond Yield Spread | The Mountain Path Academy",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -----------------------------------------------------------------------------
# BRAND PALETTE
# -----------------------------------------------------------------------------
GOLD  = "#FFD700"
BLUE  = "#003366"
MID   = "#004d80"
CARD  = "#112240"
TXT   = "#e6f1ff"
MUTED = "#8892b0"
GRN   = "#28a745"
RED   = "#dc3545"
LB    = "#ADD8E6"
AMBER = "#f0ad4e"

LINK_ACADEMY = "https://themountainpathacademy.com"
LINK_LI      = "https://www.linkedin.com/in/trichyravis"
LINK_GH      = "https://github.com/trichyravis"

# -----------------------------------------------------------------------------
# LIVE DATA LAYER  (FRED public CSV — no API key required)
#   US 10Y   : DGS10          (daily, reliable)
#   India 10Y: INDIRLTLT01STM (OECD long-term govt bond rate; monthly, may lag)
# Falls back to illustrative defaults if the network/feed is unavailable.
# -----------------------------------------------------------------------------
DEFAULT_IND = 6.87   # India 10Y G-Sec (%)  — reference/fallback
DEFAULT_US  = 4.65   # US 10Y Treasury (%)  — reference/fallback

_BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
               "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")

@st.cache_data(ttl=3600, show_spinner=False)
def _fred_latest(series_id: str):
    """Return (latest_value_pct, as_of_date_str) for a FRED series.
    Raises on failure so the failure is NOT cached (Streamlit re-tries next run)."""
    if not _HAS_REQUESTS:
        raise RuntimeError("requests unavailable")
    # One attempt per refresh; short timeouts avoid long retry delays.
    start = (pd.Timestamp.now() - pd.Timedelta(days=730)).strftime("%Y-%m-%d")
    with requests.Session() as session:
        r = session.get("https://fred.stlouisfed.org/graph/fredgraph.csv",
                        params={"id": series_id, "cosd": start}, timeout=(3, 7),
                        headers={"User-Agent": _BROWSER_UA, "Accept": "text/csv,*/*"})
        r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    if len(df.columns) != 2 or series_id not in df.columns:
        raise ValueError(f"Unexpected CSV columns for {series_id}")
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna().sort_values("date")
    df = df[df["date"] <= pd.Timestamp.now().normalize()]
    if df.empty:
        raise ValueError(f"No valid observations for {series_id}")
    last = df.iloc[-1]
    value = float(last["value"])
    if not math.isfinite(value):
        raise ValueError(f"Non-finite observation for {series_id}")
    return round(value, 2), last["date"].strftime("%Y-%m-%d")

def _age_days(date_str):
    try:
        return int((pd.Timestamp.now().normalize() - pd.to_datetime(date_str)).days)
    except Exception:
        return None

@st.cache_data(ttl=3600, show_spinner=False)
def _treasury_latest():
    """Official nominal 10-year par yield; no API key or extra dependency."""
    if not _HAS_REQUESTS:
        raise RuntimeError("requests unavailable")
    # Include the previous year for the New Year holiday publication gap.
    observations = []
    today = pd.Timestamp.now().normalize()
    years = [today.year] if today.month != 1 else [today.year, today.year - 1]
    for year in years:
        with requests.Session() as session:
            r = session.get(
                "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml",
                params={"data": "daily_treasury_yield_curve", "field_tdr_date_value": str(year)},
                timeout=(3, 7), headers={"User-Agent": _BROWSER_UA, "Accept": "application/xml"})
            r.raise_for_status()
        root = ET.fromstring(r.content)
        for properties in root.findall(".//{*}properties"):
            date_node = properties.find("{*}NEW_DATE")
            value_node = properties.find("{*}BC_10YEAR")
            if date_node is None or value_node is None:
                continue
            date = pd.to_datetime(date_node.text, errors="coerce")
            value = pd.to_numeric(value_node.text, errors="coerce")
            if pd.notna(date) and pd.notna(value) and math.isfinite(float(value)) and date.normalize() <= today:
                observations.append((date, float(value)))
        if observations:
            break
    if not observations:
        raise ValueError("Treasury feed has no valid nominal 10-year observations")
    date, value = max(observations, key=lambda observation: observation[0])
    return round(value, 2), date.strftime("%Y-%m-%d")

WEBSITE_MARKETS_URL = 'https://script.google.com/macros/s/AKfycbwbr79vFr7xw1KcEKdB3kwKo6C9ECmolQ9DfcSeALCMgk0ZYLefB3Ka1a2iiWpIskM/exec'

@st.cache_data(ttl=120, show_spinner=False)
def _website_markets():
    if not _HAS_REQUESTS:
        raise RuntimeError("requests unavailable")
    with requests.Session() as session:
        response = session.get(WEBSITE_MARKETS_URL, params={"action": "markets"},
                               timeout=(3, 7), headers={"Accept": "application/json"})
        response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise ValueError("Website returned an unexpected market-data response")
    return payload

def _website_quote(payload, symbol):
    data = payload.get("data", {}).get(symbol)
    if not isinstance(data, dict) or isinstance(data.get("price"), bool):
        return None
    try:
        value = float(data["price"])
    except (KeyError, TypeError, ValueError):
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    # Quote timestamps describe prices; history dates are used for EOD yields.
    timestamp = pd.to_datetime(data.get("time"), unit="s", utc=True, errors="coerce")
    if pd.isna(timestamp):
        dates = pd.to_datetime(data.get("dates", []), utc=True, errors="coerce")
        dates = dates[dates.notna()]
        timestamp = dates.max() if len(dates) else pd.NaT
    if pd.isna(timestamp) or timestamp > pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=1):
        return None
    stale = bool(payload.get("stale")) or (pd.Timestamp.now(tz="UTC") - timestamp > pd.Timedelta(days=4))
    return {"value": value, "date": timestamp.strftime("%Y-%m-%d"),
            "as_of": timestamp.tz_convert("Asia/Kolkata").strftime("%d %b %Y %H:%M IST"),
            "stale": stale, "state": data.get("state")}

@st.cache_data(ttl=120, show_spinner=False)
def _direct_market_quote(symbol):
    # Same upstream provider as the website, reached independently.
    if not _HAS_REQUESTS:
        raise RuntimeError("requests unavailable")
    with requests.Session() as session:
        response = session.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/" + urlquote(symbol, safe=""),
            params={"range": "5d", "interval": "1d"}, timeout=(3, 7),
            headers={"User-Agent": _BROWSER_UA, "Accept": "application/json"})
        response.raise_for_status()
    chart = response.json().get("chart", {})
    results = chart.get("result")
    if chart.get("error") or not results:
        raise ValueError(f"Yahoo quote unavailable for {symbol}")
    meta = results[0].get("meta", {})
    quote = _website_quote({"data": {symbol: {"price": meta.get("regularMarketPrice"),
                                             "time": meta.get("regularMarketTime")}}}, symbol)
    if quote is None:
        raise ValueError(f"Yahoo returned no valid dated quote for {symbol}")
    quote["source"] = "Yahoo backup"
    return quote

def _backup_attempt(symbol, cooldowns):
    cached = cooldowns.get(symbol)
    if cached is not None and time.monotonic() < cached[0]:
        return cached[1], cached[2]
    try:
        result, error = _direct_market_quote(symbol), None
        duration = 120
    except Exception as exception:
        result, duration = None, 900
        if _HAS_REQUESTS and isinstance(exception, requests.HTTPError) and exception.response is not None and exception.response.status_code == 429:
            error = f"{symbol}: Yahoo rate limit reached; backup paused for 15 minutes"
        else:
            error = f"{symbol}: backup unavailable ({type(exception).__name__}); retry after cooldown"
    cooldowns[symbol] = (time.monotonic() + duration, result, error)
    return result, error

@st.cache_data(ttl=900, show_spinner=False)
def _ccil_far_holdings():
    """CCIL's indicative FPI holdings in FAR G-Secs, in INR crore."""
    if not _HAS_REQUESTS:
        raise RuntimeError("requests unavailable")
    params = {"p_p_id": "FPI_FPIPortlet_INSTANCE_rkvf", "p_p_lifecycle": "2",
              "p_p_state": "normal", "p_p_mode": "view", "p_p_resource_id": "FPI",
              "p_p_cacheability": "cacheLevelPage"}
    with requests.Session() as session:
        response = session.post("https://www.ccilindia.com/fpi-home-page", params=params,
                                data={}, timeout=(3, 7),
                                headers={"User-Agent": _BROWSER_UA, "Accept": "application/json"})
        response.raise_for_status()
    payload = response.json()
    rows = payload.get("result1")
    if isinstance(rows, str):
        rows = json.loads(rows)
    if not isinstance(rows, list) or not rows:
        raise ValueError("CCIL FAR holdings table is unavailable")
    total, seen = 0.0, set()
    for row in rows:
        isin = row.get("dfar_ismt_scnd_desc")
        if not isin or isin in seen:
            raise ValueError("CCIL FAR table contains missing or duplicate ISINs")
        seen.add(isin)
        value = float(row["dfar_totl_util_qnty"])
        if not math.isfinite(value) or value < 0:
            raise ValueError("CCIL FAR table contains invalid holdings")
        total += value
    # This response supplies no observation date; do not invent one.
    return {"value": total, "retrieved_at": pd.Timestamp.now(tz="Asia/Kolkata").strftime("%d %b %Y %H:%M IST"),
            "stale": False, "securities": len(rows)}

@st.cache_data(ttl=60, show_spinner=False)
def get_live_yields(fetch_india=False, _cooldowns=None):
    # Independent US sources run together; use the newest completed observation.
    out = {"us": None, "us_date": None, "us_source": None, "us_stale": False,
           "india": None, "india_date": None, "india_stale": False, "errors": [], "diagnostics": [], "markets": {}, "website_error": None, "fpi_holdings": None}
    pool = ThreadPoolExecutor(max_workers=5)
    jobs = {
        pool.submit(_ccil_far_holdings): ("fpi", "CCIL FAR holdings", 4),
        pool.submit(_website_markets): ("website", "Academy markets feed", 4),
        pool.submit(_fred_latest, "DGS10"): ("us", "FRED DGS10", 10),
        pool.submit(_treasury_latest): ("us", "US Treasury nominal 10Y par yield", 10),
    }
    if fetch_india:
        jobs[pool.submit(_fred_latest, "INDIRLTLT01STM")] = ("india", "FRED INDIRLTLT01STM", 100)
    done, pending = set(), set(jobs)
    deadline = time.monotonic() + 10
    while pending:
        finished, pending = wait(pending, timeout=max(0, deadline - time.monotonic()),
                                 return_when=FIRST_COMPLETED)
        done.update(finished)
        website_future = next(f for f in jobs if jobs[f][0] == "website")
        india_future = next((f for f in jobs if jobs[f][0] == "india"), None)
        website_ready = False
        website_finished = website_future in done
        india_finished = india_future is None or india_future in done
        if website_finished and india_finished:
            try:
                website_payload = website_future.result()
                required_symbols = ("^TNX", "USDINR=X", "BZ=F", "^VIX")
                quotes = [_website_quote(website_payload, symbol) for symbol in required_symbols]
                website_ready = all(quotes)
            except Exception:
                website_ready = False
        fpi_future = next(f for f in jobs if jobs[f][0] == "fpi")
        if website_ready and fpi_future in done:
            break
        if not finished or time.monotonic() >= deadline:
            break
    pool.shutdown(wait=False, cancel_futures=True)
    failures = []
    candidates = []
    website_us_stale = False
    for future in done:
        key, source, max_age = jobs[future]
        try:
            if key == "fpi":
                out["fpi_holdings"] = future.result()
                continue
            if key == "website":
                payload = future.result()
                for symbol in ("USDINR=X", "BZ=F", "^VIX", "^INDIAVIX"):
                    quote = _website_quote(payload, symbol)
                    if quote:
                        quote["source"] = "Academy / Yahoo"
                        out["markets"][symbol] = quote
                quote = _website_quote(payload, "^TNX")
                if quote:
                    website_us_stale = quote["stale"]
                    candidates.append((quote["date"], False, quote["value"], "Academy markets / FRED DGS10"))
                else:
                    out["website_error"] = "Website US 10Y observation is unavailable"
                continue
            value, date = future.result()
            if key == "us":
                candidates.append((date, source.startswith("US Treasury"), value, source))
            else:
                out[key], out[f"{key}_date"] = value, date
                age = _age_days(date)
                out[f"{key}_stale"] = age is not None and age > max_age
        except Exception as e:
            failures.append((key, f"{source}: {type(e).__name__}: {e}"))
    for future in pending:
        key, source, _ = jobs[future]
        future.cancel()
        failures.append((key, f"{source}: exceeded the 10-second wait limit"))
    # Use direct Yahoo only for missing quotes, never on every website refresh.
    missing = [symbol for symbol in ("USDINR=X", "BZ=F", "^VIX")
               if symbol not in out["markets"]]
    if missing:
        cooldowns = _cooldowns if _cooldowns is not None else {}
        backup_pool = ThreadPoolExecutor(max_workers=len(missing))
        backup_jobs = {backup_pool.submit(_backup_attempt, symbol, cooldowns): symbol for symbol in missing}
        completed, unfinished = wait(backup_jobs, timeout=5)
        backup_pool.shutdown(wait=False, cancel_futures=True)
        for future in completed:
            symbol = backup_jobs[future]
            quote, error = future.result()
            if quote is not None:
                out["markets"][symbol] = quote
            if error:
                failures.append(("market", error))
        for future in unfinished:
            future.cancel()
            failures.append(("market", f"{backup_jobs[future]}: backup wait limit reached"))
    if candidates:
        date, _, value, source = max(candidates)
        out["us"], out["us_date"], out["us_source"] = value, date, source
        age = _age_days(date)
        out["us_stale"] = (age is not None and age > 10) or (source.startswith("Academy") and website_us_stale)
    for key, message in failures:
        if key == "us" and out["us"] is not None:
            continue  # A successful US source makes redundant-source failures non-actionable.
        out["diagnostics"].append(message)
        if key == "website":
            out["website_error"] = message
        elif key not in ("market", "fpi") and out[key] is None:
            out["errors"].append(message)
    return out

def market_summary(live, india_yield, us_yield, spread_bps, manual):
    """Describe dashboard inputs without treating examples or stale quotes as live signals."""
    scores = []
    us_valid = not manual and live.get("us") is not None and not live.get("us_stale")
    if manual:
        us_text = f"US 10Y is {us_yield:.2f}% (manual input)."
    elif live.get("us") is None:
        us_text = f"US 10Y is {us_yield:.2f}% (illustrative reference; feed unavailable or off)."
    else:
        freshness = "lagged observation" if live.get("us_stale") else "published daily observation"
        us_text = f"US 10Y is {us_yield:.2f}% ({freshness}, as of {live.get('us_date')})."
    if us_valid:
        scores.append(2 if us_yield >= 4.75 else (1 if us_yield >= 4.55 else 0))
        us_text += " It is " + ("above" if us_yield >= 4.75 else "below") + " the dashboard's 4.75% teaching threshold."

    def describe_market(symbol, name, unit, critical, watch):
        quote = live.get("markets", {}).get(symbol)
        if quote is None:
            return f"{name} is unavailable."
        value = quote["value"]
        text = f"{name} is {unit}{value:.2f}, quoted {quote['as_of']}."
        if quote.get("stale") or quote.get("retained"):
            return text + " This is a stale or retained quote; it is excluded from the current signal count."
        score = 2 if value >= critical else (1 if value >= watch else 0)
        scores.append(score)
        status = ("above the critical teaching level" if score == 2 else
                  "in the watch band" if score == 1 else "below the watch band")
        return text + f" It is {status}; watch {watch:g}, critical {critical:g}."

    brent_text = describe_market("BZ=F", "Brent futures", "$", 90, 85)
    vix_text = describe_market("^VIX", "US VIX", "", 25, 18)
    inr_text = describe_market("USDINR=X", "USD/INR", "₹", 86, 85)
    if manual:
        india_source = "manual input"
    elif live.get("india") is None:
        india_source = "illustrative reference"
    else:
        india_source = f"monthly OECD observation as of {live.get('india_date')}"
    spread_text = (f"The India–US spread is {spread_bps} bps using India {india_yield:.2f}% "
                   f"({india_source}) and the displayed US yield. ")
    if manual or not us_valid or live.get("india") is None or live.get("india_stale"):
        spread_text += "This is an input-based calculation, not a verified current market spread."
    else:
        spread_text += "The two observations have different frequencies and may have different dates."
    holdings = live.get("fpi_holdings")
    if holdings is None:
        holdings_text = "FPI FAR G-Sec holdings are unavailable."
    else:
        state = "last successful retrieval" if holdings.get("stale") else "retrieved"
        holdings_text = (f"FPI FAR G-Sec holdings are ₹{holdings['value']:,.2f} crore "
                         f"(CCIL, {state} {holdings['retrieved_at']}). The source supplies no observation date. "
                         "This covers FAR government bonds only; a holdings level does not establish inflows or outflows.")
    if not scores:
        headline = "No current fetched signals available for comparison with the teaching thresholds."
    else:
        critical = scores.count(2)
        watch = scores.count(1)
        headline = (f"Of {len(scores)} usable fetched indicators, {critical} exceed critical teaching levels, "
                    f"{watch} are in watch bands and {scores.count(0)} are below watch bands. "
                    "Reference, manual and stale values are excluded from this count.")
    return headline, [us_text + " " + brent_text, vix_text + " " + inr_text,
                      spread_text + " " + holdings_text]

# -----------------------------------------------------------------------------
# GLOBAL STYLE
# -----------------------------------------------------------------------------
st.html(f"""
<style>
  .stApp {{
    background: linear-gradient(135deg,#1a2332,#243447,#2a3f5f) fixed;
  }}
  #MainMenu, header[data-testid="stHeader"], footer {{ visibility: hidden; }}
  .block-container {{ padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1200px; }}

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {{
    gap: 6px; background: rgba(17,34,64,.55); padding: 6px; border-radius: 12px;
    border: 1px solid rgba(255,215,0,.18); flex-wrap: wrap;
  }}
  .stTabs [data-baseweb="tab"] {{
    background: transparent; border-radius: 8px;
    padding: 8px 16px; font-weight: 600; font-size: 14px;
    color: #c7d3e8 !important; -webkit-text-fill-color: #c7d3e8 !important;
  }}
  .stTabs [data-baseweb="tab"] * {{
    color: #c7d3e8 !important; -webkit-text-fill-color: #c7d3e8 !important;
  }}
  .stTabs [aria-selected="true"] {{ background: {GOLD} !important; }}
  .stTabs [aria-selected="true"], .stTabs [aria-selected="true"] * {{
    color: {BLUE} !important; -webkit-text-fill-color: {BLUE} !important;
  }}
  .stTabs [data-baseweb="tab"] p {{ font-size: 14px; font-weight: 600; }}

  /* Force native widget text readable even if the base theme loads light */
  [data-testid="stWidgetLabel"] *, .stCheckbox *, [data-baseweb="checkbox"] label * {{
    color: {TXT} !important; -webkit-text-fill-color: {TXT} !important;
  }}
  /* Expander (Data settings) — dark surface + light header text */
  details, [data-testid="stExpander"] details {{
    background: {CARD} !important; border: 1px solid rgba(255,215,0,.18) !important;
    border-radius: 12px !important;
  }}
  details summary, details summary *,
  [data-testid="stExpander"] summary, [data-testid="stExpander"] summary * {{
    color: {TXT} !important; -webkit-text-fill-color: {TXT} !important;
  }}
  /* Refresh button */
  .stButton button {{
    background: {CARD} !important; border: 1px solid rgba(255,215,0,.35) !important;
  }}
  .stButton button p, .stButton button span, .stButton button div {{
    color: {GOLD} !important; -webkit-text-fill-color: {GOLD} !important;
  }}

  /* Slider accent */
  .stSlider [data-baseweb="slider"] div[role="slider"] {{ background: {GOLD}; }}

  /* Generic card look for our HTML blocks */
  .mp-card {{
    background: {CARD}; border: 1px solid rgba(255,215,0,.16);
    border-radius: 14px; padding: 18px 20px; margin-bottom: 14px;
    box-shadow: 0 4px 18px rgba(0,0,0,.28); user-select: none;
  }}
  .mp-card:hover {{ border-color: rgba(255,215,0,.42); }}
</style>
""")

# Small helpers -----------------------------------------------------------------
def html(s: str):
    st.html(s)

def plotly_theme(fig, height=420, legend=True):
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TXT, family="Inter, Segoe UI, sans-serif", size=13),
        margin=dict(l=20, r=20, t=50, b=20),
        hoverlabel=dict(bgcolor=CARD, font_color=TXT, bordercolor=GOLD),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(255,215,0,.2)",
                    borderwidth=1) if legend else dict(),
        showlegend=legend,
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,.06)", zeroline=False,
                     linecolor="rgba(255,255,255,.2)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,.06)", zeroline=False,
                     linecolor="rgba(255,255,255,.2)")
    return fig

# =============================================================================
# HEADER
# =============================================================================
html(f"""
<div style="background:linear-gradient(90deg,{BLUE},{MID});border-radius:16px;
     padding:22px 26px;border:1px solid rgba(255,215,0,.3);user-select:none;
     box-shadow:0 6px 24px rgba(0,0,0,.35);margin-bottom:6px;">
  <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
    <div style="font-size:34px;-webkit-text-fill-color:initial;">️</div>
    <div style="flex:1;min-width:260px;">
      <div style="color:{GOLD};-webkit-text-fill-color:{GOLD};font-size:13px;
           font-weight:700;letter-spacing:2px;">THE MOUNTAIN PATH ACADEMY · WORLD OF FINANCE</div>
      <div style="color:#ffffff;-webkit-text-fill-color:#ffffff;font-size:26px;
           font-weight:800;line-height:1.15;margin-top:2px;">
           India–US 10-Year Bond Yield Spread</div>
      <div style="color:{LB};-webkit-text-fill-color:{LB};font-size:14px;margin-top:3px;">
           Why the Gap Has Shrunk to a Multi-Decadal Low — and What It Means for India's Economy</div>
    </div>
    <div style="text-align:right;min-width:150px;">
      <div style="color:{MUTED};-webkit-text-fill-color:{MUTED};font-size:12px;">Educational Series by</div>
      <div style="color:#ffffff;-webkit-text-fill-color:#ffffff;font-size:15px;font-weight:700;">Prof. V. Ravichandran</div>
      <a href="{LINK_ACADEMY}" target="_blank"
         style="color:{GOLD};-webkit-text-fill-color:{GOLD};font-size:12px;text-decoration:none;">
         themountainpathacademy.com ↗</a>
    </div>
  </div>
</div>
""")

# =============================================================================
# "THINK ABOUT THIS" PROMPTS — shown while live data is being fetched
# =============================================================================
THINK_QS = [
    "If the spread falls to 180 bps, does it matter <i>which</i> yield moved to get there — the US or the Indian one? Why?",
    "A US investor earns 6.87% in India, but the rupee falls 3% over the year. Are they better or worse off than simply holding a US Treasury?",
    "Why does hedging the currency shrink a 222 bps spread down to barely ~12 bps of real pickup?",
    "If crude oil jumps to $100, trace the chain: what happens to the rupee, to inflation, and to the RBI's room to cut rates?",
    "Why can the RBI cut rates comfortably when the US Fed is <i>also</i> cutting, but not when US yields are rising?",
    "India holds $700bn+ in reserves. How does that change what a thin spread <i>means</i> today versus during the 2013 taper tantrum?",
    "A 10-year bond has duration ≈ 7. If Indian yields rise 0.5%, the price falls ~3.5% — how does that compare with a whole year's carry advantage?",
    "Global index inclusion adds steady foreign demand for G-secs. Does that push the spread up or down — and through which leg, India or the US?",
    "‘More sensitive at the margin, but structurally more resilient.’ What makes both halves of that statement true at once?",
    "If the spread narrows because Indian yields <i>fall</i>, why can that be bullish — the opposite of the same number reached by US yields rising?",
]

def _think_card():
    q = random.choice(THINK_QS)
    return (f"<div class='mp-card' style='border-color:rgba(255,215,0,.45);"
            f"background:linear-gradient(135deg,{CARD},#16203c);'>"
            f"<div style='color:{GOLD};-webkit-text-fill-color:{GOLD};font-weight:700;"
            f"font-size:14px;margin-bottom:4px;'> While the live data loads — think about this</div>"
            f"<div style='color:{TXT};-webkit-text-fill-color:{TXT};font-size:14px;"
            f"line-height:1.55;'>{q}</div></div>")

# =============================================================================
# DATA SETTINGS — live yields with manual override
# =============================================================================
with st.expander("⚙️  Data settings — latest published yields & manual override", expanded=False):
    tog_col, btn_col = st.columns([3, 1])
    with tog_col:
        use_live = st.toggle("Fetch latest published yields", value=True,
                             help="Academy markets, US Treasury and FRED provide daily yield observations, "
                                  "not intraday quotes. India is monthly. "
                                  "Successful downloads are cached for one hour.")
        fetch_india = st.toggle("Fetch monthly India OECD yield", value=False,
                                help="Optional monthly feed; it is not today's RBI 10Y benchmark. "
                                     "Leave off for faster loading; use manual yields for a current India rate.")
        manual = st.toggle("Use manual yield overrides", value=False,
                           help="Enable to edit yields. Disable to apply the latest fetched values.")
    with btn_col:
        if st.button("↻ Refresh", disabled=not use_live,
                     help="Download latest observations; manual overrides remain in effect"):
            _fred_latest.clear()
            _treasury_latest.clear()
            _website_markets.clear()
            # Preserve Yahoo cooldown even when Refresh is clicked.
            _ccil_far_holdings.clear()
            get_live_yields.clear()
    if use_live:
        with st.spinner("Checking Academy markets and official yield sources…"):
            live = get_live_yields(fetch_india, st.session_state.setdefault("yahoo_backup_cooldowns", {}))
    else:
        live = {"us": None, "us_date": None, "india": None, "india_date": None, "errors": []}
        st.caption("Fetching is off. Reference figures are illustrative; enable manual overrides to edit.")

    # Session state survives refreshes but is isolated per visitor. Keep dates unchanged.
    if use_live:
        saved_quotes = st.session_state.get("last_good_market_quotes", {})
        quotes = live.setdefault("markets", {})
        for symbol in ("USDINR=X", "BZ=F", "^VIX", "^INDIAVIX"):
            if symbol in quotes:
                saved_quotes[symbol] = dict(quotes[symbol])
            elif symbol in saved_quotes:
                quotes[symbol] = dict(saved_quotes[symbol], stale=True, retained=True)
        st.session_state["last_good_market_quotes"] = saved_quotes
        if live.get("fpi_holdings") is not None:
            st.session_state["last_good_fpi_holdings"] = dict(live["fpi_holdings"])
        elif st.session_state.get("last_good_fpi_holdings") is not None:
            live["fpi_holdings"] = dict(st.session_state["last_good_fpi_holdings"], stale=True)

    us_seed = live["us"] if live.get("us") is not None else DEFAULT_US
    ind_seed = live["india"] if live.get("india") is not None else DEFAULT_IND
    # Synchronize before constructing widgets. Never overwrite an active manual override.
    for key, seed in (("us_yield", us_seed), ("ind_yield", ind_seed)):
        if not manual or key not in st.session_state:
            st.session_state[key] = float(seed)

    def _src(val, date, sid, stale):
        if manual:
            return "Manual override — used in all calculations" + (f" · fetched {val:.2f}% as of {date}" if val is not None else " · automatic feed unavailable")
        if val is None:
            return "Illustrative reference figure — " + ("feed unavailable" if use_live else "fetching off")
        status = "Lagged observation — verify/override" if stale else "Latest published observation"
        source = live.get("us_source") if sid == "DGS10" else f"FRED {sid}"
        return f"{status} · {source} · as of {date}"

    cset = st.columns(2)
    with cset[0]:
        IND = st.number_input("India 10Y yield (%)", step=0.01, format="%.2f",
                              key="ind_yield", disabled=not manual)
        st.caption(_src(live.get("india"), live.get("india_date"),
                        "INDIRLTLT01STM", live.get("india_stale")))
    with cset[1]:
        USY = st.number_input("US 10Y yield (%)", step=0.01, format="%.2f",
                              key="us_yield", disabled=not manual)
        st.caption(_src(live.get("us"), live.get("us_date"), "DGS10", live.get("us_stale")))
    if live.get("website_error"):
        st.caption("Academy feed could not be fully read. Backup quotes or the last successful quotes are used where available.")
        st.caption(live["website_error"])
    if manual:
        st.info("Manual overrides are ON. Turn them OFF to apply downloaded yields automatically.")
    if use_live and live.get("errors"):
        st.warning("Some feeds could not be loaded. Illustrative reference figures are used "
                   "unless manual overrides are enabled.")
        for error in live["errors"]:
            st.caption(error)
    if use_live and not fetch_india:
        st.caption("India monthly feed is off. The India yield is an illustrative reference unless manually overridden.")
    if use_live and live.get("india") is not None:
        st.caption("India's OECD feed is monthly and can lag; use a manual override for today's G-Sec yield.")

SPREAD_BPS = round((IND - USY) * 100)
IS_LIVE = bool(use_live and not manual and live.get("us") is not None
               and not live.get("us_stale"))

# =============================================================================
# TABS
# =============================================================================
tabs = st.tabs([
    " Overview",
    " Key Terms",
    " Historical Spread",
    "⚖️ Breakeven Calculator",
    " Drivers & Implications",
    " Risk Triggers",
])

# -----------------------------------------------------------------------------
# TAB 1 — OVERVIEW
# -----------------------------------------------------------------------------
with tabs[0]:
    if IS_LIVE:
        badge = f"<span style='color:{GRN};-webkit-text-fill-color:{GRN};font-size:11px;'>● latest published US yield</span>"
        tail = f"{live.get('us_source')} as of {live.get('us_date')} · India source shown in Data settings · spread may mix observation dates"
    else:
        badge = f"<span style='color:{AMBER};-webkit-text-fill-color:{AMBER};font-size:11px;'>reference</span>"
        tail = "manual overrides in effect" if manual else "reference or lagged values · check Data settings"
    html(f"<div style='margin:2px 0 8px;color:{MUTED};-webkit-text-fill-color:{MUTED};font-size:12px;'>"
         f"Current yields {badge}<span style='color:{MUTED};-webkit-text-fill-color:{MUTED};'>"
         f" · {tail}</span></div>")
    metrics = [
        ("India 10Y G-Sec", f"{IND:.2f}%", "Norm ~7.5% · Lower", "India's disinflation success", GRN),
        ("US 10Y Treasury", f"{USY:.2f}%", "Norm ~2.5% · Higher", "Higher-for-longer Fed regime", RED),
        ("India–US Spread", f"{SPREAD_BPS} bps", "Norm 400–600 bps", "Multi-decadal (~15–20 yr) low", GOLD),
        ("FX Hedging Cost", "~2.10%", "Norm ~3.0% · Lower", "Consumes almost entire spread", AMBER),
    ]
    cols = st.columns(4)
    for c, (label, val, sub, note, col) in zip(cols, metrics):
        with c:
            html(f"""
            <div class="mp-card" style="text-align:left;padding:16px 18px;">
              <div style="color:{MUTED};-webkit-text-fill-color:{MUTED};font-size:12px;
                   font-weight:600;text-transform:uppercase;letter-spacing:1px;">{label}</div>
              <div style="color:{col};-webkit-text-fill-color:{col};font-size:30px;
                   font-weight:800;margin:4px 0;">{val}</div>
              <div style="color:{LB};-webkit-text-fill-color:{LB};font-size:12px;">{sub}</div>
              <div style="color:{TXT};-webkit-text-fill-color:{TXT};font-size:12px;
                   margin-top:6px;opacity:.85;">{note}</div>
            </div>""")

    c1, c2 = st.columns([1.35, 1])
    with c1:
        html(f"""
        <div class="mp-card">
          <div style="color:{GOLD};-webkit-text-fill-color:{GOLD};font-size:16px;
               font-weight:700;margin-bottom:8px;">⏱️ One-Minute Overview</div>
          <div style="color:{TXT};-webkit-text-fill-color:{TXT};font-size:14.5px;line-height:1.65;">
            India's 10-year government bond pays about <b style="color:{GOLD};-webkit-text-fill-color:{GOLD};">{IND:.2f}%</b>.
            The US 10-year Treasury pays about <b style="color:{LB};-webkit-text-fill-color:{LB};">{USY:.2f}%</b>.
            The difference — the <b>spread</b> — is about <b style="color:{GOLD};-webkit-text-fill-color:{GOLD};">{SPREAD_BPS} bps</b>.
            Historically this gap was <b>400–600+ bps</b> for most of the last two decades.
            Today's ~220 bps is roughly <b>one-third</b> of the historical norm and among the tightest
            in 15–20 years.
          </div>
        </div>
        <div class="mp-card" style="border-color:rgba(255,215,0,.42);background:linear-gradient(135deg,{CARD},#16203c);">
          <div style="color:{GOLD};-webkit-text-fill-color:{GOLD};font-size:15px;font-weight:700;margin-bottom:6px;">
             The Single Most Important Idea</div>
          <div style="color:{TXT};-webkit-text-fill-color:{TXT};font-size:14.5px;line-height:1.6;">
            A shrinking spread is <b>not automatically good or bad</b> for India. What matters is
            <b>which side is moving</b>. If the gap closes because <b style="color:{RED};-webkit-text-fill-color:{RED};">US yields rise</b>,
            that is a <b>warning</b>. If it closes because <b style="color:{GRN};-webkit-text-fill-color:{GRN};">Indian yields fall</b>,
            that can be <b>good news</b>.
          </div>
        </div>
        """)
    with c2:
        contents = [
            ("1", "Overview", "Key metrics & one-minute summary"),
            ("2", "Key Terms", "Bond yield, spread, carry, duration, hedging"),
            ("3", "Historical Spread", "20-year data with visualization"),
            ("4", "Breakeven Calculator", "Rupee depreciation scenarios"),
            ("5", "Drivers & Implications", "Rupee, RBI, and the economy"),
            ("6", "Risk Triggers", "Four triggers & monitoring dashboard"),
        ]
        rows = "".join(f"""
          <div style="display:flex;gap:10px;padding:7px 0;border-bottom:1px solid rgba(255,255,255,.06);">
            <div style="background:{GOLD};-webkit-text-fill-color:{BLUE};color:{BLUE};min-width:22px;height:22px;
                 border-radius:6px;text-align:center;font-weight:800;font-size:13px;line-height:22px;">{n}</div>
            <div><div style="color:{TXT};-webkit-text-fill-color:{TXT};font-weight:700;font-size:13.5px;">{t}</div>
            <div style="color:{MUTED};-webkit-text-fill-color:{MUTED};font-size:12px;">{d}</div></div>
          </div>""" for n, t, d in contents)
        html(f"""
        <div class="mp-card">
          <div style="color:{GOLD};-webkit-text-fill-color:{GOLD};font-size:16px;font-weight:700;margin-bottom:6px;">
             Workbook Contents</div>{rows}
        </div>""")

# -----------------------------------------------------------------------------
# TAB 2 — KEY TERMS
# -----------------------------------------------------------------------------
with tabs[1]:
    html(f"""<div style="color:{LB};-webkit-text-fill-color:{LB};font-size:14px;margin:2px 0 12px;">
         Essential financial terminology to understand the India–US Bond Yield Spread.</div>""")
    terms = [
        ("Government Bond Yield", "The annual return an investor earns for lending money to a government by buying its bond and holding it to maturity.", "Reflects a country's risk-free rate and inflation expectations."),
        ("Basis Point (bps)", "1/100th of a percentage point. 100 bps = 1%.", "Standard unit for measuring yield differences and rate changes."),
        ("The Spread", "India's 10-year yield MINUS the US 10-year yield.", "Compensation investors demand for taking Indian risk over US risk."),
        ("Carry", "The running income you earn just for holding a bond (the yield income).", "Higher carry = more incentive for foreign investors to invest in India."),
        ("Duration", "How much a bond's price falls (in %) when its yield rises by 1%. Indian 10Y duration ≈ 7.", "Measures interest-rate risk — bigger duration = bigger price swings."),
        ("Hedging Cost", "The cost of removing currency (FX) risk via forwards/swaps. Currently ~2.10%.", "Consumes almost the entire spread — hedged carry is barely profitable."),
        ("Carry Trade", "Borrowing in a low-yield currency (USD) to invest in a higher-yield currency (INR) to capture the spread.", "Main mechanism through which foreign capital flows into Indian bonds."),
        ("Real Yield", "Nominal bond yield MINUS expected inflation. India ~2.5%, US ~2.0%.", "True return after inflation — drives long-term capital allocation."),
        ("Risk-Off", "Global sentiment shift where investors flee risky (EM) assets for safe havens (US Treasuries, gold, USD).", "Triggers capital outflows from India and rupee weakness."),
        ("FX Reserves", "Foreign currency assets held by the RBI (currently $700bn+).", "India's buffer to defend the rupee during outflows."),
        ("Higher-for-Longer", "Post-2022 regime where the US Fed keeps interest rates elevated for extended periods.", "Key reason US 10Y yields have risen and the spread has compressed."),
    ]
    cc = st.columns(2)
    for i, (term, defn, why) in enumerate(terms):
        with cc[i % 2]:
            html(f"""
            <div class="mp-card">
              <div style="color:{GOLD};-webkit-text-fill-color:{GOLD};font-size:15.5px;font-weight:700;">{term}</div>
              <div style="color:{TXT};-webkit-text-fill-color:{TXT};font-size:13.5px;line-height:1.55;margin:6px 0;">{defn}</div>
              <div style="color:{LB};-webkit-text-fill-color:{LB};font-size:12.5px;line-height:1.5;">
                 <b style="color:{MUTED};-webkit-text-fill-color:{MUTED};">Why it matters — </b>{why}</div>
            </div>""")
    html(f"""
    <div class="mp-card" style="border-color:rgba(255,215,0,.42);">
      <div style="color:{TXT};-webkit-text-fill-color:{TXT};font-size:14px;line-height:1.6;">
         <b style="color:{GOLD};-webkit-text-fill-color:{GOLD};">Key Insight:</b>
        The spread is the compensation foreign investors demand for India-specific risks
        (currency depreciation, credit risk, political/policy risk). When the spread narrows,
        that compensation shrinks — and so does the incentive to hold Indian bonds.
      </div>
    </div>""")

# -----------------------------------------------------------------------------
# TAB 3 — HISTORICAL SPREAD
# -----------------------------------------------------------------------------
with tabs[2]:
    hist = pd.DataFrame({
        "Year": list(range(2005, 2026)),
        "India": [7.15,7.55,7.90,8.10,7.30,7.90,8.40,8.30,8.10,8.55,7.78,7.30,6.80,7.78,6.80,6.05,6.20,7.30,7.25,7.05,6.87],
        "US":    [4.29,4.80,4.63,3.66,3.26,3.22,2.78,1.80,2.35,2.54,2.14,1.84,2.33,2.91,2.14,0.89,1.45,2.95,3.88,4.20,4.65],
        "Context": ["Pre-GFC growth era","Rising rates globally","Peak pre-crisis yields",
            "GFC — US yields collapse","Post-GFC recovery","QE era begins","India high inflation",
            "Peak spread ~650 bps","Taper tantrum","Modi election rally","Oil crash, RBI cuts",
            "Demonetization","Fed hiking cycle","EM stress","Global slowdown","COVID — US yields ~0%",
            "Recovery, inflation building","Fed pivots to hikes","Higher-for-longer takes hold",
            "Spread compression accelerates","Multi-decadal low ~220 bps"],
    })
    hist["Spread_bps"] = ((hist["India"] - hist["US"]) * 100).round(0)

    st.markdown(f"<span style='color:{LB};font-size:14px;'>Illustrative annual averages — the "
                f"multi-decadal compression from 400–700+ bps down to ~220 bps.</span>",
                unsafe_allow_html=True)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=hist["Year"], y=hist["Spread_bps"], name="Spread (bps)",
                         marker_color=GOLD, opacity=0.35,
                         customdata=hist["Context"],
                         hovertemplate="<b>%{x}</b><br>Spread: %{y:.0f} bps<br>%{customdata}<extra></extra>"),
                  secondary_y=True)
    fig.add_trace(go.Scatter(x=hist["Year"], y=hist["India"], name="India 10Y",
                             line=dict(color=GOLD, width=3), mode="lines+markers"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=hist["Year"], y=hist["US"], name="US 10Y",
                             line=dict(color=LB, width=3), mode="lines+markers"),
                  secondary_y=False)
    fig.update_yaxes(title_text="Yield (%)", secondary_y=False)
    fig.update_yaxes(title_text="Spread (bps)", secondary_y=True, showgrid=False)
    fig.update_layout(title="India & US 10Y Yields and the Spread (2005–2025)",
                      barmode="overlay", hovermode="x unified")
    st.plotly_chart(plotly_theme(fig, height=460), use_container_width=True)

    s1, s2, s3, s4, s5 = st.columns(5)
    stats = [("20-Yr Avg Spread","446 bps",LB),("Median","466 bps",LB),
             ("Max (2012)","650 bps",RED),("Min (2025)","222 bps",GOLD),
             ("Current vs Avg","−224 bps",AMBER)]
    for col, (lab, val, c) in zip((s1,s2,s3,s4,s5), stats):
        with col:
            html(f"""<div class="mp-card" style="text-align:center;padding:14px 8px;">
                 <div style="color:{MUTED};-webkit-text-fill-color:{MUTED};font-size:11.5px;">{lab}</div>
                 <div style="color:{c};-webkit-text-fill-color:{c};font-size:22px;font-weight:800;">{val}</div>
                 </div>""")

    obs = ["Peak spread ~650 bps in 2012 during India's high-inflation period.",
           "Spread typically ranged 400–600 bps across 2005–2019.",
           "COVID (2020) briefly pushed the spread wider as US yields crashed to ~0.9%.",
           "Post-2022 'higher-for-longer' US regime + India's disinflation drove the compression.",
           "2025's ~220 bps is roughly one-third the 20-year average of ~450–500 bps."]
    lis = "".join(f"<li style='margin:4px 0;'>{o}</li>" for o in obs)
    html(f"""<div class="mp-card">
      <div style="color:{GOLD};-webkit-text-fill-color:{GOLD};font-weight:700;font-size:15px;margin-bottom:4px;">Key Observations</div>
      <ul style="color:{TXT};-webkit-text-fill-color:{TXT};font-size:13.5px;line-height:1.5;margin:0;padding-left:18px;">{lis}</ul>
    </div>""")

# -----------------------------------------------------------------------------
# TAB 4 — BREAKEVEN CALCULATOR
# -----------------------------------------------------------------------------
with tabs[3]:
    spread = IND - USY
    st.markdown(f"<span style='color:{LB};font-size:14px;'>How much rupee depreciation wipes out the "
                f"India–US 10Y spread for an <b>unhedged</b> US-dollar investor "
                f"(using India {IND:.2f}% − US {USY:.2f}% = {spread:.2f}%). Move the slider.</span>",
                unsafe_allow_html=True)

    left, right = st.columns([1, 1.25])
    with left:
        rupee = st.slider("Rupee move over 1-year holding period (%)  —  negative = depreciation",
                          min_value=-10.0, max_value=3.0, value=-2.0, step=0.1)
        net = IND + rupee                    # INR carry + FX move, in USD terms
        vs_ust = net - USY
        if vs_ust > 1.0:      verdict, vc = "Excellent — well ahead of US Treasuries", GRN
        elif vs_ust > 0.05:   verdict, vc = "Positive — still beats US Treasuries", GRN
        elif vs_ust >= -0.05: verdict, vc = "Breakeven — a tie with US Treasuries", GOLD
        elif vs_ust > -1.0:   verdict, vc = "Loss vs US Treasuries", AMBER
        else:                 verdict, vc = "Significant loss — capital flight risk", RED
        html(f"""
        <div class="mp-card" style="border-color:{vc};">
          <div style="display:flex;justify-content:space-between;gap:8px;">
            <div><div style="color:{MUTED};-webkit-text-fill-color:{MUTED};font-size:12px;">Net USD Return</div>
              <div style="color:{TXT};-webkit-text-fill-color:{TXT};font-size:28px;font-weight:800;">{net:.2f}%</div></div>
            <div><div style="color:{MUTED};-webkit-text-fill-color:{MUTED};font-size:12px;">vs US Treasury</div>
              <div style="color:{vc};-webkit-text-fill-color:{vc};font-size:28px;font-weight:800;">{vs_ust:+.2f}%</div></div>
          </div>
          <div style="margin-top:10px;color:{vc};-webkit-text-fill-color:{vc};font-weight:700;font-size:14px;">{verdict}</div>
          <div style="margin-top:8px;color:{MUTED};-webkit-text-fill-color:{MUTED};font-size:12px;line-height:1.5;">
            India carry {IND:.2f}% + FX move {rupee:+.2f}% = {net:.2f}% &nbsp;·&nbsp; minus US {USY:.2f}% = {vs_ust:+.2f}%
          </div>
        </div>
        <div class="mp-card" style="background:linear-gradient(135deg,{CARD},#16203c);">
          <div style="color:{GOLD};-webkit-text-fill-color:{GOLD};font-size:13px;font-weight:700;">Breakeven rupee depreciation</div>
          <div style="color:{TXT};-webkit-text-fill-color:{TXT};font-size:13.5px;line-height:1.55;margin-top:4px;">
            The rupee only has to fall <b style="color:{GOLD};-webkit-text-fill-color:{GOLD};">{spread:.2f}%</b> for a USD investor
            to earn <b>zero</b> extra return vs a US Treasury. Since the INR has historically fallen
            <b>3–4% a year</b>, the bond is a losing trade on average — and a <b>hedged</b> investor keeps only ~12 bps
            after the ~2.10% hedging cost.
          </div>
        </div>""")
    with right:
        xs = [i / 10 for i in range(-100, 31)]
        ys = [(IND + x) - USY for x in xs]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name="Return vs UST",
                                 line=dict(color=GOLD, width=3),
                                 hovertemplate="Rupee move %{x:.1f}%<br>vs UST %{y:+.2f}%<extra></extra>"))
        fig.add_hline(y=0, line_dash="dash", line_color=MUTED)
        fig.add_vline(x=-spread, line_dash="dot", line_color=LB)
        fig.add_trace(go.Scatter(x=[rupee], y=[vs_ust], mode="markers",
                                 marker=dict(color=vc, size=15, line=dict(color="white", width=1.5)),
                                 name="Your scenario",
                                 hovertemplate="You: %{x:.1f}%, %{y:+.2f}%<extra></extra>"))
        fig.add_annotation(x=-spread, y=0, text=f"Breakeven −{spread:.2f}%",
                           showarrow=True, arrowcolor=LB, font=dict(color=LB, size=12), ay=-40)
        fig.update_layout(title="Return vs US Treasury as the Rupee Moves",
                          xaxis_title="Rupee move (%)  ·  left = depreciation",
                          yaxis_title="Excess return vs UST (%)")
        st.plotly_chart(plotly_theme(fig, height=430, legend=False), use_container_width=True)

    moves  = [2.0, 0.0, -1.0, -2.0, -round(spread, 2), -3.0, -4.0, -6.0, -8.0, -10.0]
    labels = ["Strong Rupee","Stable Rupee","Mild Fall","Fall","Breakeven",
              "Moderate Fall","Sharp Fall","Crisis Fall","Severe Crisis","Taper-Tantrum"]
    def _outcome(vs):
        if vs > 1.5:   return "Excellent"
        if vs > 0.05:  return "Positive"
        if vs >= -0.05:return "Exactly breaks even"
        if vs > -1.0:  return "Loss vs UST"
        if vs > -3.0:  return "Significant loss"
        if vs > -5.0:  return "Major loss"
        return "2013-style shock"
    rows = []
    for lab, mv in zip(labels, moves):
        net = IND + mv
        vs  = net - USY
        rows.append({"Scenario": f"{lab} ({mv:+.2f}%)", "Rupee Move": f"{mv:+.2f}%",
                     "Net USD Return": f"{net:.2f}%", "vs US Treasury": f"{vs:+.2f}%",
                     "Outcome": _outcome(vs)})
    scen = pd.DataFrame(rows)
    st.markdown(f"<div style='color:{GOLD};font-weight:700;font-size:15px;margin:6px 0;'>"
                f"Rupee Depreciation Scenarios (1-Year Holding) — computed from India {IND:.2f}% / US {USY:.2f}%</div>",
                unsafe_allow_html=True)
    st.dataframe(scen, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# TAB 5 — DRIVERS & IMPLICATIONS
# -----------------------------------------------------------------------------
with tabs[4]:
    st.markdown(f"<div style='color:{GOLD};font-weight:700;font-size:16px;'>Part 1 · Drivers of Spread Compression</div>",
                unsafe_allow_html=True)
    drivers = pd.DataFrame({
        "Driver": ["India's Disinflation Success","US 'Higher-for-Longer' Fed","India's Sovereign Credibility",
                   "Global Bond Index Inclusion","US Fiscal Deficits","Softer Oil & Commodities"],
        "Direction": ["India Yields ↓","US Yields ↑","India Risk Premium ↓","Demand for INR bonds ↑",
                      "US Yields ↑","India Inflation ↓"],
        "Description": [
            "RBI's inflation targeting (4%±2%) anchored expectations; India 10Y drifted from 8%+ to ~6.87%.",
            "Post-2022 Fed regime keeps US rates elevated; US 10Y jumped from ~1.5% (2021) to ~4.65% (2025).",
            "Improved fiscal discipline, $700bn+ forex buffer, stable politics — investors demand less compensation.",
            "JP Morgan GBI-EM inclusion (June 2024) brought passive inflows, pushing India yields down.",
            "Ballooning US debt (~$34T+) and Treasury supply raise term premia on US bonds.",
            "Contained oil prices reduce imported inflation, allowing lower India yields."],
    })
    st.dataframe(drivers, use_container_width=True, hide_index=True)

    st.markdown(f"<div style='color:{GOLD};font-weight:700;font-size:16px;margin-top:10px;'>Part 2 · Impact on the Rupee (INR)</div>",
                unsafe_allow_html=True)
    inr = pd.DataFrame({
        "Aspect": ["Carry-Trade Cushion","Foreign Portfolio Flows","INR Volatility","Imported Inflation Risk"],
        "Before (wide spread)": ["400–600 bps buffer","Strong bond inflows","Lower","Manageable"],
        "After (narrow spread)": ["~220 bps buffer","Marginal / volatile","Higher","Elevated"],
        "Risk Level": ["HIGH","HIGH","MEDIUM","MEDIUM-HIGH"],
    })
    st.dataframe(inr, use_container_width=True, hide_index=True)

    html("""
<style>
.fed-panel{background:#112240;border:1px solid #355071;border-radius:18px;padding:26px;margin:16px 0 24px;color:#e6f1ff;font-family:inherit}
.fed-panel *{box-sizing:border-box;-webkit-text-fill-color:currentColor}
.fed-eyebrow{color:#FFD700;font-size:14px;font-weight:700;letter-spacing:.06em;text-transform:uppercase}
.fed-panel h3{color:#e6f1ff;font-size:24px;line-height:1.3;margin:8px 0}
.fed-intro{color:#c3cee2;font-size:16px;line-height:1.6;margin:0 0 22px}
.fed-paths{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}
.fed-path{--accent:#ffabb3;--tint:#36253b;border:1px solid #805061;border-radius:14px;padding:20px;background:#14233b}
.fed-path.cut{--accent:#8ee4c2;--tint:#193c3d;border-color:#386f65}
.fed-path h4{color:var(--accent);font-size:21px;line-height:1.4;margin:0 0 6px}
.fed-sub{color:#c3cee2;font-size:14px;line-height:1.5;margin:0 0 18px}
.fed-steps{list-style:none;margin:0;padding:0;counter-reset:step}
.fed-steps li{position:relative;background:#1b304c;border-radius:9px;padding:12px 14px 12px 46px;font-size:16px;line-height:1.5;margin:0 0 27px;counter-increment:step;color:#e6f1ff}
.fed-steps li:before{content:counter(step);position:absolute;left:14px;top:13px;color:var(--accent);font-size:14px;font-weight:800}
.fed-steps li:after{content:'↓';position:absolute;left:50%;bottom:-25px;color:var(--accent);font-size:20px;line-height:24px}
.fed-outcome{background:var(--tint);border:1px solid var(--accent);border-radius:10px;padding:15px;color:#e6f1ff;font-size:16px;line-height:1.6}
.fed-outcome strong{display:block;color:var(--accent);font-size:18px;margin-bottom:3px}
.fed-decision{border-top:1px solid #355071;margin-top:24px;padding-top:20px}
.fed-decision h4{color:#FFD700;font-size:18px;margin:0 0 12px}
.fed-choices{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.fed-choice{border:1px solid #355071;border-radius:10px;padding:14px;font-size:15px;line-height:1.6;color:#c3cee2}
.fed-choice b{display:block;color:#e6f1ff;font-size:16px;margin-bottom:4px}
.fed-note{color:#c3cee2;font-size:14px;line-height:1.65;margin:18px 0 0}
.fed-note b{color:#FFD700}
@media(max-width:700px){.fed-paths,.fed-choices{grid-template-columns:1fr}.fed-panel{padding:18px}.fed-path{padding:16px}.fed-panel h3{font-size:22px}}

.fed-path.neutral{--accent:#ffe08a;--tint:#373529;border-color:#786b42}
.fed-path summary{cursor:pointer;color:var(--accent);font-size:18px;font-weight:700;line-height:1.5;min-height:44px}
.fed-path summary:focus-visible{outline:2px solid #FFD700;outline-offset:5px}
.fed-path[open] summary{margin-bottom:14px}
.fed-group{color:#FFD700;font-size:19px;line-height:1.4;margin:26px 0 14px}
.fed-key{display:flex;flex-wrap:wrap;gap:10px 20px;color:#c3cee2;font-size:14px;margin:0 0 18px}
</style>
<section class="fed-panel" aria-labelledby="fed-title">
<div class="fed-eyebrow">Part 3 · Fed–RBI scenario guide</div>
<h3 id="fed-title">Different rate decisions. Different paths for India.</h3>
<p class="fed-intro">The RBI does not automatically follow the Fed. Explore all nine rate combinations, then see how a recession or oil shock can change the outcome. Open any scenario to follow the steps.</p>
<div class="fed-key"><span style="color:#ffabb3">Red: potential currency pressure</span><span style="color:#8ee4c2">Green: potential currency support</span><span style="color:#ffe08a">Gold: depends on relative moves or other forces</span></div>
<p class="fed-note"><b>Two different gaps:</b> The policy-rate gap compares central-bank rates. This dashboard’s bond-yield spread compares Indian and US 10-year government bond yields. They can move differently. “Widens” means India’s rate minus the US rate increases; it does not guarantee a positive gap.</p>
<h4 class="fed-group">01–09 · Rate combinations</h4><div class="fed-paths">
<details class="fed-path " open><summary>01 · Fed raises · RBI holds</summary><p class="fed-sub">US tightens while India waits</p><ol class="fed-steps"><li>US policy rate rises; India’s policy rate stays unchanged.</li><li>India’s policy-rate advantage narrows. If bond yields follow, its bond-yield advantage narrows too.</li><li>Outflow pressure may increase → rupee may weaken → imported inflation pressure may rise.</li></ol><div class="fed-outcome"><strong>Less room for future RBI cuts</strong>The RBI may continue to hold or raise rates if Indian inflation requires it.</div></details><details class="fed-path cut" open><summary>02 · Fed cuts · RBI holds</summary><p class="fed-sub">US eases while India waits</p><ol class="fed-steps"><li>US policy rate falls; India’s policy rate stays unchanged.</li><li>India’s policy-rate advantage widens. If bond yields follow, Indian bonds may become relatively more attractive.</li><li>Inflows may support the rupee → currency-driven import-cost pressure may ease.</li></ol><div class="fed-outcome"><strong>More room for a later RBI cut</strong>The RBI may cut if Indian inflation allows and growth needs support.</div></details><details class="fed-path "><summary>03 · Fed raises · RBI cuts</summary><p class="fed-sub">Policies move in opposite directions</p><ol class="fed-steps"><li>US policy rate rises while India’s policy rate falls.</li><li>India’s policy-rate advantage narrows from both sides; bond yields may also move closer.</li><li>Currency and outflow pressure may increase, complicating India’s inflation outlook.</li></ol><div class="fed-outcome"><strong>A harder growth–inflation trade-off</strong>An RBI cut can support weak growth, but currency pressure may constrain further easing.</div></details><details class="fed-path cut"><summary>04 · Fed cuts · RBI raises</summary><p class="fed-sub">India tightens while the US eases</p><ol class="fed-steps"><li>US policy rate falls while India’s policy rate rises.</li><li>India’s policy-rate advantage widens from both sides; this may support demand for Indian assets.</li><li>The rupee may gain support, while higher Indian borrowing costs restrain domestic demand.</li></ol><div class="fed-outcome"><strong>Indian inflation takes priority</strong>The RBI may still raise rates when domestic inflation is too high.</div></details><details class="fed-path neutral"><summary>05 · Fed raises · RBI raises</summary><p class="fed-sub">Both tighten: compare the size of the hikes</p><ol class="fed-steps"><li>Both central banks raise their policy rates.</li><li>RBI hikes more → policy gap widens. Fed hikes more → gap narrows. Equal hikes → gap unchanged.</li><li>Capital flows and the rupee depend on bond yields, expectations and risk—not simply on both banks hiking.</li></ol><div class="fed-outcome"><strong>Following is not automatic</strong>The RBI’s hike should be understood through India’s inflation and growth conditions.</div></details><details class="fed-path neutral"><summary>06 · Fed cuts · RBI cuts</summary><p class="fed-sub">Both ease: compare the size of the cuts</p><ol class="fed-steps"><li>Both central banks lower their policy rates.</li><li>Fed cuts more → policy gap widens. RBI cuts more → gap narrows. Equal cuts → gap unchanged.</li><li>Lower Indian borrowing costs may support growth; the currency effect depends on relative yields and risk.</li></ol><div class="fed-outcome"><strong>The size of each cut matters</strong>Both banks cutting does not by itself tell us whether India’s yield spread will widen or narrow.</div></details><details class="fed-path "><summary>07 · Fed holds · RBI cuts</summary><p class="fed-sub">India eases on its own</p><ol class="fed-steps"><li>US policy rate is unchanged; India’s policy rate falls.</li><li>India’s policy-rate advantage narrows; Indian bond yields may fall relative to US yields.</li><li>Growth may benefit, but outflow and rupee pressure may increase.</li></ol><div class="fed-outcome"><strong>Further cuts may become harder</strong>The RBI weighs growth support against inflation and currency pressures.</div></details><details class="fed-path cut"><summary>08 · Fed holds · RBI raises</summary><p class="fed-sub">India tightens on its own</p><ol class="fed-steps"><li>US policy rate is unchanged; India’s policy rate rises.</li><li>India’s policy-rate advantage widens, potentially supporting demand for rupee assets.</li><li>The rupee may gain support; higher borrowing costs may slow spending and investment.</li></ol><div class="fed-outcome"><strong>Inflation control has a growth cost</strong>The RBI may choose this path when Indian inflation needs restraint.</div></details><details class="fed-path neutral"><summary>09 · Fed holds · RBI holds</summary><p class="fed-sub">Policy rates pause; markets can still move</p><ol class="fed-steps"><li>Neither central bank changes its policy rate.</li><li>The policy-rate gap stays unchanged, but 10-year bond yields can still change.</li><li>Inflation news, oil prices, government borrowing and global risk can move the spread and the rupee.</li></ol><div class="fed-outcome"><strong>A pause is not a market freeze</strong>The RBI watches incoming data before deciding its next move.</div></details></div>
<h4 class="fed-group">10–11 · Shocks that can change the story</h4><div class="fed-paths"><details class="fed-path neutral"><summary>10 · Fed cuts during a global recession</summary><p class="fed-sub">A rate cut can coexist with a weaker rupee</p><ol class="fed-steps"><li>The Fed cuts as the global outlook deteriorates.</li><li>Investors may seek safety in dollars and reduce exposure to emerging markets.</li><li>Money may leave India → rupee may weaken, even as US policy rates fall.</li></ol><div class="fed-outcome"><strong>Relief is not guaranteed</strong>The RBI balances weaker growth against currency and inflation pressures.</div></details><details class="fed-path "><summary>11 · Oil prices jump · any Fed decision</summary><p class="fed-sub">An external shock can outweigh rate relief</p><ol class="fed-steps"><li>India’s dollar cost of oil imports rises, other things equal.</li><li>A larger import bill may pressure the rupee; higher energy costs can add to inflation.</li><li>Even a Fed cut may provide too little relief to offset the oil shock.</li></ol><div class="fed-outcome"><strong>RBI may have less room to ease</strong>Its response depends on how persistent the shock is and how widely it lifts prices.</div></details></div>
<div class="fed-decision"><h4>What ultimately guides the RBI?</h4><div class="fed-choices">
<div class="fed-choice"><b>Indian inflation</b>High or persistent inflation can favour holding or raising rates.</div>
<div class="fed-choice"><b>Indian growth</b>Weak growth with contained inflation can create room for a cut.</div>
<div class="fed-choice"><b>Currency &amp; financial conditions</b>Rupee pressure may constrain easing. Forex intervention can help smooth volatility.</div>
</div></div>
<p class="fed-note"><b>Possible paths, not predictions.</b> Market expectations, hedging costs, risk appetite and the size of each move matter. A decision already priced in may have little immediate effect. Green means potential currency support—not that higher rates are better for the whole economy.</p>
</section>""")
    html(f"""
    <div class="mp-card" style="border-color:rgba(40,167,69,.45);">
      <div style="color:{GRN};-webkit-text-fill-color:{GRN};font-weight:700;font-size:15px;">
        ✅ Bottom Line — 'More Sensitive at the Margin, Structurally More Resilient'</div>
      <div style="color:{TXT};-webkit-text-fill-color:{TXT};font-size:14px;line-height:1.6;margin-top:6px;">
        The compressed spread is a signal of <b>maturity</b> — India has earned a lower risk premium through
        disinflation, fiscal credibility, and index inclusion. But maturity brings new constraints: the RBI has
        less policy autonomy, and the INR carries more day-to-day volatility. India is
        <b style="color:{AMBER};-webkit-text-fill-color:{AMBER};">more sensitive at the margin</b>, but
        <b style="color:{GRN};-webkit-text-fill-color:{GRN};">structurally more resilient</b> than any prior cycle.
      </div>
    </div>""")

# -----------------------------------------------------------------------------
# TAB 6 — RISK TRIGGERS
# -----------------------------------------------------------------------------
with tabs[5]:
    st.markdown(f"<div style='color:{GOLD};font-weight:700;font-size:16px;'>Part 1 · The Four Triggers to Watch</div>",
                unsafe_allow_html=True)
    triggers = [
        ("1","US 10Y Yield Rising",">4.75% breakout","Higher US yields → capital rotation to USD → INR down","HIGH",RED),
        ("2","Oil Prices Rising",">$90/bbl sustained","Oil ↑ → import bill ↑ → INR ↓ → RBI can't cut","HIGH",RED),
        ("3","Global Risk-Off","VIX >25, EM outflows","Risk-off → FII outflows → INR weakness → yields up","MEDIUM-HIGH",AMBER),
        ("4","Rupee Weakness Itself",">₹86/USD, >3% YTD fall","INR ↓ → outflows → INR ↓ (feedback loop)","HIGH",RED),
    ]
    tc = st.columns(2)
    for i,(n,t,th,ch,sev,c) in enumerate(triggers):
        with tc[i%2]:
            html(f"""
            <div class="mp-card">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <div style="color:{TXT};-webkit-text-fill-color:{TXT};font-weight:700;font-size:15px;">
                  <span style="color:{GOLD};-webkit-text-fill-color:{GOLD};">#{n}</span> {t}</div>
                <div style="background:{c};-webkit-text-fill-color:#fff;color:#fff;font-size:11px;font-weight:700;
                     padding:3px 9px;border-radius:20px;">{sev}</div>
              </div>
              <div style="color:{GOLD};-webkit-text-fill-color:{GOLD};font-size:12.5px;font-weight:600;margin:5px 0;">Threshold: {th}</div>
              <div style="color:{MUTED};-webkit-text-fill-color:{MUTED};font-size:12.5px;line-height:1.5;">{ch}</div>
            </div>""")

    st.markdown(f"<div style='color:{GOLD};font-weight:700;font-size:16px;margin-top:6px;'>"
                "Part 2 · Market Monitoring Dashboard</div>", unsafe_allow_html=True)
    st.caption("Academy markets: FX, Brent futures and VIX are delayed or last available quotes; US yields are end-of-day. "
               "Click Refresh in Data settings to update. Thresholds are illustrative teaching levels.")
    us_stat = ("Critical", RED) if USY >= 4.75 else (("Watch", AMBER) if USY >= 4.55 else ("Safe", GRN))
    sp_stat = ("Critical", RED) if SPREAD_BPS <= 200 else (("Watch", AMBER) if SPREAD_BPS <= 240 else ("Safe", GRN))
    def market_card(label, symbol, threshold, watch):
        quote = live.get("markets", {}).get(symbol)
        if quote is None:
            return (label, "—", str(threshold), "Unavailable", MUTED, "No current quote from Academy markets")
        value = quote["value"]
        status, color = ("Critical", RED) if value >= threshold else (("Watch", AMBER) if value >= watch else ("Safe", GRN))
        if quote["stale"]:
            status, color = "Stale — verify", AMBER
        source = quote.get("source", "Academy / Yahoo")
        as_of = quote["as_of"]
        if quote.get("retained"):
            freshness = "retained after refresh failure"
        else:
            freshness = "delayed or last quote"
        note = f"{source} · {as_of} · {freshness}"
        return label, f"{value:.2f}", str(threshold), status, color, note

    us_note = ("Manual override" if manual else
               (f"{live.get('us_source')} · {live.get('us_date')}" if live.get("us") is not None
                else "Illustrative reference — no fetched US yield"))
    holdings = live.get("fpi_holdings")
    if holdings is None:
        fpi_card = ("FPI G-Sec holdings — FAR (₹ cr)", "—", "N/A", "Unavailable", MUTED,
                    "CCIL holdings feed unavailable")
    else:
        fpi_status = "Last successful fetch" if holdings["stale"] else "Reported holdings"
        fpi_card = ("FPI G-Sec holdings — FAR (₹ cr)", f"{holdings['value']:,.2f}", "N/A", fpi_status,
                    AMBER if holdings["stale"] else LB,
                    "CCIL · retrieved " + holdings["retrieved_at"] + " · source observation date not supplied")
    st.caption("FPI holdings: CCIL indicative FAR government-bond holdings only, in ₹ crore; "
               "excludes general-route, corporate and state bonds. Retrieval time is shown because the feed supplies no observation date.")
    dash = [
        ("US 10Y Treasury", f"{USY:.2f}%", "4.75%", us_stat[0] if manual or live.get("us") is not None else "Reference",
         us_stat[1] if manual or live.get("us") is not None else MUTED, us_note),
        market_card("Brent futures ($/bbl)", "BZ=F", 90, 85),
        market_card("US VIX Index", "^VIX", 25, 18),
        market_card("USD/INR", "USDINR=X", 86, 85),
        ("India–US Spread (bps)", f"{SPREAD_BPS}", "200", sp_stat[0], sp_stat[1], "Computed from displayed yields; India may be monthly or reference"),
        fpi_card,
    ]
    if live.get("diagnostics"):
        with st.expander("Market feed connection details", expanded=False):
            for detail in live["diagnostics"]:
                st.caption(detail)
    dcols = st.columns(3)
    for i,(ind,cur,thr,stat,c,act) in enumerate(dash):
        with dcols[i%3]:
            html(f"""
            <div class="mp-card" style="padding:14px 16px;">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <div style="color:{TXT};-webkit-text-fill-color:{TXT};font-size:13px;font-weight:700;">{ind}</div>
                <span style="width:10px;height:10px;border-radius:50%;background:{c};display:inline-block;"></span>
              </div>
              <div style="color:{c};-webkit-text-fill-color:{c};font-size:24px;font-weight:800;margin:2px 0;">{cur}</div>
              <div style="color:{MUTED};-webkit-text-fill-color:{MUTED};font-size:11.5px;">Threshold {thr} ·
                <b style="color:{c};-webkit-text-fill-color:{c};">{stat}</b></div>
              <div style="color:{LB};-webkit-text-fill-color:{LB};font-size:11.5px;margin-top:4px;">{escape(act)}</div>
            </div>""")

    summary_headline, summary_paragraphs = market_summary(live, IND, USY, SPREAD_BPS, manual)
    summary_body = "".join(
        f"<p style='margin:8px 0;color:{TXT};line-height:1.65;'>{escape(paragraph)}</p>"
        for paragraph in summary_paragraphs)
    html(f"<div class='mp-card' style='border-color:rgba(255,215,0,.4);'>"
         f"<div style='color:{GOLD};font-size:17px;font-weight:700;'>Dashboard Market Summary</div>"
         f"<p style='color:{LB};line-height:1.55;'>{escape(summary_headline)}</p>"
         f"<div style='font-size:13.5px;'>{summary_body}</div>"
         f"<p style='color:{MUTED};font-size:11.5px;margin-bottom:0;'>"
         "Updates from the displayed dashboard values on refresh or input changes. "
         "Quotes are delayed or end-of-day; teaching thresholds are illustrative.</p></div>")

    st.markdown(f"<div style='color:{GOLD};font-weight:700;font-size:16px;margin-top:6px;'>Part 3 · Scenario Playbook — What Happens If…</div>",
                unsafe_allow_html=True)
    play = pd.DataFrame({
        "Scenario": ["US 10Y hits 5.0%","Oil spikes to $100","Global risk-off (Lehman-style)",
                     "India CPI stays <4%","Fed pivots to cuts"],
        "Probability": ["Medium","Medium","Low","High","Medium"],
        "Impact on Spread": ["Narrows to ~180 bps","Neutral (both yields up)","Widens (India yields spike)",
                             "Narrows further (India ↓)","Widens (US yields ↓)"],
        "INR Impact": ["86–87","87–88","88–90 briefly","Stable/mild weakness","Strengthens to 83"],
        "RBI Response": ["FX intervention + pause cuts","Sell USD reserves","Emergency liquidity",
                         "Room for 25–50 bps cuts","Comfortable — can cut too"],
        "Investor Playbook": ["Reduce EM bond exposure","Hedge via commodities","Move to cash/gold",
                              "Add duration in India bonds","Overweight EM bonds"],
    })
    st.dataframe(play, use_container_width=True, hide_index=True)

    html(f"""
    <div class="mp-card" style="border-color:rgba(255,215,0,.42);">
      <div style="color:{TXT};-webkit-text-fill-color:{TXT};font-size:14px;line-height:1.6;">
         <b style="color:{GOLD};-webkit-text-fill-color:{GOLD};">Key Takeaway:</b>
        A narrow spread is a <b>warning light, not a crisis</b>. As long as India's structural buffers hold
        (FX reserves, fiscal discipline, anchored inflation, robust equity flows), the compressed spread is
        manageable. But policy autonomy is now smaller — every RBI decision must weigh the global cycle first.
      </div>
    </div>""")

# =============================================================================
# FOOTER
# =============================================================================
html(f"""
<div style="margin-top:20px;background:linear-gradient(90deg,{BLUE},{MID});border-radius:16px;
     padding:20px 26px;border:1px solid rgba(255,215,0,.3);user-select:none;">
  <div style="display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;align-items:center;">
    <div>
      <div style="color:{GOLD};-webkit-text-fill-color:{GOLD};font-size:15px;font-weight:800;">
        The Mountain Path — World of Finance</div>
      <div style="color:{LB};-webkit-text-fill-color:{LB};font-size:12.5px;margin-top:2px;">
        Bridging Theory with Practice · Excellence in Financial Education</div>
      <div style="color:{MUTED};-webkit-text-fill-color:{MUTED};font-size:11.5px;margin-top:6px;">
        Prof. V. Ravichandran · Visiting Professor & Professor of Practice at Leading Business Schools ·
        28+ Years Corporate Finance & Banking</div>
    </div>
    <div style="text-align:right;display:flex;flex-direction:column;gap:6px;">
      <a href="{LINK_ACADEMY}" target="_blank" style="color:{GOLD};-webkit-text-fill-color:{GOLD};
         font-weight:700;font-size:13px;text-decoration:none;"> themountainpathacademy.com ↗</a>
      <a href="{LINK_LI}" target="_blank" style="color:{GOLD};-webkit-text-fill-color:{GOLD};
         font-weight:700;font-size:13px;text-decoration:none;">in · LinkedIn ↗</a>
      <a href="{LINK_GH}" target="_blank" style="color:{GOLD};-webkit-text-fill-color:{GOLD};
         font-weight:700;font-size:13px;text-decoration:none;">⌥ GitHub ↗</a>
    </div>
  </div>
  <div style="color:{MUTED};-webkit-text-fill-color:{MUTED};font-size:11px;margin-top:12px;
       border-top:1px solid rgba(255,255,255,.1);padding-top:8px;">
    Educational content only — not investment advice. Figures are illustrative of the current regime and
    should be refreshed against live market data.</div>
</div>
""")
