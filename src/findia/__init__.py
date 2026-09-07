"""
FinDia: Financial Data Pipeline for Indian Stock Markets.

Provides direct access to core extraction engines and export utilities.
"""

from findia.extractors.market_data import PriceExtractor
from findia.extractors.screener_annual import ScreenerAnnualEngine
from findia.extractors.screener_quarterly import ScreenerQuarterlyEngine
from findia.extractors.financial_statement_extractor import VisionExtractor
from findia.extractors.generic_vision_extractor import GenericVisionExtractor
from findia.loaders.exporter import DataExporter
from findia.extractors.index_data import LocalIndexExtractor

__version__ = "0.1.0"
__author__ = "DeepStratAI"

# Define explicit public exports
__all__ = [
    "PriceExtractor",
    "ScreenerAnnualEngine",
    "ScreenerQuarterlyEngine",
    "VisionExtractor",
    "GenericVisionExtractor",
    "DataExporter",
    "LocalIndexExtractor"
] 
