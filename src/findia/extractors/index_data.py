"""Local Excel Extractor for NSE Indices (Total Return Focus), mimicking yfinance API."""

import sys
import logging
from pathlib import Path
from typing import Union, List, Optional
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Allow direct CLI execution
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class LocalIndexExtractor:
    """Extracts and resamples historical index data (Close & Total Returns) from local NSE files."""

    VALID_INTERVALS = ["1d", "1wk", "1mo"]
    VALID_PERIODS = ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"]

    def __init__(self, data_dir: str = "data/nse_data"):
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            logger.warning(f"Data directory {self.data_dir.resolve()} does not exist. Creating it.")
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
        # Map logical index tickers to their downloaded NSE Excel filenames
        self.file_map = {
            "NIFTY_MIDCAP_150": "3_NIFTY_MIDCAP150_HISTORICAL.xlsx",
            "NIFTY_50": "1_NIFTY50_HISTORICAL.xlsx", 
            "NIFTY_NEXT50": "2_NIFTY_NEXT50_HISTORICAL.xlsx",
            "NIFTY_SMALLCAP_250":"4_NIFTY_SMALLCAP150_HISTORICAL.xlsx",
            "NIFTY_500":"5_NIFTY500_HISTORICAL.xlsx"
        }

    def _calculate_start_date(self, period: str, end_date: datetime) -> datetime:
        """Calculates start date based on the yfinance-style period string."""
        if period == "max":
            return datetime(1990, 1, 1) # Safe lower bound for Indian Indices
            
        value = int(period[:-2]) if period.endswith("mo") else int(period[:-1])
        unit = period[-2:] if period.endswith("mo") else period[-1]

        if unit == "mo":
            return end_date - relativedelta(months=value)
        elif unit == "y":
            return end_date - relativedelta(years=value)
        else:
            raise ValueError(f"Unsupported period format: {period}")

    def _clean_and_resample(self, df: pd.DataFrame, interval: str) -> pd.DataFrame:
        """Cleans missing data and resamples strictly for closing/TRI values."""
        # Force numeric, turning older '-' strings into NaN
        for col in ['Close', 'Total Returns Index']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Forward fill missing values to prevent gaps in trading days
        df.ffill(inplace=True)
        # Drop rows where even ffill couldn't find a base value
        df.dropna(subset=['Close', 'Total Returns Index'], how='all', inplace=True)

        # Resampling logic (Last valid value of the period)
        if interval == "1d":
            return df
            
        resample_rule = 'W' if interval == '1wk' else 'ME' 
        
        agg_dict = {
            'Close': 'last',
            'Total Returns Index': 'last',
            'Ticker': 'first'
        }
        
        resampled_df = df.resample(resample_rule).agg(agg_dict)
        resampled_df.dropna(subset=['Close'], inplace=True)
        
        return resampled_df

    def fetch_historical_data(
        self,
        tickers: Union[str, List[str]],
        interval: str = "1d",
        period: str = "1y",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetches historical TRI and Close data, replicating standard OHLCV API interfaces.
        """
        if interval not in self.VALID_INTERVALS:
            raise ValueError(f"Invalid interval '{interval}'. Allowed: {self.VALID_INTERVALS}")

        ticker_list = [tickers] if isinstance(tickers, str) else tickers
        
        end_dt = pd.to_datetime(end_date) if end_date else datetime.now()
        if start_date:
            start_dt = pd.to_datetime(start_date)
        else:
            if period not in self.VALID_PERIODS:
                raise ValueError(f"Invalid period '{period}'. Allowed: {self.VALID_PERIODS}")
            start_dt = self._calculate_start_date(period, end_dt)

        all_data = []

        for ticker in ticker_list:
            if ticker not in self.file_map:
                logger.error(f"Ticker {ticker} not mapped. Available: {list(self.file_map.keys())}")
                continue

            file_path = self.data_dir / self.file_map[ticker]
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                continue
            
            try:
                # Strictly pull Date, Close, and TRI
                df = pd.read_excel(file_path, usecols=['Date', 'Close', 'Total Returns Index'])
                df['Date'] = pd.to_datetime(df['Date'])
                
                # Filter by exact date window
                mask = (df['Date'] >= start_dt) & (df['Date'] <= end_dt)
                df = df.loc[mask].copy()
                
                if df.empty:
                    logger.warning(f"No data found for {ticker} in the specified date range.")
                    continue

                df['Ticker'] = ticker
                df.set_index('Date', inplace=True)
                df.sort_index(inplace=True)

                df = self._clean_and_resample(df, interval)
                df.reset_index(inplace=True)
                
                all_data.append(df)
                
            except Exception as e:
                logger.error(f"Failed to process {ticker}: {e}")

        if not all_data:
            return pd.DataFrame()

        final_df = pd.concat(all_data, ignore_index=True)
        
        # Strip the time component so Excel only sees YYYY-MM-DD
        final_df['Date'] = final_df['Date'].dt.date
        
        # Rename 'Ticker' to 'Index Name' for a cleaner presentation
        final_df.rename(columns={'Ticker': 'Index Name'}, inplace=True)
        
        # Enforce column order
        return final_df[['Date', 'Index Name', 'Close', 'Total Returns Index']]


# =====================================================================
# CLI Execution & Export Block
# =====================================================================
if __name__ == "__main__":
    print("\n--- Testing FinDia Local Index Extractor (TRI Focus) ---")
    
    engine = LocalIndexExtractor(data_dir="data/nse_data")
    output_dir = Path("data/pipeline_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Target our specific index
    target_indices = ["NIFTY_MIDCAP_150"] 
    
    print(f"\nFetching Monthly data for {target_indices} (5 Year Lookback)...")
    df_indices = engine.fetch_historical_data(
        tickers=target_indices, 
        interval="1mo", 
        period="5y"
    )
    
    if not df_indices.empty:
        out_file = output_dir / "Indices_Historical_TRI.xlsx"
        
        # Group the concatenated DataFrame by Index Name and write to separate tabs
        with pd.ExcelWriter(out_file, engine="openpyxl") as writer:
            for index_name, group_df in df_indices.groupby("Index Name"):
                # We retain the Index Name column as requested
                group_df.to_excel(writer, sheet_name=index_name, index=False)
                
        print(f"\n[Success] Local Index data exported to: {out_file.resolve()}")
        print(df_indices.head())
    else:
        print("\n[Failure] No data returned. Please check your data/nse_data folder.")