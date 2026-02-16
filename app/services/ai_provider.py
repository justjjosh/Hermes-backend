from abc import ABC, abstractmethod
from typing import Dict, List

class AIProvider(ABC):
    @abstractmethod
    def generate_pitch(self, brand: dict, profile: dict)-> Dict[str, str]:
        pass
    @abstractmethod
    def discover_brands(self, niches: List[str], limit: int = 10) -> List[dict]:
        pass