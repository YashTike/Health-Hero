"""Main pipeline orchestrator for medical bill processing."""

import logging
from typing import Dict, Any, Optional, List

# Import config to ensure .env is loaded
from backend.config import get_openai_api_key

from backend.agents.extraction_agent import extraction_agent
from backend.agents.analysis_agent import analysis_agent
from backend.agents.negotiation_agent import negotiation_agent

logger = logging.getLogger(__name__)


def process_medical_bill(
    ocr_text: str,
    api_key: Optional[str] = None,
    model: str = "gpt-4o",
    extraction_temperature: float = 0.1,
    analysis_temperature: float = 0.2,
    negotiation_temperature: float = 0.7
) -> Dict[str, Any]:
    """Process a medical bill through the complete LLM agent pipeline.
    
    This is the main entry point for processing medical bills. It orchestrates
    three agents:
    1. Extraction Agent: Converts OCR text to structured line items
    2. Analysis Agent: Analyzes items for overcharges and issues
    3. Negotiation Agent: Generates negotiation materials
    
    Args:
        ocr_text: Raw text extracted from OCR pipeline
        api_key: OpenAI API key. If None, uses OPENAI_API_KEY env var.
        model: OpenAI model to use for all agents (default: "gpt-4o")
        extraction_temperature: Temperature for extraction agent (default: 0.1)
        analysis_temperature: Temperature for analysis agent (default: 0.2)
        negotiation_temperature: Temperature for negotiation agent (default: 0.7)
    
    Returns:
        Dictionary with complete processing results:
        {
            "extraction": [
                {
                    "code": str,
                    "description": str,
                    "quantity": float,
                    "price": float,
                    "notes": Optional[str]
                },
                ...
            ],
            "analysis": [
                {
                    "code": str,
                    "description": str,
                    "quantity": float,
                    "price": float,
                    "notes": Optional[str],
                    "expected_cost": float,
                    "overcharge_flag": bool,
                    "flag_level": str,
                    "issue": Optional[str]
                },
                ...
            ],
            "negotiation": {
                "email": str,
                "phone_script": str,
                "summary": str
            },
            "summary_stats": {
                "total_items": int,
                "total_billed": float,
                "total_expected": float,
                "potential_savings": float,
                "flagged_items": int
            }
        }
    
    Raises:
        ValueError: If API key is missing or processing fails
        Exception: If any agent fails
    """
    logger.info("Starting medical bill processing pipeline...")
    
    # Step 1: Extraction Agent
    logger.info("Step 1/3: Running Extraction Agent...")
    line_items = extraction_agent(
        ocr_text=ocr_text,
        api_key=api_key,
        model=model,
        temperature=extraction_temperature
    )
    
    if not line_items:
        logger.warning("No line items extracted. Continuing with empty list...")
    
    # Step 2: Analysis Agent
    logger.info("Step 2/3: Running Analysis Agent...")
    if line_items:
        analysis_items = analysis_agent(
            line_items=line_items,
            api_key=api_key,
            model=model,
            temperature=analysis_temperature
        )
    else:
        # If no items extracted, create empty analysis
        analysis_items = []
    
    # Step 3: Negotiation Agent
    logger.info("Step 3/3: Running Negotiation Agent...")
    if analysis_items:
        negotiation_materials = negotiation_agent(
            analysis_items=analysis_items,
            api_key=api_key,
            model=model,
            temperature=negotiation_temperature
        )
    else:
        # If no items, create placeholder materials
        negotiation_materials = {
            "email": "No line items were extracted from this bill. Please review the document manually.",
            "phone_script": "No specific issues were identified. Please review the bill with the billing department.",
            "summary": "The bill could not be automatically processed. Please review it manually or try again with a clearer image/PDF."
        }
    
    # Calculate summary statistics
    total_billed = sum(item.get("price", 0.0) * item.get("quantity", 1.0) for item in analysis_items)
    total_expected = sum(item.get("expected_cost", 0.0) * item.get("quantity", 1.0) for item in analysis_items)
    flagged_items = sum(1 for item in analysis_items if item.get("overcharge_flag", False))
    
    summary_stats = {
        "total_items": len(analysis_items),
        "total_billed": round(total_billed, 2),
        "total_expected": round(total_expected, 2),
        "potential_savings": round(total_billed - total_expected, 2),
        "flagged_items": flagged_items
    }
    
    # Compile final result
    result = {
        "extraction": line_items,
        "analysis": analysis_items,
        "negotiation": negotiation_materials,
        "summary_stats": summary_stats
    }
    
    logger.info("Medical bill processing pipeline completed successfully")
    logger.info(f"Summary: {summary_stats['total_items']} items, "
                f"${summary_stats['potential_savings']:.2f} potential savings, "
                f"{summary_stats['flagged_items']} flagged items")
    
    return result

