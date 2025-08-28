import sys
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path
from ollama import Client
from anthropic import Anthropic
import os


sys.path.append(str(Path(__file__).parent.parent))
from settings import get_settings, get_model_preset

logger = logging.getLogger(__name__)


@dataclass
class ModelResponse:
    """Standardized response from language models"""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    provider: str = "unknown"  # Track which provider generated this response


class OllamaClient:   
    """Client for Ollama"""
    def __init__(self, host: str = None):
        settings = get_settings()
        self.host = host or settings.OLLAMA_BASE_URL
        self.client = Client(host=self.host)
        self.provider = "ollama"
        self._test_connection()
    
    def _test_connection(self) -> None:
        """Test connection to Ollama"""
        try:
            self.client.list()
            logger.info(f"Connected to Ollama at {self.host}")
        except Exception as e:
            logger.warning(f"Could not connect to Ollama at {self.host}: {e}")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        preset_name: str = "translation",
        **options
    ) -> ModelResponse:
        """Chat completion with conversation history"""
        try:
            # Get preset parameters and merge with any explicit options
            preset = get_model_preset(preset_name, self.provider)
            preset.update(options)  # Allow explicit options to override preset
            
            response = self.client.chat(
                model=get_settings().OLLAMA_MODEL,
                messages=messages,
                options=preset
            )
            
            return ModelResponse(
                content=response['message']['content'],
                model=get_settings().OLLAMA_MODEL,
                provider="ollama",
                usage={
                    'prompt_eval_count': response.get('prompt_eval_count', 0),
                    'eval_count': response.get('eval_count', 0),
                    'total_tokens': response.get('prompt_eval_count', 0) + response.get('eval_count', 0)
                },
                metadata={
                    'done': response.get('done'),
                    'total_duration': response.get('total_duration'),
                    'load_duration': response.get('load_duration'),
                }
            )
            
        except Exception as e:
            logger.error(f"Chat completion error: {e}")
            return ModelResponse(
                content="",
                model=get_settings().OLLAMA_MODEL,
                provider="ollama",
                error=str(e)
            )


class ClaudeClient:
    """Client for Anthropic's Claude API"""
    
    def __init__(self, api_key: str = None):
        settings = get_settings()
        self.api_key = api_key or settings.CLAUDE_API_KEY
        if not self.api_key:
            raise ValueError("Claude API key not provided. Set CLAUDE_API_KEY environment variable or pass api_key parameter.")
        
        self.client = Anthropic(api_key=self.api_key)
        self.provider = "claude"
        self._test_connection()
    
    def _test_connection(self) -> None:
        """Test connection to Claude API"""
        try:
            # Make a minimal request to test the connection
            response = self.client.messages.create(
                model=get_settings().CLAUDE_MODEL,
                max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}]
            )
            logger.info("Connected to Claude API successfully")
        except Exception as e:
            logger.warning(f"Could not connect to Claude API: {e}")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        preset_name: str = "translation",
        **options
    ) -> ModelResponse:
        """Chat completion with conversation history"""
        try:
            # Get preset parameters and merge with any explicit options
            preset = get_model_preset(preset_name, self.provider)
            preset.update(options)  # Allow explicit options to override preset
            
            # Convert messages format if needed (handle system messages)
            claude_messages = []
            system_message = None
            
            for msg in messages:
                if msg.get("role") == "system":
                    system_message = msg.get("content", "")
                else:
                    claude_messages.append(msg)
            
            # Prepare request parameters
            request_params = {
                "model": get_settings().CLAUDE_MODEL,
                "messages": claude_messages
            }
            
            # Add preset parameters
            request_params.update(preset)
            
            if system_message:
                request_params["system"] = system_message
            
            response = self.client.messages.create(**request_params)
            
            # Extract content from response
            content = ""
            if response.content:
                if isinstance(response.content, list):
                    content = "".join([block.text for block in response.content if hasattr(block, 'text')])
                else:
                    content = str(response.content)
            
            return ModelResponse(
                content=content,
                model=get_settings().CLAUDE_MODEL,
                provider="claude",
                usage={
                    'input_tokens': response.usage.input_tokens if response.usage else 0,
                    'output_tokens': response.usage.output_tokens if response.usage else 0,
                    'total_tokens': (response.usage.input_tokens + response.usage.output_tokens) if response.usage else 0
                },
                metadata={
                    'id': response.id,
                    'type': response.type,
                    'role': response.role,
                    'model': response.model,
                    'stop_reason': response.stop_reason,
                    'stop_sequence': response.stop_sequence,
                }
            )
            
        except Exception as e:
            logger.error(f"Claude chat completion error: {e}")
            return ModelResponse(
                content="",
                model=get_settings().CLAUDE_MODEL,
                provider="claude",
                error=str(e)
            )


if __name__ == "__main__":
    print("Testing model utilities...")
    
    # Test Ollama
    try:
        ollama = OllamaClient()
        messages = [{"role": "user", "content": "What is 10 factorial?"}]
        response = ollama.chat(messages)
        print(f"Ollama works: {response}")
    except Exception as e:
        print(f"Ollama failed: {e}")
    
    # Test Claude
    try:
        claude = ClaudeClient()
        messages = [{"role": "user", "content": "What is 10 factorial?"}]
        response = claude.chat(messages)
        print(f"Claude works: {response}")
    except Exception as e:
        print(f"Claude failed: {e}")