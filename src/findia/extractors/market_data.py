"""Market Data Extractor module for pulling equity price action via yfinance."""

import sys
import logging
from pathlib import Path
from typing import Union, List, Optional
from datetime import date
import pandas as pd
import yfinance as yf

# Ensure root directory is in sys.path for direct command line execution
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from findia.loaders.exporter import DataExporter

# Configure logging for CLI feedback
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class PriceExtractor:
    """Extracts and normalizes OHLCV price action data from yfinance for Indian equities."""

    VALID_INTERVALS = ["1d", "1wk", "1mo"]
    VALID_PERIODS = ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"]

    def _format_ticker(self, ticker: str, exchange: str = "NS") -> str:
        """
        Ensures Indian ticker symbols have the correct exchange suffix for yfinance.
        
        E.g., 'RELIANCE' -> 'RELIANCE.NS', 'TCS.NS' -> 'TCS.NS'
        """
        ticker = ticker.strip().upper()
        if not (ticker.endswith(".NS") or ticker.endswith(".BO")):
            return f"{ticker}.{exchange}"
        return ticker

    def fetch_ohlcv(
        self,
        tickers: Union[str, List[str]],
        interval: str = "1d",
        period: str = "1y",
        start_date: Optional[Union[str, date]] = None,
        end_date: Optional[Union[str, date]] = None,
    ) -> pd.DataFrame:
        """
        Fetches historical OHLCV data for single or multiple Indian stock tickers.

        Args:
            tickers: Single ticker string (e.g., 'RELIANCE') or list of strings (e.g., ['TCS', 'INFY']).
            interval: Bar frequency ('1d', '1wk', '1mo').
            period: Lookback window ('1mo', '6mo', '1y', '5y', 'max'). Used if start_date is None.
            start_date: Start date string ('YYYY-MM-DD') or date object.
            end_date: End date string ('YYYY-MM-DD') or date object.

        Returns:
            Normalized Pandas DataFrame with columns:
            ['Date', 'Ticker', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
        """
        if interval not in self.VALID_INTERVALS:
            raise ValueError(f"Invalid interval '{interval}'. Must be one of {self.VALID_INTERVALS}")

        # Normalize ticker input to a list
        ticker_list = [tickers] if isinstance(tickers, str) else tickers
        formatted_tickers = [self._format_ticker(t) for t in ticker_list]

        logger.info("Fetching price action data for tickers: %s | Interval: %s", formatted_tickers, interval)

        # Execute extraction via yfinance
        try:
            raw_data = yf.download(
                tickers=formatted_tickers,
                interval=interval,
                period=period if not start_date else None,
                start=start_date,
                end=end_date,
                group_by="ticker" if len(formatted_tickers) > 1 else "column",
                auto_adjust=False,
                progress=False,
            )
        except Exception as err:
            logger.error("Failed to download data from yfinance: %s", err)
            return pd.DataFrame()

        if raw_data.empty:
            logger.warning("No price data returned from yfinance for specified query.")
            return pd.DataFrame()

        # Parse and normalize DataFrame structure
        normalized_df = self._normalize_dataframe(raw_data, formatted_tickers)
        return normalized_df

    def _normalize_dataframe(self, raw_df: pd.DataFrame, tickers: List[str]) -> pd.DataFrame:
        """Normalizes yfinance output into a standard long-format DataFrame."""
        records = []

        if len(tickers) == 1:
            # Single ticker download structure
            ticker = tickers[0]
            df = raw_df.copy().reset_index()
            
            # Flatten multi-index columns if present in newer yfinance versions
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] for col in df.columns]

            df["Ticker"] = ticker
            records.append(df)
        else:
            # Multi-ticker download structure
            for ticker in tickers:
                try:
                    if ticker in raw_df.columns.levels[0]:
                        ticker_df = raw_df[ticker].copy().dropna(how="all").reset_index()
                        ticker_df["Ticker"] = ticker
                        records.append(ticker_df)
                except Exception as parse_err:
                    logger.warning("Could not parse ticker sub-frame for %s: %s", ticker, parse_err)

        if not records:
            return pd.DataFrame()

        combined_df = pd.concat(records, ignore_index=True)

        # Format Date column cleanly
        if "Date" in combined_df.columns:
            combined_df["Date"] = pd.to_datetime(combined_df["Date"]).dt.strftime("%Y-%m-%d")

        # Standardize column order
        standard_cols = ["Date", "Ticker", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
        existing_cols = [col for col in standard_cols if col in combined_df.columns]
        
        final_df = combined_df[existing_cols].sort_values(by=["Ticker", "Date"]).reset_index(drop=True)
        return final_df


# =====================================================================
# CLI Execution & Testing Block
# =====================================================================
if __name__ == "__main__":
    print("\n--- Starting FinDia Stage 1: Price Action Extraction Test ---")

    extractor = PriceExtractor()
    exporter = DataExporter(output_dir="data")

    # Test 1: Single Company Daily OHLCV Data
    single_ticker = "RELIANCE"
    print(f"\n[Test 1] Extracting Daily OHLCV for '{single_ticker}' (Last 1 Year)...")
    df_single = extractor.fetch_ohlcv(tickers=single_ticker, interval="1d", period="1y")

    print("\nDataFrame Shape:", df_single.shape)
    print("Sample Output:")
    print(df_single.head(3))

    # Export Test 1 to Excel
    file_path_single = exporter.to_excel(
        df=df_single, 
        filename="reliance_daily_price.xlsx", 
        group_by_ticker=False
    )
    print(f"Saved Single Ticker Excel to: {file_path_single.resolve()}")

    # Test 2: Multiple Companies Weekly OHLCV Data
    multi_tickers = ["TCS", "INFY", "HDFCBANK"]
    print(f"\n[Test 2] Extracting Weekly OHLCV for Multi-Tickers {multi_tickers}...")
    df_multi = extractor.fetch_ohlcv(tickers=multi_tickers, interval="1wk", period="6mo")

    print("\nDataFrame Shape:", df_multi.shape)
    print("Sample Output:")
    print(df_multi.head(3))

    # Export Test 2 to Excel with separate tabs per ticker
    file_path_multi = exporter.to_excel(
        df=df_multi, 
        filename="tech_banking_weekly_price.xlsx", 
        group_by_ticker=True
    )
    print(f"Saved Multi-Tab Excel to: {file_path_multi.resolve()}")

    print("\n--- Stage 1 Extraction & Export Test Completed Successfully! ---") 
