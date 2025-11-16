"""Two-Agent Debate System: Medical Bill Fighter vs. Hospital Agent.

This module implements a debate system where two AI agents argue over medical bill charges:
- MedicalBillFighterAgent: Patient advocate focused on identifying overcharges
- MedicalHospitalAgent: Billing department representative defending charges
- DebateManager: Orchestrates the debate rounds
"""

import json
import logging
from typing import List, Dict, Any, Optional

from openai import OpenAI

from backend.config import get_openai_api_key

logger = logging.getLogger(__name__)


class MedicalBillFighterAgent:
    """Patient advocate agent that identifies inflated charges and advocates for reductions."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        temperature: float = 0.8
    ):
        """Initialize the Medical Bill Fighter Agent.
        
        Args:
            api_key: OpenAI API key. If None, uses OPENAI_API_KEY env var.
            model: OpenAI model to use (default: "gpt-4o")
            temperature: Sampling temperature (default: 0.8 for persuasive arguments)
        """
        if api_key is None:
            try:
                api_key = get_openai_api_key()
            except RuntimeError as e:
                raise ValueError(str(e)) from e
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        
        self.system_prompt = """You are a Medical Bill Fighter Agent—a patient advocate expert specializing in identifying inflated medical charges, duplicates, miscoding, and billing errors.

Your role is to:
- Advocate for the patient by identifying problematic charges
- Point out overcharges compared to typical market rates
- Identify duplicate charges or suspicious billing codes
- Highlight items that seem inflated, incorrectly coded, or unjustified
- Push for reductions and corrections on behalf of the patient
- Reference specific line items, codes, prices, and comparisons to market rates

Communication style:
- Professional but firm
- Evidence-based arguments using the bill data
- Focus on specific discrepancies and overcharges
- Reference CPT/HCPCS codes and typical pricing
- Be assertive but respectful

Your goal is to help the patient reduce their medical bill by identifying legitimate billing issues and advocating for fair pricing."""
    
    def generate_response(
        self,
        previous_message: Optional[str],
        bill_json: List[Dict[str, Any]],
        round_number: int = 1
    ) -> str:
        """Generate a response in the debate.
        
        Args:
            previous_message: The previous message from the opponent (None for opening statement)
            bill_json: The structured bill data (list of enriched line items)
            round_number: Current debate round number (1, 2, 3, etc.)
        
        Returns:
            The agent's response as a string
        
        Raises:
            ValueError: If API key is missing or generation fails
            Exception: If OpenAI API call fails
        """
        # Calculate summary statistics for context
        total_billed = sum(item.get("price", 0.0) * item.get("quantity", 1.0) for item in bill_json)
        total_expected = sum(item.get("expected_cost", 0.0) * item.get("quantity", 1.0) for item in bill_json)
        flagged_items = [item for item in bill_json if item.get("overcharge_flag", False)]
        
        # Prepare bill data as JSON string
        bill_json_str = json.dumps(bill_json, indent=2)
        
        # Construct user prompt based on whether this is an opening or response
        if previous_message is None:
            # Opening statement
            user_prompt = f"""You are starting the debate. This is Round {round_number}—your opening argument.

Analyze the following medical bill data and present the strongest patient-side arguments:

Bill Summary:
- Total Billed: ${total_billed:,.2f}
- Expected Market Rate: ${total_expected:,.2f}
- Potential Overcharge: ${total_billed - total_expected:,.2f}
- Items Flagged: {len(flagged_items)} out of {len(bill_json)}

Structured Bill Data:
{bill_json_str}

Present your opening argument identifying:
1. The most egregious overcharges
2. Duplicate or suspicious charges
3. Items that appear miscoded or inflated
4. Specific evidence from the bill data

Be concise, evidence-based, and focus on the strongest patient-side arguments. Keep your response to ~75 words."""
        else:
            # Response to opponent
            user_prompt = f"""You are responding in Round {round_number}. The hospital representative just said:

"{previous_message}"

Rebuttal Guidelines:
- Address their specific points if they are incorrect
- Reinforce your strongest evidence from the bill
- Highlight any issues they ignored or dismissed
- Maintain focus on the patient's perspective

