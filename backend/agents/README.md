# LLM Agent Pipeline - Medical Bill Processing

This module provides an LLM-powered pipeline for processing medical bills after OCR extraction. It uses OpenAI's API to extract structured data, analyze for overcharges, and generate negotiation materials.

## Architecture

The pipeline consists of three sequential agents:

1. **Extraction Agent** (`extraction_agent.py`)
   - Converts raw OCR text into structured line items
   - Identifies CPT/HCPCS/ICD codes, descriptions, quantities, and prices
   - Handles noisy or poorly extracted text

2. **Analysis Agent** (`analysis_agent.py`)
   - Analyzes line items for cost anomalies
   - Flags overcharges, duplicates, and unusual codes
   - Estimates expected costs and assigns severity levels

3. **Negotiation Agent** (`negotiation_agent.py`)
   - Generates consumer-friendly negotiation materials
   - Creates professional dispute emails
   - Provides phone call scripts and summaries

## Installation

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This will install the OpenAI SDK along with other dependencies.

### 2. Set OpenAI API Key

```bash
export OPENAI_API_KEY='your-api-key-here'
```

Or set it in your environment before running the code.

## Usage

### Basic Usage

```python
from backend.agents.pipeline import process_medical_bill

# Process OCR text from your OCR pipeline
ocr_text = "..."  # Raw text from OCRPipeline.extract()

result = process_medical_bill(ocr_text=ocr_text)

# Access results
print(f"Extracted {len(result['extraction'])} line items")
print(f"Potential savings: ${result['summary_stats']['potential_savings']:.2f}")
print(result['negotiation']['email'])
print(result['negotiation']['phone_script'])
print(result['negotiation']['summary'])
```

### Complete Integration Example

```python
from backend.ocr.pipeline import OCRPipeline
from backend.agents.pipeline import process_medical_bill

# Step 1: Extract text from PDF
ocr_pipeline = OCRPipeline()
ocr_result = ocr_pipeline.extract("medical_bill.pdf", return_pages=False)
ocr_text = ocr_result  # or ocr_result["text"] if return_pages=True

# Step 2: Process through LLM agents
result = process_medical_bill(ocr_text=ocr_text)

# Step 3: Use results
for item in result['analysis']:
    if item['overcharge_flag']:
        print(f"⚠️  {item['code']}: {item['description']}")
        print(f"   Billed: ${item['price']:.2f}, Expected: ${item['expected_cost']:.2f}")
        print(f"   Issue: {item['issue']}")
```

### Command Line Usage

Run the example:

```bash
cd backend
python -m agents.main --example
```

Process from a text file:

```bash
python -m agents.main --file path/to/ocr_output.txt
```

## API Reference

### `process_medical_bill(ocr_text, ...)`

Main pipeline function that orchestrates all three agents.

**Parameters:**
- `ocr_text` (str): Raw text from OCR extraction
- `api_key` (str, optional): OpenAI API key (defaults to `OPENAI_API_KEY` env var)
- `model` (str): OpenAI model to use (default: `"gpt-4o"`)
- `extraction_temperature` (float): Temperature for extraction (default: `0.1`)
- `analysis_temperature` (float): Temperature for analysis (default: `0.2`)
- `negotiation_temperature` (float): Temperature for negotiation (default: `0.7`)

**Returns:**
```python
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
            "flag_level": str,  # "low", "medium", or "high"
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
```

### Individual Agents

You can also use agents individually:

```python
from backend.agents.extraction_agent import extraction_agent
from backend.agents.analysis_agent import analysis_agent
from backend.agents.negotiation_agent import negotiation_agent

# Step 1: Extract
line_items = extraction_agent(ocr_text="...")

# Step 2: Analyze
analysis_items = analysis_agent(line_items=line_items)

# Step 3: Generate negotiation materials
negotiation = negotiation_agent(analysis_items=analysis_items)
```

## FastAPI Integration

Here's how to integrate into a FastAPI backend:

```python
from fastapi import FastAPI, UploadFile, HTTPException
from backend.ocr.pipeline import OCRPipeline
from backend.agents.pipeline import process_medical_bill
from io import BytesIO

app = FastAPI()
ocr_pipeline = OCRPipeline()

@app.post("/process-bill")
async def process_bill(file: UploadFile):
    """Process a medical bill PDF through OCR and LLM pipeline."""
    try:
        # Read file
        contents = await file.read()
        file_obj = BytesIO(contents)
        
        # Extract text
        ocr_text = ocr_pipeline.extract(file_obj, return_pages=False)
        
        # Process through LLM agents
        result = process_medical_bill(ocr_text=ocr_text)
        
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Error Handling

The pipeline handles various error scenarios:

- **Missing API Key**: Raises `ValueError` with clear message
- **Invalid JSON Response**: Logs error and raises `ValueError`
- **API Failures**: Logs error and re-raises exception
- **Empty Extraction**: Continues with empty list and placeholder negotiation materials

## Configuration

### Model Selection

Default model is `gpt-4o`. You can use other models:

```python
result = process_medical_bill(
    ocr_text=ocr_text,
    model="gpt-4-turbo"  # or "gpt-3.5-turbo" for faster/cheaper
)
```

### Temperature Tuning

Adjust temperatures for different use cases:

- **Extraction** (default: 0.1): Low temperature for consistent, accurate extraction
- **Analysis** (default: 0.2): Slightly higher for nuanced analysis
- **Negotiation** (default: 0.7): Higher for creative, varied negotiation materials

```python
result = process_medical_bill(
    ocr_text=ocr_text,
    extraction_temperature=0.0,  # More deterministic
    analysis_temperature=0.3,    # More creative analysis
    negotiation_temperature=0.8   # More varied writing
)
```

## Cost Considerations

Each bill processing makes 3 API calls:
1. Extraction Agent: ~1-2k tokens input, ~500-2k tokens output
2. Analysis Agent: ~2-5k tokens input, ~1-3k tokens output
3. Negotiation Agent: ~3-6k tokens input, ~1-2k tokens output

**Estimated cost per bill** (using gpt-4o):
- Small bill (5-10 items): ~$0.10-0.20
- Medium bill (10-20 items): ~$0.20-0.40
- Large bill (20+ items): ~$0.40-0.80

## Troubleshooting

### "OpenAI API key required"
- Set `OPENAI_API_KEY` environment variable
- Or pass `api_key` parameter to functions

### "Invalid JSON response"
- Usually indicates model confusion or malformed prompt
- Check logs for raw response
- Try lowering temperature
- Verify OCR text quality

### Low extraction accuracy
- Ensure OCR text is reasonably clean
- Check that bill format is standard
- Consider preprocessing OCR text before extraction

### Analysis not flagging obvious issues
- Adjust `analysis_temperature` slightly higher
- Review prompt in `analysis_agent.py`
- Check that expected costs are reasonable

## Future Enhancements

Potential improvements:
- Caching for repeated analyses
- Batch processing for multiple bills
- Custom heuristics in Analysis Agent
- Multi-language support
- Integration with medical code databases
- Cost database lookups for more accurate expected costs

