# FinDia (InStoMaDa)

![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-active-success)

**FinDia** is a Python package designed for extracting, transforming, and analyzing Indian equity market data (NSE/BSE). 

Built for quantitative analysts and financial engineers, FinDia provides a unified, resilient pipeline that bridges the gap between price action and  fundamental data—eliminating the headache of managing raw web scrapers, rate limits, and broken Indian accounting formats.

## ✨ Why FinDia?

* **Unified API:** Pull OHLCV price action, multi-year annual statements, quarterly earnings, and digitize image-based financial statements through a single, standardized interface.
* **Multimodal Vision OCR:** Convert scanned annual report tables, footnotes, and financial statements directly into structured Pandas DataFrames using Gemini 2.5 Vision with enforced JSON schemas.
* **Indian Market Optimized:** Automatically handles NSE/BSE ticker formatting (`.NS` suffixes), standalone vs. consolidated reporting, and Indian accounting terminology.
* **Ready for Quant Math:** Strips commas, percentages, and formatting artifacts, returning numeric DataFrames ready for financial modeling.
* **Anti-Scraping Resilience:** Bypass strict exchange rate-limits by natively ingesting local NSE historical Excel files (specifically extracting Date, Close, and Total Returns Index) for benchmark indices.

---

## 🚀 Quick Start

Extract a complete quantitative profile for a company—including historical price action, annual financial statements, and quarterly earnings—in just a few lines of code.

```python
from findia import PriceExtractor, ScreenerAnnualEngine, ScreenerQuarterlyEngine, DataExporter

# 1. Initialize Engines
price_engine = PriceExtractor()
annual_engine = ScreenerAnnualEngine()
exporter = DataExporter(output_dir="data/exports")

ticker = "RELIANCE"

# 2. Extract Price Action
df_price = price_engine.fetch_ohlcv(tickers=ticker, interval="1d", period="2y")
exporter.to_excel(df_price, filename=f"{ticker}_Price_Action.xlsx")

# 3. Extract & Export Clean Annual Fundamentals (P&L, Balance Sheet, Cash Flow)
annual_engine.export_to_excel(ticker=ticker, reporting_level="consolidated", output_dir="data/exports")
```

### 📸 Multimodal Vision Extraction (Annual Reports & Scanned Files)

Digitize scanned PDF tables, annual report footnotes, or financial statement images using Gemini 2.5 Vision.

```python
from findia import VisionExtractor, GenericVisionExtractor

# 1. Standard Financial Triad (Balance Sheet, Income Statement, Cash Flow)
statement_engine = VisionExtractor()
statement_data = statement_engine.process_input_directory(input_dir="data/input")

# 2. Generic Annual Report Notes & Footnotes
generic_engine = GenericVisionExtractor()
notes_data = generic_engine.process_directory(input_dir="data/input/annual_report_notes")
```

📚 API Reference & Documentation
To keep this landing page clean, all technical details regarding classes, methods, accepted arguments (like reporting_level, interval, period), and expected return schemas are documented in our dedicated API dictionary.

👉 [View the Full API Reference](API_REFERENCE.md)

### 📉 Local Market Index Extraction (Total Returns)

Bypass NSE anti-scraping measures by parsing locally downloaded historical Excel files to extract accurate Total Returns Index (TRI) data for benchmark comparison.

```python
from findia import LocalIndexExtractor
import pandas as pd

index_engine = LocalIndexExtractor(data_dir="data/nse_data")

# Extract 5 years of monthly resampled Total Return data
df_indices = index_engine.fetch_historical_data(
    tickers=["NIFTY_MIDCAP_150"], 
    interval="1mo", 
    period="5y"
)


```

## 🧮 Quantitative Transformation & Risk Analytics (Phase 2)
Transform raw price action and fundamental data into institutional-grade risk metrics. Calculates Calendar CAGR, Annualized Volatility, Sharpe/Sortino ratios, and runs dynamic OLS regression for Market Beta against a Total Returns Index (TRI). Automatically generates visual Underwater Curves.

```python
from findia.transform.stock import StockAnalytics

# Initialize the transformation engine
analytics_engine = StockAnalytics()

# Generate a unified multi-tab Excel report and Drawdown .png chart
analytics_engine.generate_pipeline_report(
    ticker="RELIANCE",
    index_ticker="NIFTY_50",    # Mapped to local TRI data
    period="2y",                # Lookback window
    interval="1wk",             # Dynamic alignment frequency for Beta
    output_dir="data/pipeline_output"
)
```

## 📁 Project Structure

```text
InStoMaDa/
├── src/findia/                # Core Package Source
│   ├── __init__.py            # Top-level unified imports
│   ├── extractors/            # Data extraction subpackage
│   │   ├── market_data.py                   # Price Action Engine (yfinance)
│   │   ├── index_data.py                    # Local NSE Index Engine (TRI Focus)
│   │   ├── screener_annual.py               # Annual Statements Engine (Screener.in)
│   │   ├── screener_quarterly.py            # Quarterly Results & CAGR Engine (Screener.in)
│   │   ├── financial_statement_extractor.py # Core Financial Statements Vision Engine
│   │   └── generic_vision_extractor.py      # Generic AR Table & Notes Vision Engine
│   ├── loaders/               # Workspace & Export Handlers
│   │   └── exporter.py        # Excel & workspace writer
│   ├── models/                # Schema definitions & Pydantic models
│   └── transform/             # Quantitative analysis engine (Phase 2)
│       ├── __init__.py        
│       └── stock.py           # Asset-level Risk, Beta, and Drawdown engine
├── data/                      # Local output workspace for exported reports
│   ├── input/                 # Staging folder for image ingestion
│   ├── nse_data/              # Staging folder for local NSE index Excel files
│   └── pipeline_output/       # Output folder for generated workbooks
├── tests/                     # Unit & integration test suite
├── .env                       # Local secrets (GEMINI_API_KEY)
├── API_REFERENCE.md           # Full technical API specifications
├── main.py                    # Root execution driver script
├── pyproject.toml             # Package metadata & dependencies
└── README.md                  # Landing page documentation