Bill Summary:
- Total Billed: ${total_billed:,.2f}
- Expected Market Rate: ${total_expected:,.2f}
- Potential Overcharge: ${total_billed - total_expected:,.2f}
- Items Flagged: {len(flagged_items)} out of {len(bill_json)}

Structured Bill Data:
{bill_json_str}

Provide a concise rebuttal (~75 words) that counters their arguments and reinforces the patient's position."""
        
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature
            )
            
            content = response.choices[0].message.content
            logger.debug(f"Fighter Agent Round {round_number} response generated ({len(content)} chars)")
            return content.strip()
        
        except Exception as e:
            logger.error(f"Fighter Agent failed in round {round_number}: {e}")
            raise


class MedicalHospitalAgent:
    """Billing department representative agent that defends the medical bill charges."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        temperature: float = 0.8
    ):
        """Initialize the Medical Hospital Agent.
        
        Args:
            api_key: OpenAI API key. If None, uses OPENAI_API_KEY env var.
            model: OpenAI model to use (default: "gpt-4o")
            temperature: Sampling temperature (default: 0.8 for persuasive arguments)
        """
        if api_key is None:
            try:
                api_key = get_openai_api_key()
            except RuntimeError as e:
                raise ValueError(str(e)) from e
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        
        self.system_prompt = """You are a Medical Hospital Agent—a billing department representative defending the medical bill charges.

Your role is to:
- Defend the charges on the bill as justified and standard
- Explain that pricing reflects quality of care, facility overhead, and regulatory requirements
- Address concerns about overcharges by explaining market variations, regional differences, and service quality
- Defend billing codes as appropriate and correctly applied
- Explain that costs are based on industry standards, provider expertise, and facility costs
- Maintain that the bill is fair and accurately represents services rendered

Communication style:
- Professional and courteous
- Educational about billing practices
- Reference industry standards, facility costs, and quality of care
- Acknowledge patient concerns while defending charges
- Be respectful but firm in defending the billing accuracy

Your goal is to defend the medical bill and explain why the charges are justified, standard, and appropriate."""
    
    def generate_response(
        self,
        previous_message: Optional[str],
        bill_json: List[Dict[str, Any]],
        round_number: int = 1
    ) -> str:
        """Generate a response in the debate.
        
        Args:
            previous_message: The previous message from the opponent (None for opening statement)
            bill_json: The structured bill data (list of enriched line items)
            round_number: Current debate round number (1, 2, 3, etc.)
        
        Returns:
            The agent's response as a string
        
        Raises:
            ValueError: If API key is missing or generation fails
            Exception: If OpenAI API call fails
        """
        # Calculate summary statistics for context
        total_billed = sum(item.get("price", 0.0) * item.get("quantity", 1.0) for item in bill_json)
        total_expected = sum(item.get("expected_cost", 0.0) * item.get("quantity", 1.0) for item in bill_json)
        flagged_items = [item for item in bill_json if item.get("overcharge_flag", False)]
        
        # Prepare bill data as JSON string
        bill_json_str = json.dumps(bill_json, indent=2)
        
        # Construct user prompt based on whether this is an opening or response
        if previous_message is None:
            # Opening statement (should not happen for hospital - they always respond)
            # But handle it gracefully
            user_prompt = f"""You are responding in Round {round_number}. This is unusual, but you are providing your opening statement.


Bill Summary:
- Total Billed: ${total_billed:,.2f}
- Expected Market Rate (claimed): ${total_expected:,.2f}
- Items Disputed: {len(flagged_items)} out of {len(bill_json)}

Structured Bill Data:
{bill_json_str}

Defend the bill by:
1. Explaining why the charges are justified and standard
2. Highlighting quality of care, facility costs, and industry standards
3. Providing context for pricing variations
4. Emphasizing that the bill reflects fair market pricing

Be concise, professional, and defend the bill fairly. Keep your response to 200-300 words."""
        else:
            # Response to opponent's argument (normal case)
            user_prompt = f"""You are responding in Round {round_number}. The patient advocate just presented their argument:

"{previous_message}"

Defend the bill by:
- Address their specific counterarguments
- Reinforce why charges are justified
- Explain market variations, quality of care factors, and facility costs
- Maintain that the bill is accurate and fair
- Stay professional and respectful

