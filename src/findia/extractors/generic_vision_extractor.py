"""Generic Multimodal Vision Extractor for digitizing any tabular image."""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Optional
import pandas as pd
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

# Allow direct CLI execution
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()


class GenericVisionExtractor:
    """Extracts tabular data from any unstructured image using Gemini Vision."""

    def __init__(self, api_key: Optional[str] = None):
        """Initializes the Gemini client dynamically based on available models."""
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY is missing. Set it in your .env file.")
        
        genai.configure(api_key=key)
        
        try:
            supported_models = [
                m.name for m in genai.list_models() 
                if 'generateContent' in m.supported_generation_methods
            ]
        except Exception as e:
            raise ConnectionError(f"Failed to communicate with Google API: {e}")

        # Priority cascade for tabular OCR tasks
        preferred_models = [
            'models/gemini-2.5-flash',
            'models/gemini-2.5-pro',
            'models/gemini-1.5-flash',
            'models/gemini-1.5-pro',
            'models/gemini-pro-vision' 
        ]
        
        selected_model = None
        for pref in preferred_models:
            if pref in supported_models:
                selected_model = pref
                break
                
        if not selected_model:
            if supported_models:
                selected_model = supported_models[0]
            else:
                raise ValueError("Your API key does not have access to any Gemini Vision models.")
                
        logger.info("Loaded Generic Vision Model: %s", selected_model)
        self.model = genai.GenerativeModel(selected_model)
        
        # A slightly broadened prompt for generic tables
        self.extraction_prompt = (
            "You are a precision data extraction AI. "
            "Extract the tabular data from this image exactly as shown. "
            "Rules:\n"
            "1. Replicate the exact row and column structure.\n"
            "2. Preserve all headers, sub-headers, and numerical values.\n"
            "3. If a cell is blank or has a dash, represent it as an empty string (\"\").\n"
            "4. Return the data STRICTLY as a raw JSON list of lists. Do NOT wrap it in ```json blocks. "
            "Example format: [[\"Header1\", \"Header2\"], [\"Value1\", \"Value2\"]]"
        )

    def extract_image_to_df(self, image_path: Path) -> pd.DataFrame:
        """Processes a single image and converts it into a Pandas DataFrame."""
        logger.info("Digitizing image: %s", image_path.name)
        try:
            img = Image.open(image_path)
            response = self.model.generate_content([self.extraction_prompt, img])
            
            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
                
            table_data = json.loads(raw_text.strip())
            
            if not table_data or len(table_data) < 2:
                return pd.DataFrame()

            columns = table_data[0]
            data = table_data[1:]
            
            return pd.DataFrame(data, columns=columns)

        except Exception as e:
            logger.error("Vision extraction failed for %s: %s", image_path.name, e)
            return pd.DataFrame()

    def process_directory(self, input_dir: str) -> Dict[str, pd.DataFrame]:
        """Scans a directory for ANY images and digitizes them."""
        input_path = Path(input_dir)
        if not input_path.exists():
            logger.error("Input directory does not exist: %s", input_dir)
            return {}

        valid_extensions = {".png", ".jpg", ".jpeg"}
        extracted_data = {}

        for file_path in input_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in valid_extensions:
                df = self.extract_image_to_df(file_path)
                if not df.empty:
                    # Clean filename to act as an Excel Sheet Name (max 31 chars)
                    sheet_name = file_path.stem[:31]
                    extracted_data[sheet_name] = df
                    
        return extracted_data


# =====================================================================
# CLI Configuration & Execution Block
# =====================================================================
if __name__ == "__main__":
    print("\n--- Starting FinDia Generic Table Extractor ---")
    
    # ==========================================
    # USER CONFIGURATION VARIABLES
    # Change these paths for different companies or reports
    # ==========================================
    INPUT_FOLDER = "data/input/annual_report_notes"
    OUTPUT_FOLDER = "data/pipeline_output"
    OUTPUT_FILENAME = "AR_Notes.xlsx"
    
    input_directory = Path(INPUT_FOLDER)
    input_directory.mkdir(parents=True, exist_ok=True)
    
    output_directory = Path(OUTPUT_FOLDER)
    output_directory.mkdir(parents=True, exist_ok=True)

    print(f"\nScanning for all images in: {input_directory.resolve()}")

    engine = GenericVisionExtractor()
    financial_tables = engine.process_directory(str(input_directory))

    if financial_tables:
        out_file = output_directory / OUTPUT_FILENAME
        with pd.ExcelWriter(out_file, engine="openpyxl") as writer:
            for sheet_name, df in financial_tables.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f" -> Successfully extracted and saved tab: {sheet_name}")
                
        print(f"\n[Success] Master Workbook Created: {out_file.resolve()}")
    else:
        print(f"\n[Notice] No valid images found or successfully processed in {INPUT_FOLDER}.")

    print("\n--- Generic Vision Extraction Completed ---")