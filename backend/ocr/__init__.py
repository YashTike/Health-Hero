"""OCR module for extracting text from PDFs and images."""

from backend.ocr.pipeline import OCRPipeline
from backend.ocr.base import OCRExtractor

__all__ = ["OCRPipeline", "OCRExtractor"]

