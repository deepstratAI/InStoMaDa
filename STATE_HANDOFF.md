# FinDia Development State Hand-Off

## Current Phase: Phase 2 — Transformation Engine (`src/findia/transform/`)

### Completed Architecture (Phase 1 - Ingestion & Extraction)
1. **Market Data Engine (`market_data.py`):** `PriceExtractor` class fetching yfinance OHLCV data with `.NS`/`.BO` auto-formatting.
2. **Annual Fundamental Engine (`screener_annual.py`):** `ScreenerAnnualEngine` extracting multi-year P&L, Balance Sheet, Cash Flow, Ratios, and Shareholding from Screener.in.
3. **Quarterly Fundamental Engine (`screener_quarterly.py`):** `ScreenerQuarterlyEngine` extracting ~10-12 quarters of income statements and CAGR growth tables.
4. **Core Financial Vision Engine (`financial_statement_extractor.py`):** `VisionExtractor` using Gemini 2.5 Vision with structured 2D JSON schemas to parse `balance_sheet.png`, `income_statement.png`, `cash_flow.png`.
5. **Generic Vision Engine (`generic_vision_extractor.py`):** `GenericVisionExtractor` parsing arbitrary annual report images/notes into named Excel tabs.
6. **Local Index Engine (`index_data.py`):** `LocalIndexExtractor` that parses local NSE Excel files to extract benchmark Total Returns Index (TRI) and Close data, completely bypassing rate limits.
7. **Workspace Loader (`exporter.py`):** `DataExporter` writing multi-tab Excel workbooks to `data/pipeline_output/`.
8. **Package Facade (`src/findia/__init__.py`):** Unified top-level imports enabled (`from findia import PriceExtractor, VisionExtractor, ...`).
### Completed Architecture (Phase 2 - Transformation Engine - Partial)
9. **Single-Asset Analytics Engine (`stock.py`):** `StockAnalytics` class calculating Calendar CAGR, Annualized Volatility, Sharpe/Sortino ratios, dynamic Market Beta (OLS against TRI), and generating visual Underwater Curves.

### Key Design Principles & Guardrails
- **Environment Management:** Secrets loaded via `python-dotenv` from `.env`. Never commit keys.
- **Top-Level Package Imports:** All public modules are exposed through `src/findia/__init__.py`.
- **Data Standards:** Numeric values are cleaned (commas, `%`, `+` signs stripped) into strict numeric Pandas DataFrames.
- **Model Standard:** Multimodal OCR uses `models/gemini-2.5-flash` with dynamic fallback.

### Immediate Task for Next Session
Continue **Phase 2: The Transformation Engine** inside `src/findia/transform/`:
1. Architect and build `portfolio.py` (Multi-Asset Engine) to handle user-defined allocation weightings.
2. Implement portfolio-level quantitative logic including covariance matrices, portfolio expected returns, aggregated drawdowns, and diversification ratios.


2. The Master Re-Entry Prompt (Copy & Paste into New Session)
When opening a fresh chat window, initialize it with this text:

Role & Mission: You are acting as QuantNSE Mentor, an elite Quantitative Software Architect and Financial Data Engineer specializing in Indian Equity Markets (NSE/BSE).

Context & Repository State: We are co-developing FinDia (InStoMaDa), a production-grade Python package for Indian equity market data.

Phase 1 (Extraction & Ingestion) is 100% complete and fully verified.

Phase 2 (Transformation Engine) is starting now.

I have attached our repository's README.md, API_REFERENCE.md, and STATE_HANDOFF.md for full context on our file structure, top-level facade imports, design principles, and completed modules.

Goal for this session: We have successfully completed Phase 1 (Extraction) and the Single-Asset Analytics engine (`src/findia/transform/stock.py`) for Phase 2. Let's continue Phase 2 by architecting `src/findia/transform/portfolio.py` to handle multi-asset covariance, portfolio-level drawdowns, and weighted aggregation. Please review the context and provide the mathematical architecture and implementation strategy for the Portfolio engine!