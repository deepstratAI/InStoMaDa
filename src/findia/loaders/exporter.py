"""Data Exporter module for saving FinDia DataFrames to local disk."""

import logging
from pathlib import Path
from typing import Union
import pandas as pd

logger = logging.getLogger(__name__)


class DataExporter:
    """Handles saving structured financial DataFrames to local Excel files."""

    def __init__(self, output_dir: Union[str, Path] = "data") -> None:
        """
        Initializes the exporter with a destination folder.
        
        Args:
            output_dir: Folder path where Excel files will be saved. Defaults to 'data'.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def to_excel(
        self, 
        df: pd.DataFrame, 
        filename: str, 
        group_by_ticker: bool = False
    ) -> Path:
        """
        Exports a normalized price DataFrame to an Excel workbook.

        Args:
            df: Normalized DataFrame containing a 'Ticker' column and price data.
            filename: Name of the output Excel file (e.g., 'price_data.xlsx').
            group_by_ticker: If True, writes each ticker's data to a separate Excel sheet.
                             If False, writes all data into a single sheet.

        Returns:
            Path object pointing to the created Excel file.
        """
        if not filename.endswith(".xlsx"):
            filename += ".xlsx"

        file_path = self.output_dir / filename

        if df.empty:
            logger.warning("Attempted to export an empty DataFrame.")
            return file_path

        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            if group_by_ticker and "Ticker" in df.columns:
                # Split data into individual worksheet tabs per ticker
                for ticker, group_df in df.groupby("Ticker"):
                    # Clean ticker name for sheet tab (remove .NS/.BO if present)
                    sheet_name = str(ticker).replace(".NS", "").replace(".BO", "")[:31]
                    group_df.to_excel(writer, sheet_name=sheet_name, index=False)
                logger.info("Successfully exported multi-tab Excel file: %s", file_path)
            else:
                # Output all data into a single worksheet
                df.to_excel(writer, sheet_name="Price_Action", index=False)
                logger.info("Successfully exported single-tab Excel file: %s", file_path)

        return file_path