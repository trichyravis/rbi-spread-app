
# =============================================================================
# The Mountain Path Academy — India–US 10Y Bond Yield Spread
# Educational Streamlit App  |  Prof. V. Ravichandran
# https://themountainpathacademy.com
# =============================================================================
import io
import random
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
    page_icon="📊",
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
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    r = requests.get(url, timeout=15,
                     headers={"User-Agent": _BROWSER_UA, "Accept": "text/csv,*/*"})
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df = df.iloc[:, :2]
    df.columns = ["date", "value"]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna()
    if df.empty:
        return None
    last = df.iloc[-1]
    return round(float(last["value"]), 2), str(last["date"])

def _age_days(date_str):
    try:
        return int((pd.Timestamp.now().normalize() - pd.to_datetime(date_str)).days)
    except Exception:
        return None

def get_live_yields():
    # Not cached here: successful values are cached inside _fred_latest (1h);
    # failures raise there (uncached) so a cold-start timeout retries next run
    # instead of pinning "reference" for an hour.
    out = {"us": None, "us_date": None, "us_stale": False,
           "india": None, "india_date": None, "india_stale": False, "errors": []}
    for key, sid, max_age in (("us", "DGS10", 10), ("india", "INDIRLTLT01STM", 100)):
        try:
            res = _fred_latest(sid)
            if res:
                out[key], out[f"{key}_date"] = res
                age = _age_days(out[f"{key}_date"])
                out[f"{key}_stale"] = (age is not None and age > max_age)
        except Exception as e:  # network off, cloud restriction, format change
            out["errors"].append(f"{key.upper()} ({sid}): {type(e).__name__}")
    return out

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
    <div style="font-size:34px;-webkit-text-fill-color:initial;">🏔️</div>
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
            f"font-size:14px;margin-bottom:4px;'>💭 While the live data loads — think about this</div>"
            f"<div style='color:{TXT};-webkit-text-fill-color:{TXT};font-size:14px;"
            f"line-height:1.55;'>{q}</div></div>")

