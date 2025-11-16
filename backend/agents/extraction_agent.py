"""Extraction Agent: Converts raw OCR text into structured line items."""

import json
import logging
from typing import List, Dict, Any, Optional

from openai import OpenAI

from backend.config import get_openai_api_key

logger = logging.getLogger(__name__)


def extraction_agent(
    ocr_text: str,
    api_key: Optional[str] = None,
    model: str = "gpt-4o",
    temperature: float = 0.1
) -> List[Dict[str, Any]]:
    """Extract structured line items from raw OCR text.
    
    This agent identifies CPT/HCPCS/ICD codes, descriptions, quantities,
    prices, and notes from medical bill text. It handles noisy or poorly
    extracted text by inferring structure where possible.
    
    Args:
        ocr_text: Raw text extracted from OCR pipeline
        api_key: OpenAI API key. If None, uses OPENAI_API_KEY env var.
        model: OpenAI model to use (default: "gpt-4o")
        temperature: Sampling temperature (default: 0.1 for deterministic output)
    
    Returns:
        List of dictionaries, each representing a line item:
        [
            {
                "code": str,           # CPT/HCPCS/ICD code (e.g., "99213", "J3420")
                "description": str,    # Service/item description
                "quantity": float,     # Quantity (default: 1.0)
                "price": float,        # Unit price or total price
                "notes": Optional[str] # Additional notes or null
            },
            ...
        ]
    
    Raises:
        ValueError: If API key is missing or extraction fails
        Exception: If OpenAI API call fails
    """
    # Get API key
    if api_key is None:
        try:
            api_key = get_openai_api_key()
        except RuntimeError as e:
            raise ValueError(str(e)) from e
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Construct prompt
    system_prompt = """You are a medical billing expert specializing in extracting structured data from medical bills.

Your task is to extract line items from medical bill text, even if the text is noisy, poorly formatted, or incomplete.

For each line item, identify:
1. **Code**: CPT, HCPCS, or ICD codes (e.g., "99213", "J3420", "E11.9")
2. **Description**: The service or item description
3. **Quantity**: Number of units (default to 1.0 if not specified)
4. **Price**: Unit price or total price for the line item
5. **Notes**: Any additional relevant information, or null if none

Guidelines:
- Extract ALL line items you can identify, even if some fields are missing
- If a code is not explicitly shown, try to infer it from the description
- If quantity is not specified, default to 1.0
- If price is ambiguous, use your best judgment based on context
- Handle common OCR errors (e.g., "O" vs "0", "I" vs "1")
- Return an empty list if no line items can be extracted

Return a JSON object with a "line_items" key containing an array of line items. No additional text or markdown formatting."""

    user_prompt = f"""Extract all line items from the following medical bill text:

{ocr_text}

Return a JSON object with this structure:
{{
  "line_items": [
    {{"code": "...", "description": "...", "quantity": 1.0, "price": 0.0, "notes": null}},
    ...
  ]
}}"""

    try:
        logger.info("Calling Extraction Agent...")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            response_format={"type": "json_object"}  # Force JSON output
        )
        
        # Parse response
        content = response.choices[0].message.content
        logger.debug(f"Extraction Agent raw response: {content}")
        
        # Parse JSON - handle both direct array and wrapped object
        try:
            parsed = json.loads(content)
            # Handle case where response is wrapped in an object
            if isinstance(parsed, dict):
                # Look for common keys that might contain the array
                if "line_items" in parsed:
                    line_items = parsed["line_items"]
                elif "items" in parsed:
                    line_items = parsed["items"]
                elif len(parsed) == 1:
                    # Single key, assume it's the array
                    line_items = list(parsed.values())[0]
                else:
                    # Try to find array value
                    line_items = next((v for v in parsed.values() if isinstance(v, list)), [])
            else:
                line_items = parsed
            
            # Ensure it's a list
            if not isinstance(line_items, list):
                raise ValueError("Response is not a list")
            
            # Validate and normalize structure
            normalized_items = []
            for item in line_items:
                if not isinstance(item, dict):
                    continue
                
                normalized = {
                    "code": str(item.get("code", "")).strip(),
                    "description": str(item.get("description", "")).strip(),
                    "quantity": float(item.get("quantity", 1.0)),
                    "price": float(item.get("price", 0.0)),
                    "notes": item.get("notes") if item.get("notes") else None
                }
                normalized_items.append(normalized)
            
            logger.info(f"Extraction Agent extracted {len(normalized_items)} line items")
            return normalized_items
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response content: {content}")
            raise ValueError(f"Invalid JSON response from Extraction Agent: {e}")
    
    except Exception as e:
        logger.error(f"Extraction Agent failed: {e}")
        raise