Bill Summary:
- Total Billed: ${total_billed:,.2f}
- Expected Market Rate (claimed): ${total_expected:,.2f}
- Items Disputed: {len(flagged_items)} out of {len(bill_json)}

Structured Bill Data:
{bill_json_str}

Provide a concise rebuttal (75-100 words) that defends the bill and counters their arguments."""
        
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature
            )
            
            content = response.choices[0].message.content
            logger.debug(f"Hospital Agent Round {round_number} response generated ({len(content)} chars)")
            return content.strip()
        
        except Exception as e:
            logger.error(f"Hospital Agent failed in round {round_number}: {e}")
            raise


class DebateManager:
    """Orchestrates the debate between Medical Bill Fighter and Hospital Agent."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        temperature: float = 0.8,
        max_rounds: int = 10
    ):
        """Initialize the Debate Manager.
        
        Args:
            api_key: OpenAI API key. If None, uses OPENAI_API_KEY env var.
            model: OpenAI model to use for both agents (default: "gpt-4o")
            temperature: Sampling temperature for both agents (default: 0.8)
            max_rounds: Maximum number of debate rounds (default: 3)
        """
        self.fighter_agent = MedicalBillFighterAgent(api_key=api_key, model=model, temperature=temperature)
        self.hospital_agent = MedicalHospitalAgent(api_key=api_key, model=model, temperature=temperature)
        self.max_rounds = max_rounds
    
    def run_debate(
        self,
        bill_json: List[Dict[str, Any]],
        num_rounds: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """Run the debate between the two agents.
        
        The debate flow:
        1. Fighter opens with arguments (Round 1)
        2. Hospital responds (Round 1)
        3. Fighter rebuts (Round 2)
        4. Hospital final response (Round 2) [if num_rounds >= 2]
        5. Optional final round if num_rounds >= 3
        
        Args:
            bill_json: Structured bill data (list of enriched line items from analysis agent)
            num_rounds: Number of rounds to run (default: self.max_rounds). 
                       Each round = 2 messages (fighter + hospital)
        
        Returns:
            List of debate messages, each as:
            [
                {"role": "fighter", "content": "..."},
                {"role": "hospital", "content": "..."},
                {"role": "fighter", "content": "..."},
                ...
            ]
        
        Raises:
            ValueError: If bill_json is empty or invalid
            Exception: If debate execution fails
        """
        if not bill_json or not isinstance(bill_json, list):
            raise ValueError("bill_json must be a non-empty list of line items")
        
        num_rounds = num_rounds if num_rounds is not None else self.max_rounds
        num_rounds = max(1, min(num_rounds, self.max_rounds))  # Clamp between 1 and max_rounds
        
        logger.info(f"Starting debate with {num_rounds} rounds on {len(bill_json)} line items...")
        
        transcript = []
        previous_message = None
        
        # Round 1: Fighter opens, Hospital responds
        logger.info("Round 1: Fighter opening argument...")
        fighter_msg = self.fighter_agent.generate_response(
            previous_message=None,
            bill_json=bill_json,
            round_number=1
        )
        transcript.append({"role": "fighter", "content": fighter_msg})
        previous_message = fighter_msg
        
        logger.info("Round 1: Hospital response...")
        hospital_msg = self.hospital_agent.generate_response(
            previous_message=previous_message,
            bill_json=bill_json,
            round_number=1
        )
        transcript.append({"role": "hospital", "content": hospital_msg})
        previous_message = hospital_msg
        
        # Round 2: Fighter rebuts, Hospital responds (if num_rounds >= 2)
        if num_rounds >= 2:
            logger.info("Round 2: Fighter rebuttal...")
            fighter_msg = self.fighter_agent.generate_response(
                previous_message=previous_message,
                bill_json=bill_json,
                round_number=2
            )
            transcript.append({"role": "fighter", "content": fighter_msg})
            previous_message = fighter_msg
            
            logger.info("Round 2: Hospital response...")
            hospital_msg = self.hospital_agent.generate_response(
                previous_message=previous_message,
                bill_json=bill_json,
                round_number=2
            )
            transcript.append({"role": "hospital", "content": hospital_msg})
            previous_message = hospital_msg
        
        # Round 3: Optional final exchange (if num_rounds >= 3)
        if num_rounds >= 3:
            logger.info("Round 3: Fighter final statement...")
            fighter_msg = self.fighter_agent.generate_response(
                previous_message=previous_message,
                bill_json=bill_json,
                round_number=3
            )
            transcript.append({"role": "fighter", "content": fighter_msg})
            # Hospital gets final word in round 3
            previous_message = fighter_msg
            
            logger.info("Round 3: Hospital final response...")
            hospital_msg = self.hospital_agent.generate_response(
                previous_message=previous_message,
                bill_json=bill_json,
                round_number=3
            )
            transcript.append({"role": "hospital", "content": hospital_msg})
        
        logger.info(f"Debate completed with {len(transcript)} messages")
        return transcript


def generate_debate_summary(
    bill_json: List[Dict[str, Any]],
    debate_transcript: List[Dict[str, str]],
    api_key: Optional[str] = None,
    model: str = "gpt-4o",
    temperature: float = 0.3
) -> Dict[str, str]:
    """Generate a summary of the debate with key arguments and recommendations.
    
    Args:
        bill_json: Structured bill data (list of enriched line items)
        debate_transcript: List of debate messages from DebateManager.run_debate()
        api_key: OpenAI API key. If None, uses OPENAI_API_KEY env var.
        model: OpenAI model to use (default: "gpt-4o")
        temperature: Sampling temperature (default: 0.3 for focused summary)
    
    Returns:
        Dictionary with:
        {
            "patient_arguments": str,      # Summary of strongest patient-side arguments
            "hospital_arguments": str,     # Summary of hospital's defense
            "recommendation": str          # Final recommendation for negotiation materials
        }
    
    Raises:
        ValueError: If API key is missing or summary generation fails
        Exception: If OpenAI API call fails
    """
    if api_key is None:
        try:
            api_key = get_openai_api_key()
        except RuntimeError as e:
            raise ValueError(str(e)) from e
    
    client = OpenAI(api_key=api_key)
    
    # Calculate bill summary
    total_billed = sum(item.get("price", 0.0) * item.get("quantity", 1.0) for item in bill_json)
    total_expected = sum(item.get("expected_cost", 0.0) * item.get("quantity", 1.0) for item in bill_json)
    flagged_items = [item for item in bill_json if item.get("overcharge_flag", False)]
    
    # Format debate transcript
    debate_text = "\n\n".join([
        f"[{msg['role'].upper()}] {msg['content']}" 
        for msg in debate_transcript
    ])
    
    system_prompt = """You are an expert medical billing analyst summarizing a debate between a patient advocate and a hospital billing representative.

Your task is to:
1. Extract the strongest patient-side arguments for reducing the bill
2. Extract the hospital's key defense points
3. Provide a final recommendation for negotiation materials

Be objective, concise, and focus on actionable insights for the patient."""
    
    user_prompt = f"""Summarize the following debate about a medical bill:

Bill Summary:
- Total Billed: ${total_billed:,.2f}
- Expected Market Rate: ${total_expected:,.2f}
- Potential Overcharge: ${total_billed - total_expected:,.2f}
- Items Flagged: {len(flagged_items)} out of {len(bill_json)}

Debate Transcript:
{debate_text}

Provide a JSON summary with three keys:
1. "patient_arguments": A concise summary (100-150 words) of the strongest patient-side arguments for reducing charges
2. "hospital_arguments": A concise summary (100-150 words) of the hospital's main defense points
3. "recommendation": A brief recommendation (100-150 words) for what the patient should focus on in actual negotiations with the billing department

Return ONLY valid JSON with these three keys."""
    
    try:
        logger.info("Generating debate summary...")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        logger.debug(f"Debate summary raw response: {content}")
        
        try:
            parsed = json.loads(content)
            
            result = {
                "patient_arguments": str(parsed.get("patient_arguments", "")).strip(),
                "hospital_arguments": str(parsed.get("hospital_arguments", "")).strip(),
                "recommendation": str(parsed.get("recommendation", "")).strip()
            }
            
            logger.info("Debate summary generated successfully")
            return result
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response content: {content}")
            raise ValueError(f"Invalid JSON response from debate summary: {e}")
    
    except Exception as e:
        logger.error(f"Debate summary generation failed: {e}")
        raise