# =============================================================================
# DATA SETTINGS — live yields with manual override
# =============================================================================
with st.expander("⚙️  Data settings — live yields (FRED) & manual override", expanded=False):
    tog_col, btn_col = st.columns([3, 1])
    with tog_col:
        use_live = st.toggle("Fetch live yields from FRED", value=False,
                             help="Off by default so the app loads instantly with reference figures. "
                                  "Turn on to pull real-time US 10Y (DGS10) and India 10Y "
                                  "(INDIRLTLT01STM) from FRED — takes a few seconds. Cached for 1 hour.")
    with btn_col:
        if use_live and st.button("↻ Refresh", help="Clear the cache and re-fetch live yields now"):
            _fred_latest.clear()
            st.rerun()

    if use_live:
        if not st.session_state.get("live_fetched", False):
            # First fetch of the session (the slow one): show a thinking prompt while waiting
            think_ph = st.empty()
            with think_ph.container():
                html(_think_card())
            with st.spinner("Fetching live yields from FRED…"):
                live = get_live_yields()
            think_ph.empty()
            st.session_state["live_fetched"] = True
        else:
            # Values are cached now — instant, no prompt/flash on later reruns
            live = get_live_yields()
    else:
        html(f"<div style='color:{AMBER};-webkit-text-fill-color:{AMBER};font-size:12px;margin:2px 0 6px;'>"
             f"⚡ Showing reference figures for an instant load — turn on "
             f"<b>Fetch live yields from FRED</b> above for real-time data.</div>")
        live = {"us": None, "us_date": None, "india": None, "india_date": None, "errors": []}
    us_seed  = live["us"]    if live.get("us")    is not None else DEFAULT_US
    ind_seed = live["india"] if live.get("india") is not None else DEFAULT_IND

    def _src(val, date, sid, stale):
        if val is None:
            return f"<span style='color:{MUTED};-webkit-text-fill-color:{MUTED};'>reference figure (feed unavailable)</span>"
        if stale:
            return (f"<span style='color:{AMBER};-webkit-text-fill-color:{AMBER};'>● lagged feed</span>"
                    f"<span style='color:{MUTED};-webkit-text-fill-color:{MUTED};'> · FRED {sid} · as of {date} — verify/override</span>")
        return (f"<span style='color:{GRN};-webkit-text-fill-color:{GRN};'>● live</span>"
                f"<span style='color:{MUTED};-webkit-text-fill-color:{MUTED};'> · FRED {sid} · as of {date}</span>")

    cset = st.columns(2)
    with cset[0]:
        IND = st.number_input("India 10Y yield (%)", value=float(ind_seed), step=0.01,
                              format="%.2f", key="ind_yield")
        html(f"<div style='font-size:11.5px;margin-top:-6px;'>{_src(live.get('india'), live.get('india_date'),'INDIRLTLT01STM', live.get('india_stale'))}</div>")
    with cset[1]:
        USY = st.number_input("US 10Y yield (%)", value=float(us_seed), step=0.01,
                              format="%.2f", key="us_yield")
        html(f"<div style='font-size:11.5px;margin-top:-6px;'>{_src(live.get('us'), live.get('us_date'),'DGS10', live.get('us_stale'))}</div>")

    if use_live and live.get("errors"):
        html(f"<div style='color:{AMBER};-webkit-text-fill-color:{AMBER};font-size:11.5px;margin-top:6px;'>"
             f"⚠ Live feed partially unavailable ({', '.join(live['errors'])}) — using reference figures where needed. "
             f"You can type today's value above.</div>")
    if use_live and live.get("india") is not None and live.get("india_date"):
        html(f"<div style='color:{MUTED};-webkit-text-fill-color:{MUTED};font-size:11px;margin-top:6px;'>"
             f"Note: the India 10Y feed (OECD) is monthly and can lag — override with today's G-Sec yield for a current read.</div>")

SPREAD_BPS = round((IND - USY) * 100)
IS_LIVE = bool(use_live and (
    (live.get("us") is not None and not live.get("us_stale")) or
    (live.get("india") is not None and not live.get("india_stale"))))

# =============================================================================
# TABS
# =============================================================================
tabs = st.tabs([
    "📌 Overview",
    "📖 Key Terms",
    "📈 Historical Spread",
    "⚖️ Breakeven Calculator",
    "🔎 Drivers & Implications",
    "🚨 Risk Triggers",
])

