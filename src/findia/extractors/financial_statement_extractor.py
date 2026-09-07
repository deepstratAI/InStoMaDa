"""Multimodal Vision Extractor for digitizing financial statement images."""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Optional
import pandas as pd
import google.generativeai as genai
from PIL import Image

# NEW: Import dotenv
from dotenv import load_dotenv

# Allow direct CLI execution
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from findia.loaders.exporter import DataExporter

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# NEW: Load the .env file into the script's environment
load_dotenv()

class VisionExtractor:
    """Uses Gemini Vision API to deterministically extract tabular data from images."""

    def __init__(self, api_key: Optional[str] = None):
        """Initializes the Gemini Vision client."""
        # This will now successfully pull from your .env file
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY is missing. Set it in your .env file.")

        genai.configure(api_key=key)

        # 1. Dynamically fetch models authorized for this specific API key
        try:
            supported_models = [
                m.name for m in genai.list_models() 
                if 'generateContent' in m.supported_generation_methods
            ]
        except Exception as e:
            raise ConnectionError(f"Failed to communicate with Google API: {e}")

        # 2. Priority cascade for tabular OCR tasks
        preferred_models = [
            'models/gemini-1.5-flash',
            'models/gemini-1.5-flash-latest',
            'models/gemini-1.5-pro',
            'models/gemini-1.5-pro-latest',
            'models/gemini-pro-vision'  # Legacy fallback for very old keys
        ]
        
        # 3. Automatically assign the best available model
        selected_model = None
        for pref in preferred_models:
            if pref in supported_models:
                selected_model = pref
                break
                
        if not selected_model:
            # If our preferred list fails, grab the first available vision model
            if supported_models:
                selected_model = supported_models[0]
            else:
                raise ValueError("Your API key does not have access to any Gemini Vision models.")
                
        logger.info("Dynamically authenticated and loaded Vision Model: %s", selected_model)

        self.model = genai.GenerativeModel(selected_model)
        
        self.extraction_prompt = (
            "You are a precision financial data extraction AI. "
            "Extract the tabular data from this financial statement image exactly as shown. "
            "Rules:\n"
            "1. Replicate the exact row and column structure.\n"
            "2. Ensure headers match exactly (e.g., 'Particulars', 'Note', 'As at March 31').\n"
            "3. If a cell is blank or has a dash, represent it as an empty string (\"\").\n"
            "4. Return the data STRICTLY as a raw JSON list of lists. Do NOT wrap it in ```json blocks. "
            "Example format: [[\"Header1\", \"Header2\"], [\"Value1\", \"Value2\"]]"
        )

    def extract_image_to_df(self, image_path: Path) -> pd.DataFrame:
        """Processes a single image and converts it into a Pandas DataFrame."""
        if not image_path.exists():
            logger.error("Image file not found: %s", image_path)
            return pd.DataFrame()

        logger.info("Digitizing image: %s", image_path.name)
        
        try:
            img = Image.open(image_path)
            response = self.model.generate_content([self.extraction_prompt, img])
            
            # Clean potential LLM markdown artifacts just in case
            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
                
            # Parse the strict JSON 2D array
            table_data = json.loads(raw_text.strip())
            
            if not table_data or len(table_data) < 2:
                logger.warning("No valid tabular data found in %s", image_path.name)
                return pd.DataFrame()

            # First list is columns, rest is data
            columns = table_data[0]
            data = table_data[1:]
            
            df = pd.DataFrame(data, columns=columns)
            return df

        except Exception as e:
            logger.error("Vision extraction failed for %s: %s", image_path.name, e)
            return pd.DataFrame()

    def process_input_directory(self, input_dir: str) -> Dict[str, pd.DataFrame]:
        """Scans an input directory for specific financial images and extracts them."""
        input_path = Path(input_dir)
        if not input_path.exists():
            logger.error("Input directory does not exist: %s", input_dir)
            return {}

        # Expected file mapping (Snapshot Name -> File Name)
        expected_files = {
            "Balance_Sheet": "balance_sheet.png",
            "Income_Statement": "income_statement.png",
            "Cash_Flow": "cash_flow.png"
        }

        extracted_data = {}
        for sheet_name, filename in expected_files.items():
            file_path = input_path / filename
            if file_path.exists():
                df = self.extract_image_to_df(file_path)
                if not df.empty:
                    extracted_data[sheet_name] = df
            else:
                logger.warning("Expected file missing: %s", file_path)

        return extracted_data


# =====================================================================
# CLI Execution Block
# =====================================================================
if __name__ == "__main__":
    print("\n--- Starting FinDia Stage 4: Vision OCR Extraction ---")
    
    # 1. Ensure directories exist
    input_directory = Path("data/input")
    input_directory.mkdir(parents=True, exist_ok=True)
    
    output_directory = Path("data/pipeline_output")
    output_directory.mkdir(parents=True, exist_ok=True)

    print(f"\n[Notice] Please ensure your images are placed in: {input_directory.resolve()}")
    print("Expected filenames: 'balance_sheet.png', 'income_statement.png', 'cash_flow.png'")
    
    # Require API Key setup
    if not os.environ.get("GEMINI_API_KEY"):
        print("\n[ERROR] GEMINI_API_KEY environment variable is not set.")
        print("Run: set GEMINI_API_KEY=your_api_key_here (Windows) or export GEMINI_API_KEY=... (Mac/Linux)")
        sys.exit(1)

    # 2. Initialize Engines
    vision_engine = VisionExtractor()
    exporter = DataExporter(output_dir=output_directory)

    # 3. Process Images
    print("\nScanning input directory and digitizing images...")
    financial_tables = vision_engine.process_input_directory(str(input_directory))

    # 4. Export to Excel
    if financial_tables:
        exporter.to_excel(
            df=pd.DataFrame(), # Dummy DF as we are passing a dict via a custom loop below
            filename="Digitized_Financials.xlsx" 
        )
        # Bypassing standard exporter for multi-sheet dict export
        out_file = output_directory / "Digitized_Financials.xlsx"
        with pd.ExcelWriter(out_file, engine="openpyxl") as writer:
            for sheet_name, df in financial_tables.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f" -> Successfully extracted and saved: {sheet_name}")
                
        print(f"\n[Success] Workbook Created: {out_file.resolve()}")
    else:
        print("\n[Failure] No valid images were processed.")

    print("\n--- Vision Extraction Completed ---")