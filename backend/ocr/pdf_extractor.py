"""Text-based PDF extraction using pdfplumber."""

import pdfplumber
from io import BytesIO
from pathlib import Path
from typing import Union, List

from backend.ocr.base import OCRExtractor


class TextPDFExtractor(OCRExtractor):
    """Extracts text from PDFs that contain embedded text.
    
    Uses pdfplumber to extract text directly from PDFs without OCR.
    This is faster and more accurate for text-based PDFs.
    """
    
    def extract(
        self, 
        file_input: Union[str, Path, BytesIO]
    ) -> List[str]:
        """Extract text from each page of a text-based PDF.
        
        Args:
            file_input: Either a file path (str or Path) or a file-like object (BytesIO)
            
        Returns:
            List of strings, one per page. Empty strings for pages with no text.
            
        Raises:
            FileNotFoundError: If file path doesn't exist
            ValueError: If file is not a valid PDF
            Exception: Other extraction errors
        """
        pages_text = []
        
        try:
            # Handle file path vs file-like object
            if isinstance(file_input, (str, Path)):
                file_path = Path(file_input)
                if not file_path.exists():
                    raise FileNotFoundError(f"PDF file not found: {file_path}")
                pdf_file = file_path
            else:
                # BytesIO or similar file-like object
                pdf_file = file_input
                # Reset position in case it was read before
                if hasattr(pdf_file, 'seek'):
                    pdf_file.seek(0)
            
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    try:
                        page_text = page.extract_text()
                        # Handle None (no text on page) or empty strings
                        pages_text.append(page_text if page_text else "")
                    except Exception as e:
                        # If extraction fails for a page, add empty string and continue
                        pages_text.append("")
                        continue
        
        except FileNotFoundError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF: {str(e)}") from e
        
        return pages_text

