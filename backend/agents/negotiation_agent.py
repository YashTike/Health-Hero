"""Negotiation Agent: Generates negotiation materials from analysis results."""

import json
import logging
from typing import Dict, Any, Optional

from openai import OpenAI

from backend.config import get_openai_api_key

logger = logging.getLogger(__name__)


def negotiation_agent(
    analysis_items: list[Dict[str, Any]],
    api_key: Optional[str] = None,
    model: str = "gpt-4o",
    temperature: float = 0.7
) -> Dict[str, str]:
    """Generate negotiation materials from analyzed line items.
    
    Creates consumer-friendly negotiation materials including:
    - Professional email for disputing charges
    - Phone call script for speaking with billing department
    - Summary explanation for the consumer
    
    Args:
        analysis_items: List of enriched line items from Analysis Agent
        api_key: OpenAI API key. If None, uses OPENAI_API_KEY env var.
        model: OpenAI model to use (default: "gpt-4o")
        temperature: Sampling temperature (default: 0.7 for creative output)
    
    Returns:
        Dictionary with:
        {
            "email": str,           # Professional dispute email
            "phone_script": str,    # Phone call talking points
            "summary": str          # Consumer-friendly explanation
        }
    
    Raises:
        ValueError: If API key is missing or generation fails
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
    
    # Filter items with issues for focus
    flagged_items = [item for item in analysis_items if item.get("overcharge_flag", False)]
    
    # Prepare summary data
    total_billed = sum(item.get("price", 0.0) * item.get("quantity", 1.0) for item in analysis_items)
    total_expected = sum(item.get("expected_cost", 0.0) * item.get("quantity", 1.0) for item in analysis_items)
    potential_savings = total_billed - total_expected
    
    # Prepare JSON for prompt
    analysis_json = json.dumps(analysis_items, indent=2)
    
    # Construct prompt
    system_prompt = """You are a medical billing advocate helping consumers dispute overcharges and negotiate medical bills.

Your task is to create three types of negotiation materials:
1. **Email**: A professional, polite email to send to the billing department
2. **Phone Script**: Clear talking points for a phone call with billing
3. **Summary**: A consumer-friendly explanation of what was found

Guidelines:
- Be professional and respectful, not confrontational
- Focus on specific line items with issues
- Reference codes, descriptions, and prices
- Suggest reasonable alternatives or corrections
- Include specific dollar amounts where relevant
- Make the summary easy to understand for non-medical professionals
- Keep phone script concise and actionable
- Email should be ready to send (include placeholders for personal info if needed)

Return ONLY valid JSON with keys: "email", "phone_script", "summary"."""

    user_prompt = f"""Based on the following medical bill analysis, create negotiation materials:

Total Billed: ${total_billed:,.2f}
Total Expected: ${total_expected:,.2f}
Potential Savings: ${potential_savings:,.2f}

Line Items Analysis:
{analysis_json}

Generate:
1. A professional email for disputing charges
2. A phone call script with key talking points
3. A consumer-friendly summary explaining the findings

Return JSON with "email", "phone_script", and "summary" keys."""

    try:
        logger.info("Calling Negotiation Agent...")
        
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
        logger.debug(f"Negotiation Agent raw response: {content}")
        
        # Parse JSON
        try:
            parsed = json.loads(content)
            
            # Extract the three required fields
            result = {
                "email": str(parsed.get("email", "")).strip(),
                "phone_script": str(parsed.get("phone_script", "")).strip(),
                "summary": str(parsed.get("summary", "")).strip()
            }
            
            # Validate that we got content
            if not result["email"] or not result["phone_script"] or not result["summary"]:
                logger.warning("Some negotiation materials may be missing")
            
            logger.info("Negotiation Agent generated materials successfully")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response content: {content}")
            raise ValueError(f"Invalid JSON response from Negotiation Agent: {e}")
    
    except Exception as e:
        logger.error(f"Negotiation Agent failed: {e}")
        raise

