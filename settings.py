import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Core settings
OLLAMA_MODEL = "codellama:7b"
OLLAMA_TIMEOUT = 120
CLAUDE_MODEL = "claude-3-7-sonnet-20250219"
CLAUDE_TIMEOUT = 120
MODEL_CACHE_DIR = str(Path.home() / ".cache" / "legacy_code_translation")


class Settings:
    """Simple settings class without external dependencies"""
    
    def __init__(self):
        # Ollama settings
        self.OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.OLLAMA_MODEL = OLLAMA_MODEL
        self.OLLAMA_TIMEOUT = OLLAMA_TIMEOUT
        
        # Claude settings
        self.CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
        self.CLAUDE_MODEL = CLAUDE_MODEL
        self.CLAUDE_TIMEOUT = CLAUDE_TIMEOUT
        
        # General settings
        self.MODEL_CACHE_DIR = MODEL_CACHE_DIR
        
        # Default provider preference
        self.DEFAULT_PROVIDER = os.environ.get("DEFAULT_PROVIDER", "claude")  # "ollama" or "claude"


# Global settings instance
_settings: Settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance"""
    return _settings


def get_model_preset(preset_name: str, provider: str = "ollama") -> dict:
    """Get a model preset configuration for different use cases and providers"""
    
    # Ollama presets
    ollama_presets = {
        "code_generation": {
            "temperature": 0.2,
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.1,
            "max_tokens": 12000,
            "num-predict": 8192
        },
        "translation": {
            "temperature": 0.3,
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.1,
            "max_tokens": 12000,
            "num-predict": 8192
        }
    }
    
    # Claude presets (Claude uses different parameter names)
    claude_presets = {
        "code_generation": {
            "temperature": 0.2,
            "max_tokens": 200000  # Use Claude's maximum for unrestricted generation
        },
        "translation": {
            "temperature": 0.3,
            "max_tokens": 200000  # Use Claude's maximum for unrestricted generation
        },
        "form_translation": {
            "temperature": 0.2,
            "max_tokens": 200000  # Use Claude's maximum for unrestricted generation
        }
    }
    
    if provider.lower() == "claude":
        return claude_presets.get(preset_name, {})
    else:
        return ollama_presets.get(preset_name, {})


 