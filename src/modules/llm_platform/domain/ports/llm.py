from abc import ABC, abstractmethod
from typing import Optional


class ILLMProvider(ABC):
    """
    LLM provider abstraction (Strategy Interface).

    This interface defines the minimal contract that any LLM implementation
    must fulfill so that upstream modules (e.g. Research) can depend only on
    this Port instead of concrete infrastructure implementations.
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """
        Generate a text response from the underlying LLM.

        Args:
            prompt: User input prompt.
            system_message: Optional system-level instruction.
            temperature: Sampling temperature (0.0 - 1.0), controls randomness.

        Returns:
            Generated text content.

        Raises:
            LLMConnectionError: When the underlying API call fails or is unavailable.
        """

        raise NotImplementedError
