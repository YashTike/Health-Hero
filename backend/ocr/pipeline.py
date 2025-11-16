"""Main OCR pipeline that orchestrates text extraction and OCR."""

import logging
from io import BytesIO
from pathlib import Path
from typing import Union, List, Dict

from backend.ocr.base import OCRExtractor
from backend.ocr.pdf_extractor import TextPDFExtractor
from backend.ocr.image_ocr import ImageOCRExtractor

logger = logging.getLogger(__name__)


class OCRPipeline:
    """Main OCR pipeline that automatically detects and extracts text from PDFs.
    
    This pipeline tries to extract text directly from PDFs first (for text-based PDFs).
    If that fails or yields minimal text, it falls back to OCR (for scanned PDFs).
    """
    
    def __init__(self, tesseract_cmd: str = None):
        """Initialize the OCR pipeline.
        
        Args:
            tesseract_cmd: Optional path to tesseract executable for OCR.
                          If None, uses system PATH.
        """
        self.text_extractor = TextPDFExtractor()
        self.ocr_extractor = ImageOCRExtractor(tesseract_cmd=tesseract_cmd)
    
    def extract(
        self, 
        file_input: Union[str, Path, BytesIO],
        return_pages: bool = True,
        min_text_threshold: int = 50
    ) -> Union[str, Dict[str, Union[str, List[str], str]]]:
        """Extract text from a PDF file.
        
        Automatically tries text extraction first, then falls back to OCR if needed.
        
        Args:
            file_input: Either a file path (str or Path) or a file-like object (BytesIO)
            return_pages: If True, returns dict with pages list. If False, returns just text string.
            min_text_threshold: Minimum characters per page to consider text extraction successful.
                               If total text is below this, falls back to OCR.
        
        Returns:
            If return_pages is True:
                Dict with keys:
                    - "text": Concatenated text from all pages
                    - "pages": List of page texts
                    - "method": "text" or "ocr" indicating which method was used
            If return_pages is False:
                Just the concatenated text string
                
        Raises:
            FileNotFoundError: If file path doesn't exist
            ValueError: If file format is not supported or extraction fails
        """
        # Try text extraction first
        try:
            logger.info("Attempting text extraction from PDF...")
            pages = self.text_extractor.extract(file_input)
            
            # Calculate total text length
            total_text = "".join(pages)
            total_length = len(total_text.strip())
            
            # Check if we got meaningful text
            if total_length >= min_text_threshold:
                logger.info(f"Text extraction successful ({total_length} characters)")
                method = "text"
            else:
                logger.info(
                    f"Text extraction yielded minimal text ({total_length} chars). "
                    "Falling back to OCR..."
                )
                # Fall back to OCR
                pages = self.ocr_extractor.extract(file_input)
                method = "ocr"
                logger.info("OCR extraction completed")
        
        except Exception as text_error:
            # If text extraction fails completely, try OCR
            logger.info(f"Text extraction failed: {str(text_error)}. Trying OCR...")
            try:
                pages = self.ocr_extractor.extract(file_input)
                method = "ocr"
                logger.info("OCR extraction completed")
            except Exception as ocr_error:
                # Both methods failed
                raise ValueError(
                    f"Both text extraction and OCR failed. "
                    f"Text extraction error: {str(text_error)}. "
                    f"OCR error: {str(ocr_error)}"
                ) from ocr_error
        
        # Prepare result
        text = "\n\n".join(pages)  # Join pages with double newline
        
        if return_pages:
            return {
                "text": text,
                "pages": pages,
                "method": method
            }
        else:
            return text

