"""Configuration management for environment variables.

This module provides safe loading of environment variables with proper error handling.
It automatically detects virtual environments and loads .env files from the project root.
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Try to load .env file if python-dotenv is available
_loaded = False
try:
    from dotenv import load_dotenv
    
    def _load_env_file():
        """Load .env file from project root."""
        global _loaded
        if _loaded:
            return
        
        # Find project root (backend/config.py -> backend -> project root)
        project_root = Path(__file__).parent.parent
        env_path = project_root / ".env"
        
        if env_path.exists():
            load_dotenv(env_path, override=False)
            _loaded = True
        else:
            # Also try backend/.env as fallback
            backend_env = Path(__file__).parent / ".env"
            if backend_env.exists():
                load_dotenv(backend_env, override=False)
                _loaded = True
    
    # Load on import
    _load_env_file()
    
except ImportError:
    # python-dotenv not installed, skip loading
    pass


def is_venv() -> bool:
    """Check if running inside a virtual environment.
    
    Returns:
        True if running in a virtual environment, False otherwise.
    """
    return (
        hasattr(sys, 'real_prefix') or
        (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) or
        os.getenv('VIRTUAL_ENV') is not None
    )


def get_env(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """Get an environment variable with proper error handling.
    
    Args:
        key: Environment variable name
        default: Default value if key is not found (only used if required=False)
        required: If True, raises RuntimeError when key is missing
    
    Returns:
        Environment variable value, or default if not required and not found
    
    Raises:
        RuntimeError: If required=True and key is missing
    """
    value = os.getenv(key, default)
    
    if required and value is None:
        raise RuntimeError(
            f"Missing required environment variable: {key}. "
            f"Please set it in your .env file or environment. "
            f"Check that your .env file exists in the project root."
        )
    
    return value


def get_openai_api_key() -> str:
    """Get OpenAI API key from environment.
    
    Returns:
        OpenAI API key string
    
    Raises:
        RuntimeError: If OPENAI_API_KEY is not set
    """
    api_key = get_env("OPENAI_API_KEY", required=True)
    
    if not api_key or api_key == "your-api-key-here":
        raise RuntimeError(
            "Missing or invalid OPENAI_API_KEY. "
            "Please set your OpenAI API key in the .env file:\n"
            "  OPENAI_API_KEY=sk-proj-your-actual-key-here\n\n"
            "Get your API key from: https://platform.openai.com/api-keys"
        )
    
    if not api_key.startswith("sk-"):
        raise RuntimeError(
            f"Invalid OPENAI_API_KEY format. Expected key starting with 'sk-', "
            f"got key starting with '{api_key[:10]}...'"
        )
    
    return api_key

