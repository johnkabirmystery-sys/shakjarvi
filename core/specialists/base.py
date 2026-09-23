"""
Base Specialist Agent Class (core/specialists/base.py)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseSpecialistAgent(ABC):
    def __init__(self, name: str, role: str, description: str, system_prompt: str):
        self.name = name
        self.role = role
        self.description = description
        self.system_prompt = system_prompt

    @abstractmethod
    async def execute(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Executes the assigned specialist task and returns a structured result with verified evidence."""
        pass

    def get_info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description
        }
