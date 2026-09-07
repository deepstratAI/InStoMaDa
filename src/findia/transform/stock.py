import sys
import os
from pathlib import Path

# ==========================================
# SYS.PATH HACK FOR INDEPENDENT TESTING
# ==========================================
# This ensures that running `python src/findia/transform/stock.py` directly 
# from the InStoMaDa root terminal will successfully resolve 'findia' imports.
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import pandas as pd
import numpy as np
import scipy.stats as stats

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Import Phase 1 Engines 
from findia.extractors.market_data import PriceExtractor
from findia.extractors.index_data import LocalIndexExtractor
from findia.extractors.screener_annual import ScreenerAnnualEngine
from findia.loaders.exporter import DataExporter

class StockAnalytics:
    """
    Asset-level quantitative transformation engine for Indian Equities.
    Calculates dynamic risk, OLS Beta regression, and fundamental summaries.
    """
    
    ANNUALIZATION_FACTORS = {
        "1d": 252,
        "1wk": 52,
        "1mo": 12
    }

    def __init__(self, risk_free_rate: float = 0.07):
        self.rf_rate = risk_free_rate
        # Initialize Phase 1 Engines
        self.price_engine = PriceExtractor()
        self.screener_engine = ScreenerAnnualEngine()
        # Initialize the Local NSE Engine to bypass rate limits
        self.index_engine = LocalIndexExtractor(data_dir="data/nse_data")

    def _get_factor(self, interval: str) -> int:
        return self.ANNUALIZATION_FACTORS.get(interval, 252)

    def calculate_risk_metrics(self, prices_df: pd.DataFrame, interval: str, period: str):
        """Calculates Returns, Volatility, Sharpe, and Sortino using strict calendar math for CAGR."""
        factor = self._get_factor(interval)
        
        valid_closes = prices_df['Close'].dropna()
        if len(valid_closes) < 2:
            return pd.DataFrame(), pd.DataFrame()

        # Extract datetime objects to compute exact calendar difference
        start_date_obj = pd.to_datetime(prices_df['Date'].iloc[0])
        end_date_obj = pd.to_datetime(prices_df['Date'].iloc[-1])
        
        start_date = start_date_obj.strftime('%Y-%m-%d')
        end_date = end_date_obj.strftime('%Y-%m-%d')

        returns = valid_closes.pct_change().dropna()
        start_price = float(valid_closes.iloc[0])
        end_price = float(valid_closes.iloc[-1])
        
        # FIXED: Calculate precise calendar years to prevent trading-holiday distortion
        days_diff = (end_date_obj - start_date_obj).days
        years = days_diff / 365.25 if days_diff > 0 else 1.0  # Fallback to prevent division by zero
        
        cagr = float((end_price / start_price) ** (1 / years) - 1)
        
        # Volatility scales by trading periods, this remains unchanged
        volatility = float(returns.std() * np.sqrt(factor))
        sharpe = float((cagr - self.rf_rate) / volatility) if volatility != 0 else 0.0

        # Sortino Math (Downside Deviation)
        downside_returns = returns[returns < 0]
        downside_volatility = float(downside_returns.std() * np.sqrt(factor)) if not downside_returns.empty else 0.0
        sortino = float((cagr - self.rf_rate) / downside_volatility) if downside_volatility != 0 else 0.0

        risk_dict = {
            "Metric": [
                "CAGR", 
                "Annualized Volatility", 
                f"Sharpe Ratio (Rf={self.rf_rate*100}%)",
                f"Sortino Ratio (Rf={self.rf_rate*100}%)",
                "---",
                "Input: Data Frequency",
                "Input: Lookback Period",
                "Audit: Start Date",
                "Audit: End Date"
            ],
            "Value": [
                round(cagr, 4), 
                round(volatility, 4), 
                round(sharpe, 4),
                round(sortino, 4),
                "---",
                interval,
                period,
                start_date,
                end_date
            ],
            "Definition": [
                "Compound Annual Growth Rate (Calendar Time)",
                "Annualized Standard Deviation of Returns",
                "Risk-Adjusted Return (Penalizes all volatility)",
                "Risk-Adjusted Return (Penalizes downside volatility)",
                "---",
                "User requested interval",
                "User requested period",
                "First available price date",
                "Last available price date"
            ]
        }
        
        raw_data_df = prices_df[['Date', 'Close']].copy()
        raw_data_df['Return'] = raw_data_df['Close'].pct_change()
        raw_data_df = raw_data_df.dropna()
        
        return pd.DataFrame(risk_dict), raw_data_df

    def calculate_drawdowns(self, prices_df: pd.DataFrame) -> pd.DataFrame:
        rolling_max = prices_df['Close'].cummax()
        drawdown_curve = (prices_df['Close'] - rolling_max) / rolling_max
        
        df_dd = pd.DataFrame({
            "Date": prices_df['Date'],
            "Close": prices_df['Close'],
            "Peak": rolling_max,
            "Drawdown": drawdown_curve
        })
        return df_dd

    def _get_resample_rule(self, interval: str) -> str:
        """Maps user interval strings to Pandas frequency strings."""
        mapping = {
            "1d": "B",       # Business Days
            "1wk": "W-FRI",  # Weekly ending on Friday
            "1mo": "ME"      # Month End
        }
        return mapping.get(interval, "ME")  # Default to monthly if unknown

    def calculate_market_beta(self, stock_df: pd.DataFrame, index_df: pd.DataFrame, stock_ticker: str, index_ticker: str, interval: str):
        """Runs OLS regression explicitly against the TRI, dynamically aligned to user interval."""
        sdf = stock_df[['Date', 'Close']].copy()
        
        if 'Total Returns Index' in index_df.columns:
            idf = index_df[['Date', 'Total Returns Index']].copy()
            idf.rename(columns={'Total Returns Index': 'Close'}, inplace=True)
        else:
            idf = index_df[['Date', 'Close']].copy()

        sdf['Date'] = pd.to_datetime(sdf['Date'], utc=True).dt.tz_localize(None)
        idf['Date'] = pd.to_datetime(idf['Date'], utc=True).dt.tz_localize(None)

        # FIXED: Dynamically align time-series based on user's requested interval
        resample_rule = self._get_resample_rule(interval)
        
        sdf = sdf.set_index('Date').resample(resample_rule).last().reset_index()
        idf = idf.set_index('Date').resample(resample_rule).last().reset_index()

        merged = pd.merge(sdf, idf, on='Date', suffixes=(f'_{stock_ticker}', f'_{index_ticker}')).dropna()
        
        merged[f'Ret_{stock_ticker}'] = merged[f'Close_{stock_ticker}'].pct_change()
        merged[f'Ret_{index_ticker}'] = merged[f'Close_{index_ticker}'].pct_change()
        merged = merged.dropna()
        
        if len(merged) < 2:
            print(f"[!] Warning: Not enough overlapping {interval} dates to compute Beta.")
            return pd.DataFrame({"Error": ["Insufficient data overlap for OLS Regression"]}), pd.DataFrame()
        
        start_date = merged['Date'].iloc[0].strftime('%Y-%m-%d')
        end_date = merged['Date'].iloc[-1].strftime('%Y-%m-%d')
        overlapping_periods = len(merged)

        slope, intercept, r_value, p_value, std_err = stats.linregress(merged[f'Ret_{index_ticker}'], merged[f'Ret_{stock_ticker}'])
        
        r_squared = r_value ** 2
        n = len(merged)
        adj_r_squared = 1 - ((1 - r_squared) * (n - 1) / (n - 2)) if n > 2 else 0
        
        beta_dict = {
            "Regression Metric": [
                "Market Beta", 
                "Alpha (Intercept)", 
                "R-Squared", 
                "Adjusted R-Squared",
                "---",
                "Input: Target Stock",
                "Input: Benchmark Index",
                f"Audit: Overlapping Periods ({interval})",
                "Audit: Start Date (Aligned)",
                "Audit: End Date (Aligned)"
            ],
            "Value": [
                round(slope, 4), 
                round(intercept, 6), 
                round(r_squared, 4), 
                round(adj_r_squared, 4),
                "---",
                stock_ticker,
                index_ticker,
                overlapping_periods,
                start_date,
                end_date
            ],
            "Definition": [
                "Market sensitivity (vs TRI)", 
                "Excess return vs model", 
                "Total variance explained", 
                "Market-explained risk penalizing noise",
                "---",
                "Asset being analyzed",
                "Market proxy used for OLS",
                f"Perfectly aligned {resample_rule} datapoints",
                "First aligned regression date",
                "Last aligned regression date"
            ]
        }
        
        merged['Date'] = merged['Date'].dt.strftime('%Y-%m-%d')
        return pd.DataFrame(beta_dict), merged

    def summarize_fundamentals(self, ticker: str) -> pd.DataFrame:
        try:
            financials = self.screener_engine.fetch_and_clean(ticker=ticker)
            ratios_df = financials.get("Ratios", pd.DataFrame())
            
            roce = ratios_df.loc['ROCE %'].iloc[-1] if 'ROCE %' in ratios_df.index else "N/A"
            debt_days = ratios_df.loc['Debtor Days'].iloc[-1] if 'Debtor Days' in ratios_df.index else "N/A"
            
            fund_dict = {
                "Metric": ["Latest ROCE", "Debtor Days"],
                "Definition": ["Return on Capital Employed (%)", "Time taken to collect cash (Days)"],
                "Value": [roce, debt_days]
            }
            return pd.DataFrame(fund_dict)
        except Exception as e:
            return pd.DataFrame({"Error": [f"Could not extract fundamentals: {str(e)}"]})

    def plot_drawdown_curve(self, df_drawdown: pd.DataFrame, ticker: str, output_dir: str):
        """Generates and saves a high-quality visual Underwater Curve."""
        if df_drawdown.empty or 'Drawdown' not in df_drawdown.columns:
            return
            
        plt.figure(figsize=(10, 5))
        
        # Ensure Date is datetime for plotting
        dates = pd.to_datetime(df_drawdown['Date'])
        # Convert drawdowns to percentages for cleaner visualization
        drawdowns = df_drawdown['Drawdown'] * 100 
        
        # Plot standard Quant Underwater Curve (Red shaded area below 0)
        plt.fill_between(dates, drawdowns, 0, color='crimson', alpha=0.3)
        plt.plot(dates, drawdowns, color='crimson', linewidth=1.5)
        
        plt.title(f"{ticker} - Underwater Curve (Max Drawdown)", fontsize=14, fontweight='bold')
        plt.ylabel("Drawdown (%)", fontsize=12)
        plt.xlabel("Date", fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.6)
        
        # Format X-axis for clean date rendering
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save the plot alongside the Excel file
        output_path = Path(output_dir) / f"{ticker}_Underwater_Curve.png"
        plt.savefig(output_path, dpi=300)
        plt.close()
        print(f"[+] Successfully exported visual Drawdown Chart to {output_path}")


    def generate_pipeline_report(self, ticker: str, index_ticker: str, period: str, interval: str, output_dir: str):
        """Orchestrates extraction, transformation, and exports dual-layer tables and charts."""
        print(f"[*] Starting Pipeline for {ticker} vs {index_ticker} | Period: {period} | Interval: {interval}")
        
        df_stock = self.price_engine.fetch_ohlcv(tickers=ticker, interval=interval, period=period)
        df_index = self.index_engine.fetch_historical_data(tickers=index_ticker, interval=interval, period=period)
        
        if df_index is None or df_index.empty:
            print(f"[!] Warning: Index data for {index_ticker} is empty. Check nse_data folder.")
            return

        df_risk_summary, df_risk_data = self.calculate_risk_metrics(df_stock, interval, period)
        df_drawdown = self.calculate_drawdowns(df_stock)
        df_beta_summary, df_beta_data = self.calculate_market_beta(df_stock, df_index, ticker, index_ticker, interval)
        df_fund = self.summarize_fundamentals(ticker)
        
        output_path = Path(output_dir) / f"{ticker}_Pipeline_Summary.xlsx"
        
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            df_risk_summary.to_excel(writer, sheet_name='Risk_Profile', index=False, startrow=0)
            if not df_risk_data.empty:
                df_risk_data.to_excel(writer, sheet_name='Risk_Profile', index=False, startrow=len(df_risk_summary) + 2)
            
            df_beta_summary.to_excel(writer, sheet_name='Beta_Regression', index=False, startrow=0)
            if not df_beta_data.empty:
                df_beta_data.to_excel(writer, sheet_name='Beta_Regression', index=False, startrow=len(df_beta_summary) + 2)
            
            df_drawdown.to_excel(writer, sheet_name='Underwater_Curve', index=False)
            df_fund.to_excel(writer, sheet_name='Fundamentals', index=False)
            
        print(f"[+] Successfully exported full analytics and raw datasets to {output_path}")
        
        # 4. Generate visual plot (Phase 2 Addition)
        self.plot_drawdown_curve(df_drawdown, ticker, output_dir)

# ==========================================
# INDEPENDENT TEST BLOCK (USER TWEAKABLE)
# ==========================================
if __name__ == "__main__":
    # --- USER CONFIGURATION ---
    TARGET_STOCK = "RELIANCE"         
    
    # Using the local file map key from index_data.py instead of yfinance ticker
    MARKET_INDEX = "NIFTY_50"         
    
    ANALYSIS_PERIOD = "2y"          
    ANALYSIS_INTERVAL = "1wk"       
    OUTPUT_FOLDER = "data/pipeline_output"
    
    analytics = StockAnalytics()
    Path(OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)
    
    analytics.generate_pipeline_report(
        ticker=TARGET_STOCK,
        index_ticker=MARKET_INDEX,
        period=ANALYSIS_PERIOD,
        interval=ANALYSIS_INTERVAL,
        output_dir=OUTPUT_FOLDER
    )