"""
J.A.R.V.I.S. Specialist Agent Registry (core/specialists/)
=========================================================
Modular on-demand specialist agents operating under Master Orchestrator supervision.
"""

from .base import BaseSpecialistAgent
from .agents import (
    ResearchAgent,
    CodingAgent,
    QAAgent,
    MarketingAgent,
    SEOAgent,
    LeadGenAgent,
    WordPressAgent,
    BusinessAnalyst,
    SystemAgent,
    get_specialist,
    list_specialists
)

__all__ = [
    "BaseSpecialistAgent",
    "ResearchAgent",
    "CodingAgent",
    "QAAgent",
    "MarketingAgent",
    "SEOAgent",
    "LeadGenAgent",
    "WordPressAgent",
    "BusinessAnalyst",
    "SystemAgent",
    "get_specialist",
    "list_specialists"
]
