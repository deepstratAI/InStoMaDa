# File: src/findia/extractors/screener_quarterly_full.py
"""Unified Screener.in Full Quarterly Fundamentals & Shareholding Engine via Playwright."""

import io
import re
import sys
import logging
from pathlib import Path
from typing import Dict, Optional
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Allow direct CLI execution
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ScreenerQuarterlyFullEngine:
    """
    Extracts full Level 1 & Level 2 Quarterly Results, Compounded Growth metrics, 
    and Quarterly Shareholding Patterns from Screener.in via Playwright rendering.
    """

    BASE_URL = "https://www.screener.in/company"

    def __init__(self, headless: bool = True, timeout_ms: int = 20000) -> None:
        self.headless = headless
        self.timeout_ms = timeout_ms

    def _fetch_expanded_html(self, ticker: str, reporting_level: str = "consolidated") -> Optional[str]:
        """
        Launches Playwright, navigates to the company page, iteratively expands 
        ALL '+' buttons across Quarterly P&L and Shareholding sections, 
        and returns the fully rendered HTML DOM.
        """
        clean_ticker = ticker.upper().replace(".NS", "").replace(".BO", "")
        url = f"{self.BASE_URL}/{clean_ticker}/"
        if reporting_level == "consolidated":
            url = f"{url}consolidated/"

        logger.info("Launching Playwright for FULL Quarterly expansion: %s (%s)...", clean_ticker, reporting_level)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                viewport={"width": 1280, "height": 960},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            try:
                page.goto(url, timeout=self.timeout_ms, wait_until="domcontentloaded")
                page.wait_for_selector("table.data-table", timeout=10000)

                # Target expandable schedule and shareholding buttons containing '+'
                plus_buttons = page.locator("table.data-table button.button-plain:has-text('+')")

                max_clicks = 30
                clicks_performed = 0

                # Iteratively click the FIRST available '+' button until all are expanded
                while plus_buttons.count() > 0 and clicks_performed < max_clicks:
                    target_btn = plus_buttons.first

                    try:
                        target_btn.scroll_into_view_if_needed(timeout=2000)

                        if target_btn.is_visible():
                            target_btn.click(timeout=2000)
                            clicks_performed += 1
                            page.wait_for_timeout(300)  # Pause for AJAX row injection
                        else:
                            break
                    except PlaywrightTimeoutError:
                        logger.warning("Timeout clicking button at iteration %d. Proceeding...", clicks_performed)
                        break
                    except Exception as btn_err:
                        logger.debug("Skipped unclickable button: %s", btn_err)
                        break

                logger.info("Successfully clicked and expanded %d quarterly schedule/shareholding buttons.", clicks_performed)

                page.wait_for_timeout(600)
                expanded_html = page.content()

            except Exception as err:
                logger.error("Error during Playwright quarterly extraction for %s: %s", clean_ticker, err)
                expanded_html = None
            finally:
                browser.close()

        return expanded_html

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Applies quantitative cleaning rules to a raw expanded Screener table."""
        first_col_name = df.columns[0]
        df = df.set_index(first_col_name)

        # Clean row labels: strip trailing '+' triggers, keep leading spaces for hierarchy
        cleaned_index = []
        for label in df.index.astype(str):
            clean_lbl = re.sub(r"\s*\+$", "", label).rstrip()
            cleaned_index.append(clean_lbl)

        df.index = cleaned_index
        df.index.name = "Line Item"

        # Clean numerical values
        for col in df.columns:
            if df[col].dtype == object:
                cleaned_series = (
                    df[col]
                    .astype(str)
                    .str.replace(",", "", regex=False)
                    .str.replace("%", "", regex=False)
                    .str.strip()
                )
                df[col] = pd.to_numeric(cleaned_series, errors="coerce")

        return df

    def fetch_quarterly_data(self, ticker: str, reporting_level: str = "consolidated") -> Dict[str, pd.DataFrame]:
        """
        Executes visual rendering, extracts expanded Quarterly P&L, CAGR Growth tables, 
        and Quarterly Shareholding Patterns into DataFrames.
        """
        expanded_html = self._fetch_expanded_html(ticker, reporting_level)
        if not expanded_html:
            logger.error("Failed to acquire expanded HTML for ticker: %s", ticker)
            return {}

        soup = BeautifulSoup(expanded_html, "html.parser")

        # Prefix Level 2 schedule & shareholder sub-rows in the DOM
        for child_tr in soup.find_all("tr", class_=re.compile(r"schedule-")):
            td_label = child_tr.find("td")
            if td_label:
                raw_text = td_label.get_text(strip=True)
                if not raw_text.startswith("  - "):
                    td_label.string = f"  - {raw_text}"

        try:
            tables = pd.read_html(io.StringIO(str(soup)))
        except Exception as err:
            logger.error("Failed to parse tables from expanded HTML: %s", err)
            return {}

        collated_data = {}
        growth_tables = []

        for df in tables:
            if df.empty or df.shape[1] < 2:
                continue

            raw_text = " ".join(str(val) for val in df.values.flatten()).lower()

            # Identify Quarterly P&L (Has Sales / Operating Profit, but NO Dividend Payout)
            if ("sales" in raw_text or "operating profit" in raw_text) and "dividend payout" not in raw_text:
                collated_data["PL_Quarterly"] = self._clean_dataframe(df)

            # Identify Compounded Growth tables
            elif "compounded sales growth" in raw_text or "stock price cagr" in raw_text or "return on equity" in raw_text:
                growth_tables.append(self._clean_dataframe(df))

            # Identify Quarterly Shareholding Pattern
            elif "promoters" in raw_text and ("fiis" in raw_text or "diis" in raw_text or "public" in raw_text):
                # Ensure we capture the quarterly breakdown table
                collated_data["Shareholding_Quarterly"] = self._clean_dataframe(df)

        # Concatenate growth metric tables into a single summary DataFrame
        if growth_tables:
            try:
                collated_data["Compounded_Growth"] = pd.concat(growth_tables, axis=0)
            except Exception as e:
                logger.warning("Could not concatenate growth tables: %s", e)

        return collated_data

    def export_to_excel(self, ticker: str, reporting_level: str = "consolidated", output_dir: str = "data") -> Path:
        """Executes full quarterly pipeline and exports workbooks with Level 2 breakdowns."""
        cleaned_tables = self.fetch_quarterly_data(ticker, reporting_level)

        if not cleaned_tables:
            logger.error("No quarterly fundamental tables were parsed successfully.")
            return Path()

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        file_path = out_path / f"{ticker.upper()}_Clean_Quarterly_Full_Fundamentals.xlsx"

        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            for sheet_name, df in cleaned_tables.items():
                df.reset_index().to_excel(writer, sheet_name=sheet_name, index=False)

        logger.info("Successfully exported FULL quarterly fundamentals to: %s", file_path)
        return file_path


# =====================================================================
# CLI Execution Block for Testing
# =====================================================================
if __name__ == "__main__":
    print("\n--- Starting Playwright Screener Full Quarterly Fundamentals Engine ---")

    engine = ScreenerQuarterlyFullEngine(headless=True)
    test_tickers = ["FIEMIND", "EMMVEE", "HBLENGINE"]

    for symbol in test_tickers:
        print(f"\nProcessing {symbol}...")
        output_excel = engine.export_to_excel(symbol, reporting_level="consolidated")

        if output_excel.exists():
            print(f"[Success] Full Quarterly Workbook Created: {output_excel.resolve()}")
        else:
            print(f"[Failure] Failed to complete quarterly extraction for {symbol}")