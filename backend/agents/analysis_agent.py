"""Analysis Agent: Analyzes line items for overcharges, duplicates, and anomalies."""

import json
import logging
from typing import List, Dict, Any, Optional

from openai import OpenAI

from backend.config import get_openai_api_key

logger = logging.getLogger(__name__)


def analysis_agent(
    line_items: List[Dict[str, Any]],
    api_key: Optional[str] = None,
    model: str = "gpt-4o",
    temperature: float = 0.2
) -> List[Dict[str, Any]]:
    """Analyze line items for cost anomalies, overcharges, and issues.
    
    This agent enriches each line item with:
    - Expected cost estimate
    - Overcharge flag
    - Flag level (low/medium/high)
    - Issue explanation
    
    Args:
        line_items: List of line items from Extraction Agent
        api_key: OpenAI API key. If None, uses OPENAI_API_KEY env var.
        model: OpenAI model to use (default: "gpt-4o")
        temperature: Sampling temperature (default: 0.2)
    
    Returns:
        List of enriched line items, each with:
        [
            {
                "code": str,
                "description": str,
                "quantity": float,
                "price": float,
                "notes": Optional[str],
                "expected_cost": float,      # LLM-estimated average cost
                "overcharge_flag": bool,     # True if price seems excessive
                "flag_level": str,           # "low", "medium", or "high"
                "issue": Optional[str]       # Short explanation of issue, or null
            },
            ...
        ]
    
    Raises:
        ValueError: If API key is missing or analysis fails
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
    
    # Prepare line items JSON for prompt
    line_items_json = json.dumps(line_items, indent=2)
    
    # Construct prompt
    system_prompt = """You are a medical billing analyst expert at detecting overcharges, duplicates, and anomalies in medical bills.

Your task is to analyze each line item and determine:
1. **Expected Cost**: What is a reasonable/average cost for this service/item based on typical market rates?
2. **Overcharge Flag**: Is the billed price significantly higher than expected?
3. **Flag Level**: How severe is the issue? ("low", "medium", or "high")
4. **Issue**: A brief explanation of any problems detected (duplicates, unusual codes, excessive pricing, etc.)

Guidelines:
- Compare billed prices to typical market rates for the same service/code
- Flag potential duplicates (same code/description appearing multiple times)
- Identify unusual or suspicious codes
- Consider regional variations in pricing
- Flag items where price is >20% above expected as "medium", >50% as "high"
- If no issues found, set overcharge_flag to false, flag_level to "low", and issue to null
- Be conservative but thorough in your analysis

Return a JSON object with a "line_items" key containing the enriched array. No additional text."""

    user_prompt = f"""Analyze the following line items from a medical bill:

{line_items_json}

For each item, add:
- expected_cost: estimated reasonable cost
- overcharge_flag: boolean indicating if price seems excessive
- flag_level: "low", "medium", or "high"
- issue: brief explanation of any problems, or null if none

Return a JSON object with this structure:
{{
  "line_items": [
    {{"code": "...", "description": "...", "quantity": 1.0, "price": 0.0, "notes": null, "expected_cost": 0.0, "overcharge_flag": false, "flag_level": "low", "issue": null}},
    ...
  ]
}}"""

    try:
        logger.info(f"Calling Analysis Agent on {len(line_items)} line items...")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        content = response.choices[0].message.content
        logger.debug(f"Analysis Agent raw response: {content}")
        
        # Parse JSON
        try:
            parsed = json.loads(content)
            # Handle wrapped response
            if isinstance(parsed, dict):
                if "line_items" in parsed:
                    enriched_items = parsed["line_items"]
                elif "items" in parsed:
                    enriched_items = parsed["items"]
                elif "analysis" in parsed:
                    enriched_items = parsed["analysis"]
                elif len(parsed) == 1:
                    enriched_items = list(parsed.values())[0]
                else:
                    enriched_items = next((v for v in parsed.values() if isinstance(v, list)), [])
            else:
                enriched_items = parsed
            
            if not isinstance(enriched_items, list):
                raise ValueError("Response is not a list")
            
            # Validate and normalize structure
            normalized_items = []
            for item in enriched_items:
                if not isinstance(item, dict):
                    continue
                
                # Preserve original fields
                normalized = {
                    "code": str(item.get("code", "")).strip(),
                    "description": str(item.get("description", "")).strip(),
                    "quantity": float(item.get("quantity", 1.0)),
                    "price": float(item.get("price", 0.0)),
                    "notes": item.get("notes") if item.get("notes") else None,
                    # Analysis fields
                    "expected_cost": float(item.get("expected_cost", item.get("price", 0.0))),
                    "overcharge_flag": bool(item.get("overcharge_flag", False)),
                    "flag_level": str(item.get("flag_level", "low")).lower(),
                    "issue": item.get("issue") if item.get("issue") else None
                }
                
                # Validate flag_level
                if normalized["flag_level"] not in ["low", "medium", "high"]:
                    normalized["flag_level"] = "low"
                
                normalized_items.append(normalized)
            
            logger.info(f"Analysis Agent processed {len(normalized_items)} items")
            return normalized_items
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response content: {content}")
            raise ValueError(f"Invalid JSON response from Analysis Agent: {e}")
    
    except Exception as e:
        logger.error(f"Analysis Agent failed: {e}")
        raise

