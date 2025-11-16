"""Abstract base class for OCR extractors."""

from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path
from typing import Union, List


class OCRExtractor(ABC):
    """Abstract base class defining the interface for OCR extractors.
    
    All OCR extractors must implement the extract method that can handle
    both file paths and file-like objects.
    """
    
    @abstractmethod
    def extract(
        self, 
        file_input: Union[str, Path, BytesIO]
    ) -> Union[str, List[str]]:
        """Extract text from a PDF or image file.
        
        Args:
            file_input: Either a file path (str or Path) or a file-like object (BytesIO)
            
        Returns:
            Either a single concatenated string of all text, or a list of strings
            (one per page). The implementation decides the format.
            
        Raises:
            FileNotFoundError: If file path doesn't exist
            ValueError: If file format is not supported
            Exception: Other extraction errors should be raised with informative messages
        """
        pass

