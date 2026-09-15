"""
Intent Routing Tests.
Verifies that user queries route to Grounded QA, Ship 30, or Artifact Generation skills.
"""

import pytest
from app.agent.router import intent_router

def test_intent_routing_qa():
    assert intent_router.classify_intent("How did Elena Verna define reverse trials?") == "grounded_qa"
    assert intent_router.classify_intent("What is Gustaf's rule on cohort retention curves?") == "grounded_qa"
    assert intent_router.classify_intent("Why did Brian Chesky criticize conventional PM structures?") == "grounded_qa"

def test_intent_routing_ship30():
    assert intent_router.classify_intent("Write a Ship 30 essay on high agency product management") == "ship30"
    assert intent_router.classify_intent("Write an atomic essay about compounding growth loops") == "ship30"
    assert intent_router.classify_intent("Write an article of 1250 words about Elena Verna's onboarding frameworks") == "ship30"
    assert intent_router.classify_intent("Can you draft a thought piece based on founder mode?") == "ship30"

def test_intent_routing_artifacts():
    assert intent_router.classify_intent("Generate an HTML growth metric dashboard") == "artifact_generation"
    assert intent_router.classify_intent("Create an HTML component for retention curves") == "artifact_generation"
    assert intent_router.classify_intent("Build an interactive dashboard for North Star metrics") == "artifact_generation"
    assert intent_router.classify_intent("Create a checklist artifact for user onboarding") == "artifact_generation"
