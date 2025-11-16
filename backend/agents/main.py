"""Main entrypoint and example usage for LLM Agent Pipeline."""

import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import config to ensure .env is loaded
from backend.config import get_openai_api_key, is_venv
from backend.agents.pipeline import process_medical_bill

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_usage():
    """Example usage of the medical bill processing pipeline."""
    
    # Check for API key
    try:
        get_openai_api_key()
    except RuntimeError as e:
        logger.error(str(e))
        logger.info(
            "\nTo fix this:\n"
            "1. Create a .env file in the project root\n"
            "2. Add: OPENAI_API_KEY=sk-proj-your-actual-key-here\n"
            "3. Get your key from: https://platform.openai.com/api-keys"
        )
        return
    
    # Example OCR text (simulated from a medical bill)
    example_ocr_text = """
    MEDICAL BILL - EXAMPLE HOSPITAL
    
    Patient: John Doe
    Date of Service: 2024-01-15
    
    Line Items:
    
    1. CPT 99213 - Office Visit, Established Patient
       Quantity: 1
       Price: $250.00
    
    2. CPT 80053 - Comprehensive Metabolic Panel
       Quantity: 1
       Price: $180.00
    
    3. HCPCS J3420 - Injection, Vitamin B-12
       Quantity: 1
       Price: $95.00
    
    4. CPT 99213 - Office Visit, Established Patient
       Quantity: 1
       Price: $250.00
       Note: Duplicate entry?
    
    5. CPT 93000 - Electrocardiogram
       Quantity: 1
       Price: $450.00
    
    Total: $1,225.00
    """
    
    logger.info("=" * 60)
    logger.info("Medical Bill Processing Pipeline - Example Usage")
    logger.info("=" * 60)
    
    try:
        # Process the medical bill
        result = process_medical_bill(ocr_text=example_ocr_text)
        
        # Display results
        print("\n" + "=" * 60)
        print("EXTRACTION RESULTS")
        print("=" * 60)
        print(f"Extracted {len(result['extraction'])} line items:")
        for i, item in enumerate(result['extraction'], 1):
            print(f"\n  Item {i}:")
            print(f"    Code: {item['code']}")
            print(f"    Description: {item['description']}")
            print(f"    Quantity: {item['quantity']}")
            print(f"    Price: ${item['price']:.2f}")
            if item['notes']:
                print(f"    Notes: {item['notes']}")
        
        print("\n" + "=" * 60)
        print("ANALYSIS RESULTS")
        print("=" * 60)
        print(f"Analyzed {len(result['analysis'])} items:")
        for i, item in enumerate(result['analysis'], 1):
            print(f"\n  Item {i}:")
            print(f"    Code: {item['code']}")
            print(f"    Description: {item['description']}")
            print(f"    Billed: ${item['price']:.2f}")
            print(f"    Expected: ${item['expected_cost']:.2f}")
            print(f"    Overcharge Flag: {item['overcharge_flag']}")
            print(f"    Flag Level: {item['flag_level']}")
            if item['issue']:
                print(f"    Issue: {item['issue']}")
        
        print("\n" + "=" * 60)
        print("SUMMARY STATISTICS")
        print("=" * 60)
        stats = result['summary_stats']
        print(f"Total Items: {stats['total_items']}")
        print(f"Total Billed: ${stats['total_billed']:.2f}")
        print(f"Total Expected: ${stats['total_expected']:.2f}")
        print(f"Potential Savings: ${stats['potential_savings']:.2f}")
        print(f"Flagged Items: {stats['flagged_items']}")
        
        print("\n" + "=" * 60)
        print("NEGOTIATION MATERIALS")
        print("=" * 60)
        
        print("\n--- EMAIL ---")
        print(result['negotiation']['email'])
        
        print("\n--- PHONE SCRIPT ---")
        print(result['negotiation']['phone_script'])
        
        print("\n--- SUMMARY ---")
        print(result['negotiation']['summary'])
        
        print("\n" + "=" * 60)
        print("Pipeline completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


def process_from_file(file_path: str):
    """Process a medical bill from a text file containing OCR output.
    
    Args:
        file_path: Path to text file containing OCR text
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return
    
    logger.info(f"Reading OCR text from: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        ocr_text = f.read()
    
    result = process_medical_bill(ocr_text=ocr_text)
    
    # Print key results
    print("\n" + "=" * 60)
    print("PROCESSING RESULTS")
    print("=" * 60)
    print(f"\nExtracted {len(result['extraction'])} line items")
    print(f"Total Billed: ${result['summary_stats']['total_billed']:.2f}")
    print(f"Potential Savings: ${result['summary_stats']['potential_savings']:.2f}")
    print(f"\nEmail Preview:\n{result['negotiation']['email'][:200]}...")
    print(f"\nSummary:\n{result['negotiation']['summary']}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Process medical bills through LLM Agent Pipeline"
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Path to text file containing OCR output"
    )
    parser.add_argument(
        "--example",
        action="store_true",
        help="Run example usage with sample data"
    )
    
    args = parser.parse_args()
    
    if args.file:
        process_from_file(args.file)
    elif args.example:
        example_usage()
    else:
        # Default to example
        example_usage()

