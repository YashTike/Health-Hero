# Medical Bill Fighter - Architecture Overview

This document explains how the complete medical bill processing system fits together, from PDF/image input to negotiation materials output.

## System Flow

```
PDF/Image File
    ↓
[OCR Pipeline]
    ↓
Raw OCR Text
    ↓
[LLM Agent Pipeline]
    ├─→ Extraction Agent → Structured Line Items
    ├─→ Analysis Agent → Enriched Analysis
    └─→ Negotiation Agent → Negotiation Materials
    ↓
Final Results (JSON)
```

## Component Overview

### 1. OCR Module (`backend/ocr/`)

**Purpose**: Extract text from medical bill PDFs and images.

**Components**:
- `base.py`: Abstract interface for extractors
- `pdf_extractor.py`: Direct text extraction from text-based PDFs
- `image_ocr.py`: OCR extraction from scanned PDFs/images
- `pipeline.py`: Main orchestrator that tries text extraction first, then OCR

**Input**: PDF file path or BytesIO object
**Output**: Raw text string (or structured dict with pages)

**Key Features**:
- Automatic method detection (text vs OCR)
- Handles both file paths and file-like objects
- Production-ready error handling

### 2. LLM Agent Pipeline (`backend/agents/`)

**Purpose**: Process OCR text through AI agents to extract, analyze, and generate negotiation materials.

**Components**:
- `extraction_agent.py`: Converts OCR text to structured line items
- `analysis_agent.py`: Analyzes items for overcharges and issues
- `negotiation_agent.py`: Generates negotiation materials
- `pipeline.py`: Orchestrates all three agents
- `main.py`: Command-line entrypoint and examples

**Input**: Raw OCR text string
**Output**: Complete analysis with extraction, analysis, negotiation, and stats

**Key Features**:
- Modular agent design (can use individually)
- Configurable model and temperature
- Comprehensive error handling
- Production-ready for FastAPI integration

## Data Flow

### Step 1: OCR Extraction

```python
from backend.ocr.pipeline import OCRPipeline

pipeline = OCRPipeline()
ocr_result = pipeline.extract("bill.pdf", return_pages=False)
ocr_text = ocr_result  # Raw text string
```

**Output Format**: Plain text string containing all extracted text from the bill.

### Step 2: LLM Processing

```python
from backend.agents.pipeline import process_medical_bill

result = process_medical_bill(ocr_text=ocr_text)
```

**Output Format**: Structured dictionary with:
- `extraction`: List of line items (code, description, quantity, price, notes)
- `analysis`: Enriched line items (adds expected_cost, overcharge_flag, flag_level, issue)
- `negotiation`: Email, phone script, and summary
- `summary_stats`: Aggregated statistics

## Integration Architecture

### Standalone Usage

```python
# Complete pipeline
from backend.ocr.pipeline import OCRPipeline
from backend.agents.pipeline import process_medical_bill

ocr_pipeline = OCRPipeline()
ocr_text = ocr_pipeline.extract("bill.pdf", return_pages=False)
result = process_medical_bill(ocr_text=ocr_text)
```

### FastAPI Backend Integration

```python
from fastapi import FastAPI, UploadFile
from backend.ocr.pipeline import OCRPipeline
from backend.agents.pipeline import process_medical_bill
from io import BytesIO

app = FastAPI()
ocr_pipeline = OCRPipeline()

@app.post("/api/process-bill")
async def process_bill_endpoint(file: UploadFile):
    # Read uploaded file
    contents = await file.read()
    file_obj = BytesIO(contents)
    
    # OCR extraction
    ocr_text = ocr_pipeline.extract(file_obj, return_pages=False)
    
    # LLM processing
    result = process_medical_bill(ocr_text=ocr_text)
    
    return {
        "status": "success",
        "data": result
    }
```

### Frontend Integration

The frontend (Next.js) would:
1. Upload PDF/image file to FastAPI endpoint
2. Receive complete analysis results
3. Display:
   - Line items table with flags
   - Summary statistics
   - Negotiation materials (email, script, summary)
   - Download/export options

## Data Structures

### Extraction Output

```python
[
    {
        "code": "99213",                    # CPT/HCPCS/ICD code
        "description": "Office Visit",      # Service description
        "quantity": 1.0,                    # Number of units
        "price": 250.00,                    # Billed price
        "notes": null                       # Optional notes
    },
    ...
]
```

### Analysis Output

