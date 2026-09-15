"""
Ship 30 for 30 Skill Unit Tests.
Verifies structure, validation metrics, headings, bold emphasis, and takeaway detection.
"""

import pytest
from app.skills.ship30 import Ship30Skill

def test_ship30_structural_validation():
    skill = Ship30Skill()

    sample_essay = """# The High Agency Product Leader

High agency is the single rarest asset in tech.
When obstacles emerge, low-agency people report back that legal or security said no. High-agency operators refuse to let constraints dictate the outcome. Shreyas Doshi embodied this across Stripe, Twitter, and Google.
Here is why this matters today.

## 1. Problem Framing Is 80% Of The Job
High agency PMs don't accept problems as handed down by executives.
- **Re-examine the premise** before assigning sprint tickets.
- Meet 1-on-1 with cross-functional detractors to uncover hidden incentives.
- Eliminate feature factories.

## Actionable Takeaway
Tomorrow morning, conduct an agency audit: identify the single biggest roadblock on your roadmap and find a creative path around it rather than waiting for permission.
"""

    metrics = skill.validate_ship30_output(sample_essay)
    assert metrics["has_headings"] is True
    assert metrics["has_bullets"] is True
    assert metrics["has_bold_emphasis"] is True
    assert metrics["has_actionable_takeaway"] is True
    assert metrics["word_count"] > 50

def test_ship30_incomplete_text_flagging():
    skill = Ship30Skill()
    plain_text = "Just a short unstructured paragraph without formatting or clear direction."
    metrics = skill.validate_ship30_output(plain_text)
    assert metrics["has_headings"] is False
    assert metrics["has_bullets"] is False
    assert metrics["has_actionable_takeaway"] is False
