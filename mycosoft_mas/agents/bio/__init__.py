"""Bio/lab automation agents."""

try:
    from mycosoft_mas.agents.bio.culture_vision_agent import CultureVisionAgent
except ImportError:
    CultureVisionAgent = None  # type: ignore[misc, assignment]

__all__ = ["CultureVisionAgent"]
