# FinDia API Reference (Phase 1: Extraction & Loading)

This document serves as the technical contract for the FinDia extraction engines. It details the available classes, methods, arguments, and expected return types for Indian equity data pipelines.

---

## 1. Market Data Extraction (`yfinance` Engine)

**Module:** `findia.extractors.market_data`  
**Class:** `PriceExtractor`  
**Purpose:** Fetches and standardizes historical equity price data into a clean, long-format Pandas DataFrame. Automatically handles `.NS` exchange suffixes for Indian tickers.

### `fetch_ohlcv`
Fetches historical Open, High, Low, Close, Volume data.

| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `tickers` | `Union[str, List[str]]` | **Required** | Indian company symbol(s). E.g., `"TCS"` or `["TCS", "INFY"]`. |
| `interval` | `str` | `"1d"` | Frequency of the data. Accepted: `"1d"`, `"1wk"`, `"1mo"`. |
| `period` | `str` | `"1y"` | Lookback window. Accepted: `"1mo"`, `"6mo"`, `"1y"`, `"2y"`, `"5y"`, `"max"`. |
| `start_date` | `Optional[str]` | `None` | Start date (`YYYY-MM-DD`). Overrides `period` if provided. |
| `end_date` | `Optional[str]` | `None` | End date (`YYYY-MM-DD`). Used with `start_date`. |

**Returns:** `pd.DataFrame` containing columns: `[Date, Ticker, Open, High, Low, Close, Adj Close, Volume]`.

### Local Index Extractor (NSE Excel Engine)
**Module:** `findia.extractors.index_data`  
**Class:** `LocalIndexExtractor`  
**Purpose:** Bypasses NSE rate limits by extracting and resampling historical Total Returns Index (TRI) and Close data from locally downloaded NSE Excel files.

#### `__init__`
| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `data_dir` | `str` | `"data/nse_data"` | Local directory containing the downloaded NSE Excel files. |

#### `fetch_historical_data`
| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `tickers` | `Union[str, List[str]]` | **Required** | Index symbol(s) mapped in `file_map` (e.g., `"NIFTY_MIDCAP_150"`). |
| `interval` | `str` | `"1d"` | Bar frequency. Accepted: `"1d"`, `"1wk"`, `"1mo"`. |
| `period` | `str` | `"1y"` | Lookback window. Accepted: `"1mo"`, `"3mo"`, `"6mo"`, `"1y"`, `"2y"`, `"5y"`, `"10y"`, `"max"`. |
| `start_date` | `Optional[str]` | `None` | Start date (`YYYY-MM-DD`). Overrides `period`. |
| `end_date` | `Optional[str]` | `None` | End date (`YYYY-MM-DD`). Used with `start_date`. |

**Returns:** `pd.DataFrame` containing columns: `[Date, Index Name, Close, Total Returns Index]`.
---

## 2. Fundamental Extraction (`Screener.in` Engines)

### Annual Engine
**Module:** `findia.extractors.screener_annual`  
**Class:** `ScreenerAnnualEngine`  
**Purpose:** Extracts and cleans multi-year annual financial tables (P&L, Balance Sheet, Cash Flow, Ratios, Shareholding).

#### `fetch_and_clean`
| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `ticker` | `str` | **Required** | Stock ticker symbol (e.g., `"RELIANCE"`). |
| `reporting_level`| `str` | `"consolidated"` | Toggle between `"consolidated"` or `"standalone"`. |

**Returns:** `Dict[str, pd.DataFrame]` containing keys: `PL_Annual`, `Balance_Sheet`, `Cash_Flow`, `Ratios`, `Shareholding`.

#### `export_to_excel`
| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `ticker` | `str` | **Required** | Stock ticker symbol. |
| `reporting_level`| `str` | `"consolidated"` | Toggle between `"consolidated"` or `"standalone"`. |
| `output_dir` | `str` | `"data"` | Target directory. Exports `{TICKER}_Clean_Annual_Fundamentals.xlsx`. |

**Returns:** `pathlib.Path` pointing to the generated Excel file.

---

### Quarterly Engine
**Module:** `findia.extractors.screener_quarterly`  
**Class:** `ScreenerQuarterlyEngine`  
**Purpose:** Extracts high-frequency quarterly earnings performance (last ~10–12 quarters) and multi-year CAGR metrics.

#### `fetch_quarterly_data`
| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `ticker` | `str` | **Required** | Stock ticker symbol (e.g., `"RELIANCE"`). |
| `reporting_level`| `str` | `"consolidated"` | Toggle between `"consolidated"` or `"standalone"`. |

**Returns:** `Dict[str, pd.DataFrame]` containing keys: `PL_Quarterly`, `Compounded_Growth`.

#### `export_to_excel`
| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `ticker` | `str` | **Required** | Stock ticker symbol. |
| `reporting_level`| `str` | `"consolidated"` | Toggle between `"consolidated"` or `"standalone"`. |
| `output_dir` | `str` | `"data"` | Target directory. Exports `{TICKER}_Clean_Quarterly_Fundamentals.xlsx`. |

**Returns:** `pathlib.Path` pointing to the generated Excel file.

---

## 3. Data Loaders & Exporting

**Module:** `findia.loaders.exporter`  
**Class:** `DataExporter`  
**Purpose:** Handles the saving and formatting of quantitative DataFrames to local disk workspaces.

