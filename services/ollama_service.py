"""Ollama local HTTP API service for HackMate AI."""
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple
import requests

logger = logging.getLogger(__name__)


class OllamaService:
    def __init__(self, base_url: str = "http://localhost:11434", default_model: str = "qwen2.5:3b"):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model

    def check_health(self) -> Dict[str, Any]:
        """Checks if Ollama server is reachable and lists installed models."""
        t0 = time.time()
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3.0)
            latency_ms = int((time.time() - t0) * 1000)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", [])]
                return {
                    "connected": True,
                    "models": models,
                    "latency_ms": latency_ms,
                    "error": None,
                }
            else:
                return {
                    "connected": False,
                    "models": [],
                    "latency_ms": latency_ms,
                    "error": f"HTTP status {resp.status_code}",
                }
        except requests.exceptions.ConnectionError:
            return {
                "connected": False,
                "models": [],
                "latency_ms": None,
                "error": "Could not connect to Ollama. Please ensure Ollama is installed and running (`ollama serve`).",
            }
        except requests.exceptions.Timeout:
            return {
                "connected": False,
                "models": [],
                "latency_ms": None,
                "error": "Connection to Ollama timed out (exceeded 3.0s).",
            }
        except Exception as e:
            return {
                "connected": False,
                "models": [],
                "latency_ms": None,
                "error": str(e),
            }

    def is_model_available(self, model_name: Optional[str] = None) -> bool:
        """Returns True if the target model is installed locally in Ollama."""
        target = (model_name or self.default_model).lower()
        health = self.check_health()
        if not health["connected"]:
            return False
        installed = [m.lower() for m in health["models"]]
        # Matches full name or tag prefix, e.g. "qwen2.5:3b" or "qwen2.5:3b-instruct"
        return any(target in m or m.startswith(target) for m in installed)

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.15,
        timeout: float = 35.0,
        num_predict: int = 750,
    ) -> Tuple[bool, str]:
        """Calls the /api/chat endpoint with messages and speed-optimized parameters."""
        target_model = model or self.default_model
        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 2048,
                "num_predict": num_predict,
                "top_k": 25,
                "top_p": 0.9,
            },
        }

        try:
            resp = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=timeout)
            if resp.status_code == 200:
                result = resp.json()
                content = result.get("message", {}).get("content", "")
                return True, content
            else:
                return False, f"Ollama HTTP error {resp.status_code}: {resp.text}"
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to local Ollama server at " + self.base_url
        except requests.exceptions.Timeout:
            return False, f"Ollama generation timed out after {timeout} seconds."
        except Exception as e:
            return False, f"Ollama error: {str(e)}"

    @staticmethod
    def extract_json(raw_text: str) -> Optional[Any]:
        """Robustly extracts JSON from an LLM response even with markdown wrappers or commentary."""
        if not raw_text:
            return None

        text = raw_text.strip()

        # Try direct parse first
        try:
            return json.loads(text)
        except Exception:
            pass

        # Try markdown code block ```json ... ``` or ``` ... ```
        code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if code_block_match:
            candidate = code_block_match.group(1).strip()
            try:
                return json.loads(candidate)
            except Exception:
                pass

        # Try finding outer brackets [ ... ] or { ... }
        bracket_match = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", text)
        if bracket_match:
            candidate = bracket_match.group(1).strip()
            try:
                return json.loads(candidate)
            except Exception:
                # Attempt minor syntax repair: remove trailing commas before } or ]
                repaired = re.sub(r",\s*([\]}])", r"\1", candidate)
                try:
                    return json.loads(repaired)
                except Exception:
                    pass

        return None
