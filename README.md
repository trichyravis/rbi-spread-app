# MPA Binomial Option Pricing Lab

An educational Streamlit application for teaching and demonstrating the Binomial Option Pricing Model.

## Features
- Manual up/down factor model without yield
- Manual up/down factor model with yield
- CRR volatility-based model with yield
- European and American calls/puts
- 2-period, 3-period and multi-period trees
- Interactive stock and option trees
- Node-level intrinsic vs continuation analysis
- Early exercise detection for American options
- Payoff, convergence and spot-sensitivity charts
- Downloadable formatted Excel workbook
- Formula reference images derived from the supplied MPA teaching deck

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud
Push this folder to GitHub and choose `app.py` as the main file when deploying in Streamlit Community Cloud.
