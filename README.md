# India–US 10Y Bond Yield Spread — Educational Streamlit App

**The Mountain Path Academy — World of Finance** · Prof. V. Ravichandran
🌐 https://themountainpathacademy.com

An interactive, classroom-ready explainer of why the India–US 10-year government bond
yield spread has compressed to a multi-decadal low (~220 bps) and what it means for the
rupee, the RBI, and India's economy. Built for MBA / CFA / FRM learners.

## Tabs
1. **Overview** — key metrics, one-minute summary, workbook contents
2. **Key Terms** — bond yield, spread, carry, duration, hedging cost, and more
3. **Historical Spread** — 20-year interactive chart (India & US yields + spread)
4. **Breakeven Calculator** — move the rupee slider and watch the return vs US Treasury update live
5. **Drivers & Implications** — why the spread shrank; impact on INR, the RBI's dilemma, the economy
6. **Risk Triggers** — the four triggers, a live-style monitoring dashboard, and a scenario playbook

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```
Then open the URL Streamlit prints (usually http://localhost:8501).

## Deploy free on Streamlit Community Cloud
1. Push this folder to a GitHub repo (e.g. `github.com/trichyravis/rbi-spread-app`).
2. Go to https://share.streamlit.io → **New app** → pick the repo, branch, and `app.py`.
3. Click **Deploy**. You'll get a public URL like
   `https://rbi-spread-app.streamlit.app`.
4. **Update the website link:** open `streamlit-projects.html`, find the card titled
   *"India–US 10Y Bond Yield Spread — RBI Rates Explainer"* (in the *Macro & Indian Banking
   Analytics* section), and replace the `href="https://github.com/trichyravis"` on its
   **Launch App ↗** button with your new `.streamlit.app` URL. Then `firebase deploy`.

## Live data
The **⚙️ Data settings** panel (top of the app) fetches current yields from FRED (no API key):
- **US 10Y** — `DGS10` (daily)
- **India 10Y** — `INDIRLTLT01STM` (OECD, monthly — can lag; the app flags a stale feed in amber)

Both feed into the KPIs, the breakeven calculator, and the risk dashboard. If the feed is
unavailable (offline, or a host not on your network's allowlist) the app falls back to reference
figures, and you can **type today's yields manually** in the same panel. Streamlit Community Cloud
can reach FRED out of the box.

## Notes
- Figures without a live feed are illustrative of the current regime — refresh against market data.
- Educational content only; not investment advice.