# -----------------------------------------------------------------------------
# TAB 1 — OVERVIEW
# -----------------------------------------------------------------------------
with tabs[0]:
    if IS_LIVE:
        badge = f"<span style='color:{GRN};-webkit-text-fill-color:{GRN};font-size:11px;'>● live</span>"
        tail = "live from FRED · adjust in ⚙️ Data settings above"
    else:
        badge = f"<span style='color:{AMBER};-webkit-text-fill-color:{AMBER};font-size:11px;'>reference</span>"
        tail = "open ⚙️ Data settings above and turn on <b>live yields</b> for real-time data"
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
            💡 The Single Most Important Idea</div>
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
            📚 Workbook Contents</div>{rows}
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
        💡 <b style="color:{GOLD};-webkit-text-fill-color:{GOLD};">Key Insight:</b>
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
    st.plotly_chart(plotly_theme(fig, height=460), width="stretch")

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
        st.plotly_chart(plotly_theme(fig, height=430, legend=False), width="stretch")

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
    st.dataframe(scen, width="stretch", hide_index=True)

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
    st.dataframe(drivers, width="stretch", hide_index=True)

    st.markdown(f"<div style='color:{GOLD};font-weight:700;font-size:16px;margin-top:10px;'>Part 2 · Impact on the Rupee (INR)</div>",
                unsafe_allow_html=True)
    inr = pd.DataFrame({
        "Aspect": ["Carry-Trade Cushion","Foreign Portfolio Flows","INR Volatility","Imported Inflation Risk"],
        "Before (wide spread)": ["400–600 bps buffer","Strong bond inflows","Lower","Manageable"],
        "After (narrow spread)": ["~220 bps buffer","Marginal / volatile","Higher","Elevated"],
        "Risk Level": ["HIGH","HIGH","MEDIUM","MEDIUM-HIGH"],
    })
    st.dataframe(inr, width="stretch", hide_index=True)

    html(f"""
    <div class="mp-card" style="border-color:rgba(220,53,69,.45);margin-top:10px;">
      <div style="color:{RED};-webkit-text-fill-color:{RED};font-weight:700;font-size:15px;margin-bottom:8px;">
        Part 3 · The RBI's Dilemma — Less Room to Cut Rates</div>
      <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;color:{TXT};
           -webkit-text-fill-color:{TXT};font-size:13px;font-weight:600;">
        <span style="background:{MID};padding:5px 10px;border-radius:6px;">RBI cuts rates</span> →
        <span style="background:{MID};padding:5px 10px;border-radius:6px;">Indian yields fall</span> →
        <span style="background:{MID};padding:5px 10px;border-radius:6px;">spread shrinks</span> →
        <span style="background:{MID};padding:5px 10px;border-radius:6px;">foreign money leaves</span> →
        <span style="background:{MID};padding:5px 10px;border-radius:6px;">rupee weakens</span> →
        <span style="background:{MID};padding:5px 10px;border-radius:6px;">imported inflation rises</span> →
        <span style="background:{RED};-webkit-text-fill-color:#fff;color:#fff;padding:5px 10px;border-radius:6px;">RBI cannot cut</span>
      </div>
      <div style="color:{MUTED};-webkit-text-fill-color:{MUTED};font-size:12.5px;margin-top:8px;">
        External constraints override domestic growth priorities. The narrower the spread, the tighter the trap.</div>
    </div>""")

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

    st.markdown(f"<div style='color:{GOLD};font-weight:700;font-size:16px;margin-top:6px;'>Part 2 · Live Monitoring Dashboard "
                f"<span style='color:{MUTED};font-size:12px;font-weight:400;'>(illustrative)</span></div>",
                unsafe_allow_html=True)
    us_stat = ("Critical", RED) if USY >= 4.75 else (("Watch", AMBER) if USY >= 4.55 else ("Safe", GRN))
    sp_stat = ("Critical", RED) if SPREAD_BPS <= 200 else (("Watch", AMBER) if SPREAD_BPS <= 240 else ("Safe", GRN))
    dash = [
        ("US 10Y Treasury", f"{USY:.2f}%", "4.75%", us_stat[0], us_stat[1], "Monitor Fed guidance"),
        ("Brent Crude ($/bbl)","78","90","Safe",GRN,"Track OPEC decisions"),
        ("VIX Index","16","25","Safe",GRN,"Global risk sentiment ok"),
        ("USD/INR","84.5","86","Watch",AMBER,"RBI intervention likely"),
        ("India–US Spread (bps)", f"{SPREAD_BPS}", "200", sp_stat[0], sp_stat[1], "Below-200 = red flag"),
        ("FII Bond Holdings ($bn)","32","25","Safe",GRN,"Watch weekly flows"),
    ]
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
              <div style="color:{LB};-webkit-text-fill-color:{LB};font-size:11.5px;margin-top:4px;">{act}</div>
            </div>""")

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
    st.dataframe(play, width="stretch", hide_index=True)

    html(f"""
    <div class="mp-card" style="border-color:rgba(255,215,0,.42);">
      <div style="color:{TXT};-webkit-text-fill-color:{TXT};font-size:14px;line-height:1.6;">
        🎯 <b style="color:{GOLD};-webkit-text-fill-color:{GOLD};">Key Takeaway:</b>
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
         font-weight:700;font-size:13px;text-decoration:none;">🌐 themountainpathacademy.com ↗</a>
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
