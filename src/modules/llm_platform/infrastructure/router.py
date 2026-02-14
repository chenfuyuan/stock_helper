from typing import TYPE_CHECKING, List, Optional

from loguru import logger

from src.modules.llm_platform.domain.exceptions import (
    LLMConnectionError,
    NoAvailableModelError,
)
from src.modules.llm_platform.domain.ports.llm import ILLMProvider

if TYPE_CHECKING:
    pass


class LLMRouter(ILLMProvider):
    def __init__(self, registry):
        self.registry = registry

    def _select_candidates(self, alias: Optional[str], tags: Optional[List[str]]) -> List:
        configs = self.registry.get_all_configs()

        candidates = []
        if alias:
            candidates = [c for c in configs if c.alias == alias and c.is_active]
        elif tags:
            # Match if config has ALL requested tags
            candidates = [c for c in configs if c.is_active and all(t in c.tags for t in tags)]
            candidates.sort(key=lambda x: x.priority)
        else:
            # Default: all active, sorted by priority
            candidates = [c for c in configs if c.is_active]
            candidates.sort(key=lambda x: x.priority)

        return candidates

    async def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
        alias: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        candidates = self._select_candidates(alias, tags)

        if not candidates:
            raise NoAvailableModelError(
                f"No LLM models found matching criteria: alias={alias}, tags={tags}"
            )

        last_error = None

        for config in candidates:
            provider = self.registry.get_provider(config.alias)
            if not provider:
                continue

            try:
                logger.debug(f"Routing request to LLM: {config.alias} (model: {config.model_name})")
                return await provider.generate(prompt, system_message, temperature)
            except LLMConnectionError as e:
                logger.warning(f"LLM {config.alias} failed: {str(e)}. Failing over...")
                last_error = e
                continue
            except Exception as e:
                logger.error(f"LLM {config.alias} unexpected error: {str(e)}")
                last_error = e
                continue

        raise NoAvailableModelError(f"All candidate models failed. Last error: {str(last_error)}")
