"""OCR extraction for scanned PDFs and images using Tesseract."""

import pytesseract
from pdf2image import convert_from_path, convert_from_bytes
from io import BytesIO
from pathlib import Path
from typing import Union, List
import logging

from backend.ocr.base import OCRExtractor

logger = logging.getLogger(__name__)


class ImageOCRExtractor(OCRExtractor):
    """Extracts text from scanned PDFs and images using OCR.
    
    Uses Tesseract OCR via pytesseract to extract text from image-based PDFs.
    Converts PDF pages to images first, then runs OCR on each image.
    """
    
    def __init__(self, tesseract_cmd: str = None):
        """Initialize the OCR extractor.
        
        Args:
            tesseract_cmd: Optional path to tesseract executable.
                          If None, uses system PATH.
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        else:
            # Try to detect tesseract installation
            try:
                pytesseract.get_tesseract_version()
            except Exception as e:
                logger.warning(
                    "Tesseract not found in PATH. "
                    "Please install Tesseract OCR or provide tesseract_cmd path. "
                    f"Error: {str(e)}"
                )
    
    def extract(
        self, 
        file_input: Union[str, Path, BytesIO]
    ) -> List[str]:
        """Extract text from scanned PDF or image using OCR.
        
        Args:
            file_input: Either a file path (str or Path) or a file-like object (BytesIO)
            
        Returns:
            List of strings, one per page. Empty strings for pages with no text.
            
        Raises:
            FileNotFoundError: If file path doesn't exist
            ValueError: If Tesseract is not installed or file format is not supported
            Exception: Other OCR errors
        """
        pages_text = []
        
        try:
            # Check if Tesseract is available
            try:
                pytesseract.get_tesseract_version()
            except Exception as e:
                raise ValueError(
                    "Tesseract OCR is not installed or not found in PATH. "
                    "Please install Tesseract OCR. "
                    "See README.md for installation instructions."
                ) from e
            
            # Handle file path vs file-like object
            if isinstance(file_input, (str, Path)):
                file_path = Path(file_input)
                if not file_path.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                # Convert PDF pages to images
                try:
                    images = convert_from_path(str(file_path))
                except Exception as e:
                    raise ValueError(
                        f"Failed to convert PDF to images. "
                        f"Make sure poppler-utils is installed. Error: {str(e)}"
                    ) from e
            else:
                # BytesIO or similar file-like object
                if hasattr(file_input, 'seek'):
                    file_input.seek(0)
                
                # Convert PDF pages to images from bytes
                try:
                    images = convert_from_bytes(file_input.read())
                except Exception as e:
                    raise ValueError(
                        f"Failed to convert PDF to images from bytes. "
                        f"Make sure poppler-utils is installed. Error: {str(e)}"
                    ) from e
            
            # Run OCR on each page
            for image in images:
                try:
                    page_text = pytesseract.image_to_string(image)
                    pages_text.append(page_text.strip() if page_text else "")
                except Exception as e:
                    logger.warning(f"OCR failed for a page: {str(e)}")
                    pages_text.append("")
                    continue
        
        except (FileNotFoundError, ValueError):
            raise
        except Exception as e:
            raise ValueError(f"Failed to perform OCR: {str(e)}") from e
        
        return pages_text

