# File: InStoMaDa/main.py
"""
Main driver script for executing end-to-end FinDia data pipelines.
Demonstrates clean top-level imports from the findia package.
"""

import sys
import shutil
from pathlib import Path
import pandas as pd

# Add 'src' to path for local execution before pip package installation
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Top-level unified imports enabled by src/findia/__init__.py
from findia import (
    PriceExtractor,
    ScreenerAnnualEngine,
    ScreenerQuarterlyEngine,
    DataExporter,
    VisionExtractor,
    LocalIndexExtractor
)


def run_pipeline(ticker: str = "EMMVEE"):
    print(f"\n==================================================")
    print(f"   Starting Full FinDia Analysis for: {ticker}")
    print(f"==================================================")

    # Setup Workspace & Purge Stale Files
    output_dir = Path("data/pipeline_output")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    exporter = DataExporter(output_dir=output_dir)

    # 1. Price Action Extraction
    print(f"\n[1/3] Extracting Price Action Data (yfinance)...")
    price_engine = PriceExtractor()
    df_price = price_engine.fetch_ohlcv(tickers=ticker, interval="1d", period="2y")
    if not df_price.empty:
        exporter.to_excel(df_price, filename=f"{ticker}_Price_Action.xlsx")
        print(f"      Successfully saved Price Action data.")

    # 2. Annual Fundamentals Extraction
    print(f"\n[2/3] Extracting Annual Financials (Screener.in)...")
    annual_engine = ScreenerAnnualEngine()
    annual_engine.export_to_excel(ticker=ticker, output_dir=output_dir)
    print(f"      Successfully saved Annual Statements.")

    # 3. Quarterly Fundamentals Extraction
    print(f"\n[3/3] Extracting Quarterly Financials & Growth (Screener.in)...")
    quarterly_engine = ScreenerQuarterlyEngine()
    quarterly_engine.export_to_excel(ticker=ticker, output_dir=output_dir)
    print(f"      Successfully saved Quarterly & Growth Statements.")

    # 4. Multimodal Vision Extraction (Financial Statements)
    print(f"\n[4/4] Extracting Financial Statements from Images (Gemini Vision)...")
    input_dir = Path("data/input")
    
    # Fault-tolerant check: Only run if the directory exists and has files
    if input_dir.exists() and any(input_dir.iterdir()):
        vision_engine = VisionExtractor()
        financial_tables = vision_engine.process_input_directory(str(input_dir))
        
        if financial_tables:
            vision_out_file = output_dir / f"{ticker}_Digitized_Financials.xlsx"
            with pd.ExcelWriter(vision_out_file, engine="openpyxl") as writer:
                for sheet_name, df in financial_tables.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"      Successfully saved Digitized Vision Statements.")
        else:
            print("      No valid tables extracted from images.")
    else:
        print(f"      Skipping: No input images found in {input_dir.resolve()}")

    # =====================================================================
    # 5. Market Index Data Extraction (Local Excel)
    # =====================================================================
    print(f"\n[5/5] Extracting Market Index Data (Local Excel)...")
    
    # Engine Initialization: Points to the local directory containing the NSE Excel files.
    index_engine = LocalIndexExtractor(data_dir="data/nse_data")
    
    # ---------------------------------------------------------------------
    # CONFIGURATION REFERENCE:
    # - tickers: List of index names matching the keys in LocalIndexExtractor.file_map 
    #            (e.g., ["NIFTY_MIDCAP_150", "NIFTY_50"])
    # - interval: Bar frequency. Allowed values: "1d", "1wk", "1mo"
    # - period: Lookback window. Allowed values: "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"
    #           (Note: 'period' is ignored if start_date and end_date are explicitly provided)
    # - start_date / end_date: Explicit date strings in 'YYYY-MM-DD' format (Optional)
    # ---------------------------------------------------------------------
    target_indices = ["NIFTY_MIDCAP_150"]
    
    df_indices = index_engine.fetch_historical_data(
        tickers=target_indices,
        interval="1mo",   # Aggregates to end-of-month Close/TRI
        period="5y"       # 5-year historical lookback
    )
    
    if not df_indices.empty:
        index_out_file = output_dir / "Indices_Historical_TRI.xlsx"
        with pd.ExcelWriter(index_out_file, engine="openpyxl") as writer:
            for index_name, group_df in df_indices.groupby("Index Name"):
                group_df.to_excel(writer, sheet_name=index_name, index=False)
        print(f"      Successfully saved Local Index data for: {target_indices}")
    else:
        print("      Skipping: No valid index data found in data/nse_data/")

    print(f"\n==================================================")
    print(f" Pipeline Complete! Files saved to: {output_dir.resolve()}")
    print(f"==================================================\n")


if __name__ == "__main__":
    run_pipeline("GENUSPOWER")