from typing import Optional
from src.shared.domain.ports.llm import ILLMProvider

class BaseLLMProvider(ILLMProvider):
    def __init__(self, model: str):
        self.model = model
