"""Screener.in Quarterly Data and Compounded Growth Extractor."""

import io
import sys
import logging
import requests
from pathlib import Path
from typing import Dict
import pandas as pd

# Allow direct CLI execution
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ScreenerQuarterlyEngine:
    """Extracts, cleans, and structures Quarterly tables and CAGR metrics from Screener.in."""

    BASE_URL = "https://www.screener.in/company"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Applies quantitative cleaning rules to a raw Screener table."""
        # 1. Set the first column (Metric Names) as the index
        first_col_name = df.columns[0]
        df = df.set_index(first_col_name)

        # 2. Clean Row Labels (Remove trailing ' +' signs)
        df.index = df.index.astype(str).str.replace(r"\s*\+$", "", regex=True).str.strip()
        df.index.name = "Line Item"

        # 3. Clean Data Values (Strip commas, percentages, and convert to numeric)
        for col in df.columns:
            if df[col].dtype == object:
                # Remove formatting characters
                cleaned_series = (
                    df[col]
                    .astype(str)
                    .str.replace(",", "", regex=False)
                    .str.replace("%", "", regex=False)
                    .str.strip()
                )
                # Coerce to numeric (blanks/errors become NaN)
                df[col] = pd.to_numeric(cleaned_series, errors="coerce")

        return df

    def fetch_quarterly_data(self, ticker: str, reporting_level: str = "consolidated") -> Dict[str, pd.DataFrame]:
        """Fetches HTML and parses out the Quarterly Results and Compounded Growth tables."""
        clean_ticker = ticker.upper().replace(".NS", "").replace(".BO", "")
        url = f"{self.BASE_URL}/{clean_ticker}/"
        if reporting_level == "consolidated":
            url = f"{url}consolidated/"

        logger.info("Fetching Quarterly %s data for %s...", reporting_level, clean_ticker)

        try:
            response = self.session.get(url, timeout=12)
            response.raise_for_status()
            tables = pd.read_html(io.StringIO(response.text))
        except Exception as err:
            logger.error("Failed to extract data: %s", err)
            return {}

        collated_data = {}
        growth_tables = []

        # Scan through all raw tables
        for df in tables:
            if df.empty or df.shape[1] < 2:
                continue

            #raw_text = " ".join(df.astype(str).values.flatten()).lower()
            raw_text = " ".join(str(val) for val in df.values.flatten()).lower()
            table_name = None

            # Identify Quarterly P&L (Has Sales, but NO Dividend Payout)
            if ("sales" in raw_text or "operating profit" in raw_text) and "dividend payout" not in raw_text:
                collated_data["PL_Quarterly"] = self._clean_dataframe(df)
            
            # Identify Compounded Growth tables (Screener splits these into multiple small tables)
            elif "compounded sales growth" in raw_text or "stock price cagr" in raw_text:
                growth_tables.append(self._clean_dataframe(df))

        # Merge growth tables into a single DataFrame if multiple were found
        if growth_tables:
            try:
                collated_data["Compounded_Growth"] = pd.concat(growth_tables, axis=0)
            except Exception as e:
                logger.warning("Could not concatenate growth tables: %s", e)

        return collated_data

    def export_to_excel(self, ticker: str, reporting_level: str = "consolidated", output_dir: str = "data") -> Path:
        """Executes the pipeline and saves the DataFrames to Excel."""
        cleaned_tables = self.fetch_quarterly_data(ticker, reporting_level)
        
        if not cleaned_tables:
            logger.error("No quarterly tables were parsed successfully.")
            return Path()

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        file_path = out_path / f"{ticker.upper()}_Clean_Quarterly_Fundamentals.xlsx"

        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            for sheet_name, df in cleaned_tables.items():
                df.reset_index().to_excel(writer, sheet_name=sheet_name, index=False)

        logger.info("Successfully exported clean quarterly financials to: %s", file_path)
        return file_path


# =====================================================================
# CLI Execution Block
# =====================================================================
if __name__ == "__main__":
    print("\n--- Starting FinDia Stage 3: Unified Quarterly Fundamentals ---")
    
    engine = ScreenerQuarterlyEngine()
    test_ticker = "EMMVEE"
    
    output_excel = engine.export_to_excel(test_ticker, reporting_level="consolidated")
    
    if output_excel.exists():
        print(f"\n[Success] Clean Quarterly Workbook Created: {output_excel.resolve()}")
    else:
        print("\n[Failure] Pipeline did not complete.")