### `__init__`
| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `output_dir` | `Union[str, Path]`| `"data"` | Folder where files are saved. Automatically creates it if missing. |

### `to_excel`
| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `df` | `pd.DataFrame` | **Required** | The standardized DataFrame to be exported. |
| `filename` | `str` | **Required** | Name of the output file. E.g., `"analysis.xlsx"`. |
| `group_by_ticker`| `bool` | `False` | If `True`, splits multi-company data into separate worksheet tabs based on a `"Ticker"` column. If `False`, dumps all data into one master sheet. |

**Returns:** `pathlib.Path` pointing to the generated Excel file.



---

## 4. Multimodal Vision Extraction (LLM / Vision OCR)

### Core Financial Statements Extractor
**Module:** `findia.extractors.financial_statement_extractor`  
**Class:** `VisionExtractor`  
**Purpose:** Processes a directory containing standard financial statement image snapshots (`balance_sheet.png`, `income_statement.png`, `cash_flow.png`) and converts them into structured DataFrames using Gemini 2.5 Vision.

#### `__init__`
| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `api_key` | `Optional[str]` | `None` | Google AI Studio key. If `None`, automatically loads `GEMINI_API_KEY` from `.env`. |

#### `extract_image_to_df`
| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `image_path` | `Path` | **Required** | Path to an image file (`.png`, `.jpg`). |

**Returns:** `pd.DataFrame` containing the extracted table, preserving exact row and column structure.

#### `process_input_directory`
| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `input_dir` | `str` | **Required** | Directory containing target financial images (`balance_sheet.png`, `income_statement.png`, `cash_flow.png`). |

**Returns:** `Dict[str, pd.DataFrame]` mapped to keys: `Balance_Sheet`, `Income_Statement`, `Cash_Flow`.

---

### Generic Table Vision Extractor
**Module:** `findia.extractors.generic_vision_extractor`  
**Class:** `GenericVisionExtractor`  
**Purpose:** Arbitrary table ingestion engine. Scans a directory for any image files (cropped footnotes, segment disclosures, debt schedules) and dynamically converts them to DataFrames.

#### `__init__`
| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `api_key` | `Optional[str]` | `None` | Google AI Studio key. If `None`, automatically loads `GEMINI_API_KEY` from `.env`. |

#### `extract_image_to_df`
| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `image_path` | `Path` | **Required** | Path to any table image file. |

**Returns:** `pd.DataFrame` containing the structured tabular data.

#### `process_directory`
| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `input_dir` | `str` | **Required** | Directory containing image files. |

**Returns:** `Dict[str, pd.DataFrame]` where keys are dynamically derived from image filenames (truncated to 31 characters for Excel tab compatibility).

## 5. Quantitative Transformation & Risk Analytics (Phase 2)

**Module:** `findia.transform.stock`  
**Class:** `StockAnalytics`  
**Purpose:** Asset-level quantitative transformation engine. Calculates dynamic risk (Calendar CAGR, Volatility, Sharpe, Sortino), runs OLS Beta regression against a Total Returns Index (TRI), and generates visual underwater curves.

### `__init__`
| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `risk_free_rate` | `float` | `0.07` | Default risk-free rate used for Sharpe and Sortino calculations (7% representing approx. Indian 10Y G-Sec). |

### `generate_pipeline_report`
Orchestrates Phase 1 extraction, Phase 2 transformation, and exports dual-layer tables (summary + raw datasets) and charts.

| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `ticker` | `str` | **Required** | Target stock ticker symbol. |
| `index_ticker` | `str` | **Required** | Benchmark index symbol (must map to local NSE TRI data keys). |
| `period` | `str` | **Required** | Lookback window (e.g., `"2y"`, `"5y"`). |
| `interval` | `str` | **Required** | Bar frequency. Used to dynamically align Beta regression (e.g., `"1wk"` automatically aligns to Fridays). |
| `output_dir` | `str` | **Required** | Target directory for the generated outputs. |

**Returns:** `None`. Writes `{TICKER}_Pipeline_Summary.xlsx` and `{TICKER}_Underwater_Curve.png` directly to disk.

### `calculate_risk_metrics`
| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `prices_df` | `pd.DataFrame` | **Required** | Price action DataFrame containing a `Close` column. |
| `interval` | `str` | **Required** | Data frequency used to determine the mathematical annualization factor. |
| `period` | `str` | **Required** | Lookback period used purely for audit logging. |

**Returns:** `Tuple[pd.DataFrame, pd.DataFrame]` containing the Risk Summary table and the raw historical dataset.

### `calculate_market_beta`
Runs an OLS regression, automatically isolating the Total Returns Index and dynamically resampling both arrays to ensure perfect date alignment.

| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `stock_df` | `pd.DataFrame` | **Required** | Target stock price data. |
| `index_df` | `pd.DataFrame` | **Required** | Benchmark index data. |
| `stock_ticker`| `str` | **Required** | Name of the stock for column and audit labeling. |
| `index_ticker`| `str` | **Required** | Name of the index for column and audit labeling. |
| `interval` | `str` | **Required** | Frequency used to dynamically resample and align the time-series arrays. |

**Returns:** `Tuple[pd.DataFrame, pd.DataFrame]` containing the Regression Summary table and the aligned historical returns array.