```python
[
    {
        # Original fields from extraction
        "code": "99213",
        "description": "Office Visit",
        "quantity": 1.0,
        "price": 250.00,
        "notes": null,
        
        # Analysis fields
        "expected_cost": 180.00,            # LLM-estimated reasonable cost
        "overcharge_flag": true,            # Is this overpriced?
        "flag_level": "medium",             # "low", "medium", or "high"
        "issue": "Price 39% above typical" # Explanation
    },
    ...
]
```

### Negotiation Output

```python
{
    "email": "Dear Billing Department,\n\n...",
    "phone_script": "1. Greet and state purpose\n2. Reference specific items...",
    "summary": "Your bill contains 3 items that may be overcharged..."
}
```

### Summary Statistics

```python
{
    "total_items": 5,
    "total_billed": 1225.00,
    "total_expected": 950.00,
    "potential_savings": 275.00,
    "flagged_items": 2
}
```

## Error Handling Strategy

### OCR Module
- **File not found**: Raises `FileNotFoundError`
- **Invalid PDF**: Raises `ValueError` with details
- **OCR failure**: Falls back to text extraction, or raises if both fail

### LLM Agents
- **Missing API key**: Raises `ValueError` with clear message
- **API failure**: Logs error and re-raises exception
- **Invalid JSON**: Logs raw response and raises `ValueError`
- **Empty extraction**: Continues with empty list and placeholder negotiation

### Pipeline Resilience
- Each agent can fail independently
- Pipeline continues with partial results when possible
- Comprehensive logging at each step

## Configuration

### Environment Variables

```bash
# Required
export OPENAI_API_KEY='your-api-key'

# Optional (for OCR)
export TESSERACT_CMD='/usr/local/bin/tesseract'  # If not in PATH
```

### Model Configuration

Default: `gpt-4o` (can be changed per call)

```python
result = process_medical_bill(
    ocr_text=ocr_text,
    model="gpt-4-turbo"  # Alternative model
)
```

### Temperature Tuning

- **Extraction**: 0.1 (deterministic, accurate)
- **Analysis**: 0.2 (balanced)
- **Negotiation**: 0.7 (creative, varied)

## Performance Considerations

### OCR Performance
- Text extraction: ~100-500ms per page
- OCR extraction: ~2-5 seconds per page
- Total: Usually <10 seconds for typical bills

### LLM Performance
- Extraction Agent: ~2-5 seconds
- Analysis Agent: ~3-8 seconds
- Negotiation Agent: ~3-6 seconds
- Total: ~8-19 seconds per bill

### Cost Estimates (gpt-4o)
- Small bill (5-10 items): ~$0.10-0.20
- Medium bill (10-20 items): ~$0.20-0.40
- Large bill (20+ items): ~$0.40-0.80

## Future Enhancements

### Short-term
- Caching for repeated analyses
- Batch processing endpoint
- More detailed cost database integration

### Medium-term
- Multi-language support
- Custom heuristics configuration
- Real-time processing status updates

### Long-term
- Machine learning model fine-tuning
- Historical data analysis
- Predictive overcharge detection
- Integration with insurance APIs

## Testing Strategy

### Unit Tests
- Individual agent functions
- JSON parsing and validation
- Error handling paths

### Integration Tests
- Full pipeline with sample bills
- OCR + LLM end-to-end
- FastAPI endpoint testing

### Sample Data
- Create test fixtures with known bills
- Expected outputs for validation
- Edge cases (empty bills, malformed text, etc.)

## Deployment Considerations

### Production Setup
1. Set `OPENAI_API_KEY` in environment
2. Install Tesseract and Poppler
3. Configure logging level
4. Set up error monitoring
5. Consider rate limiting for API calls

### Scaling
- Use async/await for concurrent processing
- Implement request queuing for high load
- Cache common analyses
- Consider batch API calls for multiple bills

### Security
- Never log API keys
- Validate file uploads (type, size)
- Sanitize OCR text before logging
- Rate limit endpoints

## Module Dependencies

```
backend/
├── ocr/              # OCR extraction (no LLM dependencies)
│   ├── base.py
│   ├── pdf_extractor.py
│   ├── image_ocr.py
│   └── pipeline.py
│
└── agents/           # LLM processing (depends on ocr output)
    ├── extraction_agent.py
    ├── analysis_agent.py
    ├── negotiation_agent.py
    ├── pipeline.py
    └── main.py
```

**Key Point**: The OCR module is independent and can be used standalone. The agents module depends on OCR output but not on OCR internals.

