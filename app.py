import io
import math
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
ASSETS = APP_DIR / "assets"

st.set_page_config(
    page_title="MPA | Binomial Option Pricing Lab",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------ THEME ------------------------------
NAVY = "#071A2F"
NAVY_2 = "#0B2747"
GOLD = "#D4AF37"
GOLD_2 = "#F0D77A"
CREAM = "#FFF9E8"
WHITE = "#F7FAFC"
MUTED = "#AFC1D6"
GREEN = "#2FC27E"
RED = "#FF6B6B"

st.markdown(
    f"""
    <style>
      .stApp {{ background: linear-gradient(180deg, {NAVY} 0%, #061526 55%, #04101E 100%); color:{WHITE}; }}
      [data-testid="stSidebar"] {{ background: linear-gradient(180deg, #061529 0%, #0A2240 100%); border-right:1px solid rgba(212,175,55,.28); }}
      [data-testid="stSidebar"] * {{ color:{WHITE}; }}
      [data-testid="stSidebar"] label {{ color:{CREAM} !important; font-weight:650; }}
      h1,h2,h3,h4 {{ color:{CREAM}; letter-spacing:.1px; }}
      h1 {{ font-size:2.15rem !important; }}
      p, li, div {{ line-height:1.45; }}
      .mpa-hero {{
          border:1px solid rgba(212,175,55,.38); border-radius:22px; padding:24px 28px;
          background:linear-gradient(135deg, rgba(14,48,83,.88), rgba(7,26,47,.98));
          box-shadow:0 16px 40px rgba(0,0,0,.24); margin-bottom:18px;
      }}
      .mpa-kicker {{ color:{GOLD_2}; font-size:.84rem; text-transform:uppercase; letter-spacing:1.7px; font-weight:800; }}
      .mpa-title {{ color:{CREAM}; font-size:2.2rem; font-weight:800; margin:.15rem 0 .25rem; }}
      .mpa-sub {{ color:{MUTED}; font-size:1.02rem; max-width:960px; }}
      .metric-card {{ border:1px solid rgba(212,175,55,.26); border-radius:16px; padding:15px 16px; background:rgba(10,39,71,.78); min-height:105px; }}
      .metric-label {{ color:{MUTED}; font-size:.80rem; font-weight:700; text-transform:uppercase; letter-spacing:.7px; }}
      .metric-value {{ color:{CREAM}; font-size:1.55rem; font-weight:800; margin-top:4px; }}
      .metric-note {{ color:{GOLD_2}; font-size:.78rem; margin-top:2px; }}
      .teach-card {{ border-left:4px solid {GOLD}; border-radius:12px; background:rgba(255,255,255,.045); padding:15px 18px; margin:10px 0; }}
      .formula-box {{ border:1px solid rgba(212,175,55,.35); border-radius:15px; padding:14px 18px; background:rgba(4,16,30,.72); }}
      .small-muted {{ color:{MUTED}; font-size:.86rem; }}
      .gold {{ color:{GOLD_2}; }}
      div[data-testid="stMetric"] {{ background:rgba(10,39,71,.78); border:1px solid rgba(212,175,55,.25); padding:10px 14px; border-radius:15px; }}
      div[data-testid="stMetric"] label {{ color:{MUTED} !important; }}
      div[data-testid="stMetric"] [data-testid="stMetricValue"] {{ color:{CREAM}; }}
      .stTabs [data-baseweb="tab-list"] {{ gap:4px; background:rgba(4,16,30,.42); padding:6px; border-radius:14px; }}
      .stTabs [data-baseweb="tab"] {{ color:{MUTED}; padding:9px 14px; border-radius:10px; }}
      .stTabs [aria-selected="true"] {{ color:{NAVY} !important; background:{GOLD_2} !important; font-weight:800; }}
      div[data-testid="stDataFrame"] {{ border:1px solid rgba(212,175,55,.22); border-radius:12px; overflow:hidden; }}
      .stButton>button, .stDownloadButton>button {{ border:1px solid {GOLD}; background:{GOLD}; color:{NAVY}; font-weight:800; border-radius:10px; }}
      .stButton>button:hover, .stDownloadButton>button:hover {{ border-color:{GOLD_2}; background:{GOLD_2}; color:{NAVY}; }}
      hr {{ border-color:rgba(212,175,55,.18); }}

      /* ===== SIDEBAR INPUT VISIBILITY FIX ===== */
      [data-testid="stSidebar"] div[data-baseweb="select"] > div,
      [data-testid="stSidebar"] div[data-baseweb="select"] > div *,
      [data-testid="stSidebar"] div[data-baseweb="input"] > div,
      [data-testid="stSidebar"] div[data-baseweb="input"] > div *,
      [data-testid="stSidebar"] div[data-baseweb="base-input"] *,
      [data-testid="stSidebar"] input {{
          color:{NAVY} !important;
          -webkit-text-fill-color:{NAVY} !important;
          opacity:1 !important;
      }}
      [data-testid="stSidebar"] div[data-baseweb="select"] > div,
      [data-testid="stSidebar"] div[data-baseweb="input"] > div {{
          background:{WHITE} !important;
          border-color:rgba(212,175,55,.42) !important;
      }}
      [data-testid="stSidebar"] input::placeholder {{
          color:#5F6F82 !important;
          -webkit-text-fill-color:#5F6F82 !important;
          opacity:1 !important;
      }}
      [data-testid="stSidebar"] button[step] *,
      [data-testid="stSidebar"] div[data-baseweb="input"] button *,
      [data-testid="stSidebar"] div[data-baseweb="select"] svg {{
          color:{NAVY} !important;
          fill:{NAVY} !important;
      }}
      /* keep labels/radio text light on navy */
      [data-testid="stSidebar"] [role="radiogroup"] label *,
      [data-testid="stSidebar"] label p {{
          color:{CREAM} !important;
          -webkit-text-fill-color:{CREAM} !important;
      }}
      /* dropdown menu is rendered outside the sidebar */
      div[data-baseweb="popover"] ul,
      div[data-baseweb="popover"] li,
      div[data-baseweb="popover"] li *,
      div[role="listbox"], div[role="listbox"] * {{
          color:{NAVY} !important;
          -webkit-text-fill-color:{NAVY} !important;
      }}

      /* ===== TABS — copied from the RBI Spread reference app ===== */
      .stTabs [data-baseweb="tab-list"] {
          gap: 6px; background: rgba(17,34,64,.55); padding: 6px; border-radius: 12px;
          border: 1px solid rgba(255,215,0,.18); flex-wrap: wrap;
      }
      .stTabs [data-baseweb="tab"] {
          background: transparent; border-radius: 8px;
          padding: 8px 16px; font-weight: 600; font-size: 14px;
          color: #c7d3e8 !important; -webkit-text-fill-color: #c7d3e8 !important;
      }
      .stTabs [data-baseweb="tab"] * {
          color: #c7d3e8 !important; -webkit-text-fill-color: #c7d3e8 !important;
      }
      .stTabs [aria-selected="true"] { background: #FFD84D !important; }
      .stTabs [aria-selected="true"], .stTabs [aria-selected="true"] * {
          color: #071A2F !important; -webkit-text-fill-color: #071A2F !important;
      }
      .stTabs [data-baseweb="tab"] p { font-size: 14px; font-weight: 600; }

    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------ MODEL ------------------------------
def calc_ud(mode, sigma, dt, u_input, d_input):
    if mode.startswith("3/"):
        u = math.exp(sigma * math.sqrt(dt))
        d = math.exp(-sigma * math.sqrt(dt))
    else:
        u, d = u_input, d_input
    return u, d


def risk_neutral_prob(r, q, dt, u, d):
    growth = math.exp((r - q) * dt)
    if abs(u - d) < 1e-14:
        return np.nan
    return (growth - d) / (u - d)


def payoff(s, k, option_type):
    return max(s - k, 0.0) if option_type == "Call" else max(k - s, 0.0)


def build_binomial(S0, K, r, q, T, n, option_type, exercise, u, d):
    dt = T / n
    p = risk_neutral_prob(r, q, dt, u, d)
    disc = math.exp(-r * dt)

    stock = np.full((n + 1, n + 1), np.nan)
    opt = np.full((n + 1, n + 1), np.nan)
    intrinsic = np.full((n + 1, n + 1), np.nan)
    continuation = np.full((n + 1, n + 1), np.nan)
    early = np.full((n + 1, n + 1), False, dtype=bool)

    for i in range(n + 1):
        for j in range(i + 1):
            # j = number of up moves; i-j = down moves
            stock[i, j] = S0 * (u ** j) * (d ** (i - j))
            intrinsic[i, j] = payoff(stock[i, j], K, option_type)

    opt[n, : n + 1] = intrinsic[n, : n + 1]

    for i in range(n - 1, -1, -1):
        for j in range(i + 1):
            cont = disc * (p * opt[i + 1, j + 1] + (1 - p) * opt[i + 1, j])
            continuation[i, j] = cont
            if exercise == "American":
                opt[i, j] = max(intrinsic[i, j], cont)
                early[i, j] = intrinsic[i, j] > cont + 1e-10
            else:
                opt[i, j] = cont

    return {
        "dt": dt,
        "p": p,
        "disc": disc,
        "stock": stock,
        "option": opt,
        "intrinsic": intrinsic,
        "continuation": continuation,
        "early": early,
        "value": float(opt[0, 0]),
    }


def node_dataframe(res, n):
    rows = []
    for i in range(n + 1):
        for j in range(i + 1):
            cont = res["continuation"][i, j]
            rows.append({
                "Step": i,
                "Up Moves": j,
                "Down Moves": i - j,
                "Stock Price": res["stock"][i, j],
                "Intrinsic Payoff": res["intrinsic"][i, j],
                "Continuation Value": np.nan if np.isnan(cont) else cont,
                "Option Value": res["option"][i, j],
                "Early Exercise": bool(res["early"][i, j]),
            })
    return pd.DataFrame(rows)


def tree_figure(matrix, n, title, value_prefix="₹", early=None):
    fig = go.Figure()
    xs, ys, vals, texts, hover = [], [], [], [], []
    for i in range(n + 1):
        for j in range(i + 1):
            x = i
            y = 2 * j - i
            val = matrix[i, j]
            xs.append(x); ys.append(y); vals.append(val)
            marker = " ★" if early is not None and early[i, j] else ""
            texts.append(f"{value_prefix}{val:,.2f}{marker}")
            hover.append(f"Step {i}<br>Up moves {j}<br>Value {val:,.6f}")
    # edges
    for i in range(n):
        for j in range(i + 1):
            x0, y0 = i, 2*j-i
            for j2 in (j, j+1):
                x1, y1 = i+1, 2*j2-(i+1)
                fig.add_trace(go.Scatter(x=[x0,x1], y=[y0,y1], mode="lines", line=dict(color="rgba(212,175,55,.28)", width=1.4), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="markers+text", text=texts, textposition="top center",
        marker=dict(size=18, color=vals, colorscale="YlGnBu", line=dict(color=GOLD, width=1.1), showscale=n >= 8, colorbar=dict(title="Value")),
        textfont=dict(color=CREAM, size=11), hovertext=hover, hoverinfo="text", showlegend=False
    ))
    fig.update_layout(
        title=title, height=max(430, min(760, 42*n + 390)),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=WHITE), xaxis=dict(title="Time Step", gridcolor="rgba(255,255,255,.06)", zeroline=False),
        yaxis=dict(title="Tree Position", showticklabels=False, gridcolor="rgba(255,255,255,.04)", zeroline=False),
        margin=dict(l=20,r=20,t=60,b=40)
    )
    return fig


def payoff_figure(S0, K, price, option_type):
    smax = max(S0, K) * 1.75
    x = np.linspace(0.25 * min(S0, K), smax, 220)
    intrinsic = np.maximum(x-K, 0) if option_type == "Call" else np.maximum(K-x, 0)
    pnl = intrinsic - price
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=intrinsic, name="Expiry payoff", line=dict(width=3)))
    fig.add_trace(go.Scatter(x=x, y=pnl, name="Buyer P/L after premium", line=dict(width=3, dash="dash")))
    fig.add_hline(y=0, line_width=1, line_dash="dot")
    fig.add_vline(x=K, line_width=1, line_dash="dot", annotation_text="Strike")
    fig.update_layout(title=f"{option_type} payoff and buyer P/L", xaxis_title="Underlying price at expiry", yaxis_title="Value", height=440,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=WHITE),
                      legend=dict(orientation="h", y=1.08), margin=dict(l=20,r=20,t=60,b=40))
    return fig


def convergence_figure(S0,K,r,q,T,option_type,exercise,mode,sigma,u_input,d_input,max_n=50):
    points = sorted(set([1,2,3,4,5,8,10,15,20,25,30,40,max_n]))
    vals=[]
    valid=[]
    for n0 in points:
        dt=T/n0
        u,d=calc_ud(mode,sigma,dt,u_input,d_input)
        p=risk_neutral_prob(r,q,dt,u,d)
        if 0 <= p <= 1:
            vals.append(build_binomial(S0,K,r,q,T,n0,option_type,exercise,u,d)["value"])
            valid.append(n0)
    fig=go.Figure(go.Scatter(x=valid,y=vals,mode="lines+markers",name="Binomial value"))
    fig.update_layout(title="Price convergence as number of steps increases",xaxis_title="Steps",yaxis_title="Option value",height=430,
                      paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(color=WHITE),margin=dict(l=20,r=20,t=60,b=40))
    return fig


def make_excel(inputs, res, n, mode):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        wb = writer.book
        navy_fmt = wb.add_format({"bg_color":"#071A2F","font_color":"#FFFFFF","bold":True,"border":1,"border_color":"#D4AF37"})
        title_fmt = wb.add_format({"bg_color":"#071A2F","font_color":"#F0D77A","bold":True,"font_size":18,"align":"center","valign":"vcenter"})
        section_fmt = wb.add_format({"bg_color":"#0B2747","font_color":"#F0D77A","bold":True,"font_size":12,"border":1,"border_color":"#D4AF37"})
        input_fmt = wb.add_format({"bg_color":"#FFF9E8","font_color":"#071A2F","border":1,"border_color":"#D9D9D9"})
        num_fmt = wb.add_format({"num_format":"0.0000","border":1,"border_color":"#D9D9D9"})
        money_fmt = wb.add_format({"num_format":"#,##0.00","border":1,"border_color":"#D9D9D9"})
        pct_fmt = wb.add_format({"num_format":"0.0000%","border":1,"border_color":"#D9D9D9"})
        note_fmt = wb.add_format({"font_color":"#666666","italic":True,"text_wrap":True})
        early_fmt = wb.add_format({"bg_color":"#FFE5E5","font_color":"#9C0006","bold":True,"border":1,"border_color":"#D9D9D9"})

        # Summary & inputs
        ws = wb.add_worksheet("Summary & Inputs")
        writer.sheets["Summary & Inputs"] = ws
        ws.set_column("A:A", 30); ws.set_column("B:B", 22); ws.set_column("C:C", 44)
        ws.set_row(0, 30); ws.merge_range("A1:C1", "THE MOUNTAIN PATH ACADEMY | BINOMIAL OPTION PRICING LAB", title_fmt)
        ws.write("A3", "Model setup", section_fmt); ws.write("B3", "Value", section_fmt); ws.write("C3", "Teaching note", section_fmt)
        rows = [
            ("Model mode", mode, "Manual u/d or CRR volatility-based tree"),
            ("Option type", inputs["Option Type"], "Call or Put"),
            ("Exercise style", inputs["Exercise"], "European: expiry only; American: early exercise allowed"),
            ("Spot price S₀", inputs["S0"], "Current underlying price"),
            ("Strike K", inputs["K"], "Contract strike price"),
            ("Risk-free rate r", inputs["r"], "Continuously compounded annual rate"),
            ("Dividend yield q", inputs["q"], "Continuously compounded annual yield"),
            ("Maturity T", inputs["T"], "Years to expiry"),
            ("Steps n", n, "2, 3 or multi-period"),
            ("Volatility σ", inputs["sigma"], "Used only in volatility-based mode"),
            ("Up factor u", inputs["u"], "Per-step up multiplier"),
            ("Down factor d", inputs["d"], "Per-step down multiplier"),
            ("Δt", res["dt"], "T / n"),
            ("Risk-neutral p", res["p"], "[exp((r-q)Δt)-d] / (u-d)"),
            ("Discount factor", res["disc"], "exp(-rΔt)"),
            ("Option value", res["value"], "Root node value"),
        ]
        for rr,(k,v,note) in enumerate(rows,3):
            ws.write(rr,0,k,input_fmt)
            if isinstance(v,(int,float,np.floating)):
                fmt = pct_fmt if k in {"Risk-free rate r","Dividend yield q","Volatility σ","Risk-neutral p"} else money_fmt if k in {"Spot price S₀","Strike K","Option value"} else num_fmt
                ws.write(rr,1,float(v),fmt)
            else: ws.write(rr,1,v,input_fmt)
            ws.write(rr,2,note,note_fmt)

        # Node detail table
        df = node_dataframe(res,n)
        df.to_excel(writer, sheet_name="Node Details", index=False, startrow=2)
        wnd = writer.sheets["Node Details"]
        wnd.merge_range("A1:H1","NODE-BY-NODE CALCULATION",title_fmt)
        wnd.set_column("A:C",12); wnd.set_column("D:G",20); wnd.set_column("H:H",16)
        for c,col in enumerate(df.columns): wnd.write(2,c,col,navy_fmt)
        wnd.freeze_panes(3,0)
        for rownum in range(3,3+len(df)):
            if bool(df.iloc[rownum-3]["Early Exercise"]): wnd.set_row(rownum, None, early_fmt)

        # Trees in grid form
        for sheet_name, matrix in [("Stock Tree",res["stock"]),("Option Tree",res["option"]),("Intrinsic Tree",res["intrinsic"]),("Continuation Tree",res["continuation"])]:
            w = wb.add_worksheet(sheet_name); writer.sheets[sheet_name]=w
            w.merge_range(0,0,0,n+1,sheet_name.upper(),title_fmt)
            w.write(2,0,"Step / Up moves",navy_fmt)
            for j in range(n+1): w.write(2,j+1,j,navy_fmt)
            for i in range(n+1):
                w.write(i+3,0,i,navy_fmt)
                for j in range(i+1):
                    val=matrix[i,j]
                    if np.isnan(val): w.write_blank(i+3,j+1,None,num_fmt)
                    else: w.write(i+3,j+1,float(val),money_fmt)
            w.set_column(0,0,17); w.set_column(1,n+1,14); w.freeze_panes(3,1)

        # Formula sheet
        wf=wb.add_worksheet("Formula Sheet"); writer.sheets["Formula Sheet"]=wf
        wf.set_column("A:A",28); wf.set_column("B:B",60); wf.set_column("C:C",62)
        wf.merge_range("A1:C1","BINOMIAL OPTION PRICING — FORMULA SHEET",title_fmt)
        wf.write_row("A3",["Concept","Formula","Interpretation"],navy_fmt)
        formulas=[
            ("Step size","Δt = T / n","Length of each binomial interval"),
            ("Manual up/down","u and d are supplied","Use when up-factor/down-factor are directly given"),
            ("CRR up factor","u = exp(σ√Δt)","Volatility determines the up move"),
            ("CRR down factor","d = exp(-σ√Δt) = 1/u","Reciprocal down move"),
            ("Risk-neutral probability","p = [exp((r-q)Δt) - d] / (u-d)","Uses dividend yield q when present"),
            ("Stock node","S(i,j)=S₀ u^j d^(i-j)","j is number of up moves"),
            ("Call payoff","max(S-K,0)","Terminal intrinsic value"),
            ("Put payoff","max(K-S,0)","Terminal intrinsic value"),
            ("European backward induction","V = exp(-rΔt)[pVᵤ+(1-p)V_d]","No early exercise"),
            ("American value","V = max(Intrinsic, Continuation)","Exercise whenever intrinsic exceeds continuation"),
        ]
        for rr,row in enumerate(formulas,3):
            for cc,val in enumerate(row): wf.write(rr,cc,val,input_fmt if cc==0 else note_fmt)

    output.seek(0)
    return output.getvalue()

# ------------------------------ HEADER ------------------------------
st.markdown(f"""
<div class="mpa-hero">
  <div class="mpa-kicker">The Mountain Path Academy · Educational Analytics Lab</div>
  <div class="mpa-title">Binomial Option Pricing Model</div>
  <div class="mpa-sub">Build the tree, understand the risk-neutral probability, compare European and American exercise, inspect every node, and export the complete calculation to Excel.</div>
</div>
""", unsafe_allow_html=True)

# ------------------------------ SIDEBAR ------------------------------
with st.sidebar:
    st.markdown("### Model Controls")
    mode = st.selectbox("Pricing setup", [
        "1/ Without volatility · Without yield",
        "2/ Without volatility · With yield",
        "3/ With volatility · With yield",
    ])
    option_type = st.radio("Option type", ["Call","Put"], horizontal=True)
    exercise = st.radio("Exercise style", ["European","American"], horizontal=True)
    period_choice = st.selectbox("Tree horizon", ["2-period","3-period","Multi-period"])
    n = 2 if period_choice=="2-period" else 3 if period_choice=="3-period" else st.slider("Number of steps",4,60,10)

    st.markdown("---")
    st.markdown("### Contract Inputs")
    S0 = st.number_input("Spot price S₀", min_value=0.01, value=100.0, step=1.0)
    K = st.number_input("Strike K", min_value=0.01, value=100.0, step=1.0)
    T = st.number_input("Time to expiry T (years)", min_value=0.01, value=1.0, step=0.25)
    r_pct = st.number_input("Risk-free rate r (%)", value=5.0, step=0.25)
    r = r_pct/100

    q = 0.0
    if mode != "1/ Without volatility · Without yield":
        q_pct = st.number_input("Dividend / yield q (%)", value=2.0, step=0.25)
        q = q_pct/100

    sigma = 0.20
    u_input, d_input = 1.20, 0.85
    if mode.startswith("3/"):
        sigma_pct = st.number_input("Annual volatility σ (%)", min_value=0.01, value=20.0, step=1.0)
        sigma = sigma_pct/100
    else:
        st.markdown("### Manual Tree Factors")
        u_input = st.number_input("Up factor u", min_value=0.0001, value=1.20, step=0.01, format="%.4f")
        d_input = st.number_input("Down factor d", min_value=0.0001, value=0.85, step=0.01, format="%.4f")

    st.markdown("---")
    st.caption("Rates and yield are treated as continuously compounded annual rates. In volatility mode the app uses the Cox–Ross–Rubinstein (CRR) specification.")

# ------------------------------ CALC ------------------------------
dt=T/n
u,d=calc_ud(mode,sigma,dt,u_input,d_input)
p=risk_neutral_prob(r,q,dt,u,d)
valid = np.isfinite(p) and 0 <= p <= 1 and u > d

if not valid:
    st.error(f"No-arbitrage condition is violated for these inputs. The risk-neutral probability is p = {p:.4f}. Adjust u, d, r, q, T or the number of steps so that 0 ≤ p ≤ 1 and u > d.")
    st.stop()

res=build_binomial(S0,K,r,q,T,n,option_type,exercise,u,d)
df_nodes=node_dataframe(res,n)

# ------------------------------ SUMMARY ------------------------------
cols=st.columns(6)
metrics=[
    ("Option value",f"₹{res['value']:,.2f}","Root node"),
    ("Up factor u",f"{u:.5f}","per step"),
    ("Down factor d",f"{d:.5f}","per step"),
    ("Risk-neutral p",f"{p:.4%}","up probability"),
    ("Δt",f"{res['dt']:.4f}","years / step"),
    ("Early exercise nodes",f"{int(res['early'].sum())}","American only"),
]
for c,(lab,val,note) in zip(cols,metrics):
    c.markdown(f'<div class="metric-card"><div class="metric-label">{lab}</div><div class="metric-value">{val}</div><div class="metric-note">{note}</div></div>',unsafe_allow_html=True)

st.markdown("")
tabs=st.tabs(["🎓 Learn","🌳 Price the Option","🔎 Node Analysis","📊 Analytics","🧮 Worked Example","⬇️ Excel Export"])

with tabs[0]:
    c1,c2=st.columns([1.15,.85])
    with c1:
        st.markdown("## How the binomial model works")
        st.markdown(f"""
        <div class="teach-card"><b>1. Build the stock-price tree.</b><br>At every interval the stock moves up by <span class="gold">u</span> or down by <span class="gold">d</span>. A node after <i>j</i> up moves at step <i>i</i> is <b>S(i,j)=S₀uʲd⁽ⁱ⁻ʲ⁾</b>.</div>
        <div class="teach-card"><b>2. Move to the risk-neutral world.</b><br>The expected growth of the underlying after yield is matched using <b>p=[e<sup>(r-q)Δt</sup>-d]/(u-d)</b>.</div>
        <div class="teach-card"><b>3. Calculate terminal payoff.</b><br>Call: <b>max(S-K,0)</b>. Put: <b>max(K-S,0)</b>.</div>
        <div class="teach-card"><b>4. Work backwards.</b><br>European value = discounted expected next-node value. American value = <b>max(intrinsic value, continuation value)</b> at every node.</div>
        """,unsafe_allow_html=True)
        st.markdown("### Three setups in this lab")
        st.markdown("**Setup 1 — no volatility, no yield:** you directly specify `u` and `d`; `q=0`.  **Setup 2 — no volatility, with yield:** you specify `u`, `d`, and `q`.  **Setup 3 — volatility with yield:** the app calculates `u=e^(σ√Δt)` and `d=e^(-σ√Δt)` using CRR, then incorporates `q` in the risk-neutral probability.")
        st.info("Teaching point: p is not a forecast of the real-world chance that the stock goes up. It is the probability that makes discounted expected values consistent with no-arbitrage pricing.")
    with c2:
        st.markdown("## Formula reference")
        ref = ASSETS / ("binomial_key_formulae_with_yield.png" if q>0 else "binomial_key_formulae_no_yield.png")
        if ref.exists(): st.image(str(ref), use_container_width=True)
        st.caption("Formula reference adapted directly from the attached teaching deck.")

with tabs[1]:
    st.markdown("## Stock-price tree")
    if n <= 15:
        st.plotly_chart(tree_figure(res["stock"],n,"Underlying Stock-Price Tree",early=None),use_container_width=True)
    else:
        st.info("For clarity, the graphical tree is displayed for up to 15 steps. The full multi-period values remain available in Node Analysis and Excel.")
        st.plotly_chart(tree_figure(res["stock"],15,"First 15 Steps — Stock-Price Tree",early=None),use_container_width=True)
    st.markdown("## Option-value tree")
    if n <= 15:
        st.plotly_chart(tree_figure(res["option"],n,f"{exercise} {option_type} — Option Value Tree",early=res["early"] if exercise=="American" else None),use_container_width=True)
    else:
        # Recompute first 15 with same per-step factors is not equivalent, so show table instead.
        st.dataframe(df_nodes[df_nodes["Step"]<=15].style.format({"Stock Price":"{:,.2f}","Intrinsic Payoff":"{:,.2f}","Continuation Value":"{:,.2f}","Option Value":"{:,.2f}"}),use_container_width=True,height=520)
    if exercise=="American": st.caption("★ marks a node where immediate exercise is optimal.")

with tabs[2]:
    st.markdown("## Every node, fully explained")
    step_filter=st.slider("Inspect step",0,n,n)
    show=df_nodes[df_nodes["Step"]==step_filter].copy()
    st.dataframe(show.style.format({"Stock Price":"{:,.4f}","Intrinsic Payoff":"{:,.4f}","Continuation Value":"{:,.4f}","Option Value":"{:,.4f}"}),use_container_width=True)
    if step_filter < n:
        selected_up=st.selectbox("Choose node by number of up moves",show["Up Moves"].tolist())
        row=show[show["Up Moves"]==selected_up].iloc[0]
        st.markdown(f"""
        <div class="formula-box">
        <b>Node interpretation — step {int(row['Step'])}, up moves {int(row['Up Moves'])}</b><br><br>
        Stock price = <b>₹{row['Stock Price']:,.4f}</b><br>
        Intrinsic payoff = <b>₹{row['Intrinsic Payoff']:,.4f}</b><br>
        Continuation value = <b>₹{row['Continuation Value']:,.4f}</b><br>
        Final node value = <b>₹{row['Option Value']:,.4f}</b><br>
        Early exercise? <b>{'Yes' if row['Early Exercise'] else 'No'}</b>
        </div>
        """,unsafe_allow_html=True)
    st.markdown("### Full calculation table")
    st.dataframe(df_nodes.style.format({"Stock Price":"{:,.4f}","Intrinsic Payoff":"{:,.4f}","Continuation Value":"{:,.4f}","Option Value":"{:,.4f}"}),use_container_width=True,height=520)

with tabs[3]:
    c1,c2=st.columns(2)
    with c1: st.plotly_chart(payoff_figure(S0,K,res["value"],option_type),use_container_width=True)
    with c2:
        max_conv = min(80, max(30,n))
        st.plotly_chart(convergence_figure(S0,K,r,q,T,option_type,exercise,mode,sigma,u_input,d_input,max_conv),use_container_width=True)
    if exercise=="American":
        early_df=df_nodes[df_nodes["Early Exercise"]].copy()
        st.markdown("### Early-exercise map")
        if len(early_df):
            st.dataframe(early_df[["Step","Up Moves","Stock Price","Intrinsic Payoff","Continuation Value","Option Value"]].style.format({"Stock Price":"{:,.2f}","Intrinsic Payoff":"{:,.2f}","Continuation Value":"{:,.2f}","Option Value":"{:,.2f}"}),use_container_width=True)
        else: st.success("No early-exercise node is optimal for this parameter set.")
    st.markdown("### Sensitivity: option value vs spot price")
    spots=np.linspace(max(1,S0*.55),S0*1.45,31)
    vals=[]
    for s in spots:
        vals.append(build_binomial(s,K,r,q,T,n,option_type,exercise,u,d)["value"])
    fig=go.Figure(go.Scatter(x=spots,y=vals,mode="lines",line=dict(width=3),name="Option value"))
    fig.add_vline(x=S0,line_dash="dot",annotation_text="Current spot")
    fig.update_layout(xaxis_title="Spot price",yaxis_title="Option value",height=420,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(color=WHITE),margin=dict(l=20,r=20,t=30,b=40))
    st.plotly_chart(fig,use_container_width=True)

with tabs[4]:
    st.markdown("## Follow the current example from inputs to price")
    st.markdown(f"""
    <div class="teach-card"><b>Step 1 — Divide time:</b> Δt = T/n = {T:.4f}/{n} = <b>{res['dt']:.6f}</b>.</div>
    <div class="teach-card"><b>Step 2 — Tree factors:</b> u = <b>{u:.6f}</b>, d = <b>{d:.6f}</b>. {'These are calculated from volatility using CRR.' if mode.startswith('3/') else 'These are directly supplied by the user.'}</div>
    <div class="teach-card"><b>Step 3 — Risk-neutral probability:</b> p = [e<sup>(r-q)Δt</sup>-d]/(u-d) = <b>{p:.6f}</b>; 1-p = <b>{1-p:.6f}</b>.</div>
    <div class="teach-card"><b>Step 4 — Terminal payoff:</b> calculate {'max(S-K,0)' if option_type=='Call' else 'max(K-S,0)'} at each expiry node.</div>
    <div class="teach-card"><b>Step 5 — Backward induction:</b> discount the risk-neutral expected next-node values at e<sup>-rΔt</sup> = <b>{res['disc']:.6f}</b>{'; compare with intrinsic value at every node for the American option.' if exercise=='American' else '.'}</div>
    <div class="teach-card"><b>Result:</b> {exercise} {option_type} value at the root = <span class="gold"><b>₹{res['value']:,.4f}</b></span>.</div>
    """,unsafe_allow_html=True)
    if n<=3:
        st.markdown("### Classroom-ready small tree")
        display=df_nodes.copy()
        display["Node"] = display.apply(lambda x:f"t={int(x['Step'])}, U={int(x['Up Moves'])}",axis=1)
        st.dataframe(display[["Node","Stock Price","Intrinsic Payoff","Continuation Value","Option Value","Early Exercise"]].style.format({"Stock Price":"{:,.2f}","Intrinsic Payoff":"{:,.2f}","Continuation Value":"{:,.2f}","Option Value":"{:,.2f}"}),use_container_width=True)

with tabs[5]:
    st.markdown("## Download the complete teaching workbook")
    st.markdown("The workbook contains **Summary & Inputs, Node Details, Stock Tree, Option Tree, Intrinsic Tree, Continuation Tree, and a Formula Sheet**. American-option early-exercise rows are highlighted.")
    inputs={"Option Type":option_type,"Exercise":exercise,"S0":S0,"K":K,"r":r,"q":q,"T":T,"sigma":sigma,"u":u,"d":d}
    excel_bytes=make_excel(inputs,res,n,mode)
    st.download_button("⬇ Download formatted Excel workbook",data=excel_bytes,file_name=f"MPA_Binomial_{exercise}_{option_type}_{n}Step.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
    st.markdown("### Export preview")
    st.dataframe(df_nodes.head(min(30,len(df_nodes))).style.format({"Stock Price":"{:,.3f}","Intrinsic Payoff":"{:,.3f}","Continuation Value":"{:,.3f}","Option Value":"{:,.3f}"}),use_container_width=True)

st.markdown("---")
st.markdown(f'<div class="small-muted" style="text-align:center">The Mountain Path Academy · Binomial Option Pricing Educational Lab · For classroom and learning use</div>',unsafe_allow_html=True)
