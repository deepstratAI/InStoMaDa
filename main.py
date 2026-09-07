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

# Phase 2 Imports
from findia.transform.stock import StockAnalytics


def run_pipeline(ticker: str = "EMMVEE", benchmark_index: str = "NIFTY_MIDCAP_150"):
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
    print(f"\n[1/6] Extracting Price Action Data (yfinance)...")
    price_engine = PriceExtractor()
    df_price = price_engine.fetch_ohlcv(tickers=ticker, interval="1d", period="2y")
    if not df_price.empty:
        exporter.to_excel(df_price, filename=f"{ticker}_Price_Action.xlsx")
        print(f"      Successfully saved Price Action data.")

    # 2. Annual Fundamentals Extraction
    print(f"\n[2/6] Extracting Annual Financials (Screener.in)...")
    annual_engine = ScreenerAnnualEngine()
    annual_engine.export_to_excel(ticker=ticker, output_dir=output_dir)
    print(f"      Successfully saved Annual Statements.")

    # 3. Quarterly Fundamentals Extraction
    print(f"\n[3/6] Extracting Quarterly Financials & Growth (Screener.in)...")
    quarterly_engine = ScreenerQuarterlyEngine()
    quarterly_engine.export_to_excel(ticker=ticker, output_dir=output_dir)
    print(f"      Successfully saved Quarterly & Growth Statements.")

    # 4. Multimodal Vision Extraction (Financial Statements)
    print(f"\n[4/6] Extracting Financial Statements from Images (Gemini Vision)...")
    input_dir = Path("data/input")
    
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
    print(f"\n[5/6] Extracting Market Index Data (Local Excel)...")
    index_engine = LocalIndexExtractor(data_dir="data/nse_data")
    
    target_indices = [benchmark_index]
    
    df_indices = index_engine.fetch_historical_data(
        tickers=target_indices,
        interval="1mo",   
        period="5y"       
    )
    
    if not df_indices.empty:
        index_out_file = output_dir / "Indices_Historical_TRI.xlsx"
        with pd.ExcelWriter(index_out_file, engine="openpyxl") as writer:
            for index_name, group_df in df_indices.groupby("Index Name"):
                group_df.to_excel(writer, sheet_name=index_name, index=False)
        print(f"      Successfully saved Local Index data for: {target_indices}")
    else:
        print("      Skipping: No valid index data found in data/nse_data/")

    # =====================================================================
    # 6. Phase 2: Quantitative Transformation & Risk Analytics
    # =====================================================================
    print(f"\n[6/6] Executing Phase 2: Quantitative Risk & Transformation Engine...")
    
    # ---------------------------------------------------------------------
    # CONFIGURATION REFERENCE:
    # - period: Lookback window for risk metrics (e.g., "1y", "2y", "5y", "max")
    # - interval: Bar frequency for calculations ("1d", "1wk", "1mo")
    # Note: Target stock and benchmark index are passed via function args.
    # ---------------------------------------------------------------------
    analysis_period = "2y"
    analysis_interval = "1wk"
    
    analytics_engine = StockAnalytics()
    analytics_engine.generate_pipeline_report(
        ticker=ticker,
        index_ticker=benchmark_index,
        period=analysis_period,
        interval=analysis_interval,
        output_dir=output_dir
    )
    print(f"      Successfully generated Quantitative Summary & Underwater Curve for {ticker}.")

    print(f"\n==================================================")
    print(f" Pipeline Complete! Files saved to: {output_dir.resolve()}")
    print(f"==================================================\n")


if __name__ == "__main__":
    # Test execution using GENUSPOWER vs NIFTY_50
    run_pipeline(ticker="GENUSPOWER", benchmark_index="NIFTY_500")