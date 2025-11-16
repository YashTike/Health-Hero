"""Example usage of the Two-Agent Debate System.

This file demonstrates how to use the debate system with medical bill data.
"""

import json
from typing import List, Dict, Any

from backend.agents.debate import DebateManager, generate_debate_summary


def example_usage():
    """Example: Run a debate on sample bill data."""
    
    # Sample bill JSON structure (this would come from analysis_agent output)
    # This matches the structure produced by the analysis pipeline
    sample_bill_json: List[Dict[str, Any]] = [
        {
            "code": "99213",
            "description": "Office visit, established patient",
            "quantity": 1.0,
            "price": 350.0,
            "notes": None,
            "expected_cost": 180.0,
            "overcharge_flag": True,
            "flag_level": "high",
            "issue": "Price is 94% above expected market rate for CPT 99213"
        },
        {
            "code": "36415",
            "description": "Venipuncture for collection",
            "quantity": 1.0,
            "price": 125.0,
            "notes": None,
            "expected_cost": 25.0,
            "overcharge_flag": True,
            "flag_level": "high",
            "issue": "Price is 400% above typical venipuncture charge"
        },
        {
            "code": "80053",
            "description": "Comprehensive metabolic panel",
            "quantity": 1.0,
            "price": 150.0,
            "notes": None,
            "expected_cost": 120.0,
            "overcharge_flag": True,
            "flag_level": "low",
            "issue": "Price is 25% above expected, but within reasonable range"
        },
        {
            "code": "85027",
            "description": "Complete blood count (CBC)",
            "quantity": 1.0,
            "price": 75.0,
            "notes": None,
            "expected_cost": 65.0,
            "overcharge_flag": False,
            "flag_level": "low",
            "issue": None
        }
    ]
    
    # Initialize Debate Manager
    print("=" * 80)
    print("Medical Bill Debate System - Example Usage")
    print("=" * 80)
    print()
    
    debate_manager = DebateManager(
        model="gpt-4o",
        temperature=0.8,
        max_rounds=3
    )
    
    # Run the debate
    print("Running debate with 3 rounds...")
    print()
    
    transcript = debate_manager.run_debate(
        bill_json=sample_bill_json,
        num_rounds=3
    )
    
    # Display the transcript
    print("=" * 80)
    print("DEBATE TRANSCRIPT")
    print("=" * 80)
    print()
    
    for i, message in enumerate(transcript, 1):
        role = message["role"].upper()
        content = message["content"]
        print(f"[{role}] (Message {i})")
        print("-" * 80)
        print(content)
        print()
    
    # Generate summary
    print("=" * 80)
    print("DEBATE SUMMARY")
    print("=" * 80)
    print()
    
    summary = generate_debate_summary(
        bill_json=sample_bill_json,
        debate_transcript=transcript
    )
    
    print("Patient Arguments Summary:")
    print("-" * 80)
    print(summary["patient_arguments"])
    print()
    
    print("Hospital Arguments Summary:")
    print("-" * 80)
    print(summary["hospital_arguments"])
    print()
    
    print("Recommendation for Negotiation:")
    print("-" * 80)
    print(summary["recommendation"])
    print()
    
    # Save to file (optional)
    output = {
        "bill_data": sample_bill_json,
        "debate_transcript": transcript,
        "summary": summary
    }
    
    with open("debate_output.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print("Full output saved to debate_output.json")
    print()


def integration_example():
    """Example: Integrating debate system into the existing pipeline."""
    
    print("=" * 80)
    print("Integration Example: Adding Debate to Pipeline")
    print("=" * 80)
    print()
    
    example_code = '''
from backend.agents.pipeline import process_medical_bill
from backend.agents.debate import DebateManager, generate_debate_summary

# Step 1: Run the existing OCR → extraction → analysis pipeline
result = process_medical_bill(ocr_text="...")

# Step 2: Extract the analyzed bill data (this is what we feed to the debate)
bill_json = result["analysis"]  # List of enriched line items

# Step 3: Run the debate
debate_manager = DebateManager(max_rounds=3)
transcript = debate_manager.run_debate(bill_json=bill_json, num_rounds=3)

# Step 4: Generate summary
summary = generate_debate_summary(
    bill_json=bill_json,
    debate_transcript=transcript
)

# Step 5: Add debate results to the pipeline output
result["debate"] = {
    "transcript": transcript,
    "summary": summary
}

print(f"Debate completed: {len(transcript)} messages")
print(f"Patient arguments: {summary['patient_arguments'][:100]}...")
'''
    
    print(example_code)
    print()


if __name__ == "__main__":
    # Uncomment to run the example (requires OpenAI API key)
    # example_usage()
    
    # Show integration example
    integration_example()

