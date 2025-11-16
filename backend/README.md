# Medical Bill Fighter - Backend OCR Module

This module provides OCR (Optical Character Recognition) functionality for extracting text from medical bills in PDF format. It supports both text-based PDFs and scanned/image-based PDFs.

## Features

- **Automatic Detection**: Tries text extraction first, falls back to OCR for scanned PDFs
- **Dual Input Support**: Accepts file paths or file-like objects (BytesIO)
- **Modular Design**: Easy to swap OCR libraries or extend functionality
- **Production Ready**: Comprehensive error handling and logging

## Installation

### 1. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Install Tesseract OCR

Tesseract is required for OCR functionality on scanned PDFs.

#### macOS
```bash
brew install tesseract
```

#### Ubuntu/Debian
```bash
sudo apt-get install tesseract-ocr
```

#### Windows
Download and install from: https://github.com/UB-Mannheim/tesseract/wiki

#### Verify Installation
```bash
tesseract --version
```

### 3. Install Poppler (for PDF to Image Conversion)

Poppler is required to convert PDF pages to images for OCR.

#### macOS
```bash
brew install poppler
```

#### Ubuntu/Debian
```bash
sudo apt-get install poppler-utils
```

#### Windows
Download from: https://github.com/oschwartz10612/poppler-windows/releases/
Add to PATH or specify path in code.

## Usage

### Basic Usage

```python
from backend.ocr.pipeline import OCRPipeline

# Initialize pipeline
pipeline = OCRPipeline()

# Extract from file path
result = pipeline.extract("path/to/medical_bill.pdf")
print(result["text"])  # Full text
print(result["pages"])  # List of page texts
print(result["method"])  # "text" or "ocr"

# Extract from file-like object
with open("medical_bill.pdf", "rb") as f:
    result = pipeline.extract(f)
```

### Return Format Options

```python
# Get structured result with pages
result = pipeline.extract("bill.pdf", return_pages=True)
# Returns: {"text": str, "pages": List[str], "method": str}

# Get just the text string
text = pipeline.extract("bill.pdf", return_pages=False)
# Returns: str
```

### Custom Tesseract Path

If Tesseract is not in your PATH, specify the path:

```python
pipeline = OCRPipeline(tesseract_cmd="/usr/local/bin/tesseract")
```

### Advanced: Using Individual Extractors

You can also use the extractors directly:

```python
from backend.ocr.pdf_extractor import TextPDFExtractor
from backend.ocr.image_ocr import ImageOCRExtractor

# Text extraction only
text_extractor = TextPDFExtractor()
pages = text_extractor.extract("bill.pdf")

# OCR only
ocr_extractor = ImageOCRExtractor()
pages = ocr_extractor.extract("bill.pdf")
```

## Architecture

The OCR module is organized into several components:

- **`base.py`**: Abstract base class defining the OCR interface
- **`pdf_extractor.py`**: Extracts text from text-based PDFs using pdfplumber
- **`image_ocr.py`**: Performs OCR on scanned PDFs using Tesseract
- **`pipeline.py`**: Main orchestrator that tries text extraction first, then OCR

## Error Handling

The pipeline handles various error scenarios:

- **File not found**: Raises `FileNotFoundError`
- **Invalid PDF**: Raises `ValueError` with descriptive message
- **Tesseract not installed**: Raises `ValueError` with installation instructions
- **Poppler not installed**: Raises `ValueError` when converting PDFs to images
- **Both methods fail**: Raises `ValueError` with details from both attempts

## Future Integration

This module is designed to integrate easily with FastAPI:

```python
from fastapi import FastAPI, UploadFile
from backend.ocr.pipeline import OCRPipeline

app = FastAPI()
pipeline = OCRPipeline()

@app.post("/extract")
async def extract_text(file: UploadFile):
    contents = await file.read()
    file_obj = BytesIO(contents)
    result = pipeline.extract(file_obj)
    return result
```

## Troubleshooting

### "Tesseract OCR is not installed"
- Install Tesseract (see Installation section above)
- Verify with `tesseract --version`
- If installed but not in PATH, use `tesseract_cmd` parameter

### "Failed to convert PDF to images"
- Install poppler-utils (see Installation section above)
- On Windows, ensure poppler is in PATH or update code to specify path

### Low OCR accuracy
- Ensure PDF images are high resolution
- Consider preprocessing images (not yet implemented)
- Check Tesseract language packs if processing non-English text

## Dependencies

- `pdfplumber`: Text extraction from PDFs
- `pytesseract`: Python wrapper for Tesseract OCR
- `Pillow`: Image processing
- `pdf2image`: PDF to image conversion
- `pypdf`: PDF handling utilities

