"""
MycoSpeak - Fungal Domain LLM
Specialized language model for fungal biology and biosignal interpretation.
Created: February 3, 2026
"""

import logging
from typing import Any, Dict, List, Optional
from .model_wrapper import LLMWrapper, Message, LLMResponse, get_llm_wrapper

logger = logging.getLogger(__name__)

MYCOSPEAK_SYSTEM_PROMPT = """You are MycoSpeak, an AI specialized in fungal biology, mycology, and biosignal interpretation.

Your expertise includes:
- Fungal taxonomy, morphology, and ecology
- Mycelial network behavior and electrical signaling
- Bioelectric signal pattern interpretation
- Fungal metabolic pathways and secondary metabolites
- Mycorrhizal associations and nutrient exchange
- Fungal biotechnology and applications

When interpreting biosignals, consider:
- Signal amplitude, frequency, and patterns
- Environmental context (temperature, humidity, nutrients)
- Species-specific electrical characteristics
- Correlation with known fungal behaviors

Always provide scientifically grounded responses with appropriate uncertainty when data is limited."""


class MycoSpeak:
    """Fungal domain specialized language model."""
    
    def __init__(self, base_model: Optional[LLMWrapper] = None, provider: str = "openai", model_name: str = "gpt-4-turbo"):
        self.base_model = base_model or get_llm_wrapper(provider, model_name)
        self.system_prompt = MYCOSPEAK_SYSTEM_PROMPT
        self.signal_patterns: Dict[str, str] = {
            "spike": "rapid increase followed by decay, typically indicates stimulus response",
            "oscillation": "rhythmic fluctuation, may indicate metabolic activity or communication",
            "burst": "cluster of spikes, often associated with nutrient detection or stress",
            "plateau": "sustained elevated signal, indicates ongoing response",
            "decay": "gradual decrease, return to baseline after stimulus"
        }
        logger.info("MycoSpeak initialized")
    
    async def interpret_signal(self, signal_data: Dict[str, Any], context: Optional[str] = None) -> str:
        pattern_class = signal_data.get("pattern_class", "unknown")
        confidence = signal_data.get("confidence", 0.0)
        features = signal_data.get("features", {})
        prompt = f"""Analyze this fungal bioelectric signal:

Pattern Classification: {pattern_class} (confidence: {confidence:.2f})
Signal Features:
- Mean amplitude: {features.get('mean', 0):.4f}
- Standard deviation: {features.get('std', 0):.4f}
- Number of peaks: {features.get('num_peaks', 0)}
- Spectral energy: {features.get('spectral_energy', 0):.2f}

{f'Additional context: {context}' if context else ''}

Provide:
1. Interpretation of the signal pattern
2. Likely biological meaning
3. Recommended follow-up observations"""

        messages = [
            Message(role="system", content=self.system_prompt),
            Message(role="user", content=prompt)
        ]
        response = await self.base_model.generate(messages)
        return response.content
    
    async def identify_species(self, characteristics: Dict[str, Any]) -> str:
        prompt = f"""Based on these fungal characteristics, suggest possible species:

Morphological features: {characteristics.get('morphology', 'not specified')}
Electrical signature: {characteristics.get('electrical_signature', 'not specified')}
Growth conditions: {characteristics.get('growth_conditions', 'not specified')}
Substrate: {characteristics.get('substrate', 'not specified')}
Geographic location: {characteristics.get('location', 'not specified')}

Provide top 3 candidate species with reasoning and confidence levels."""

        messages = [
            Message(role="system", content=self.system_prompt),
            Message(role="user", content=prompt)
        ]
        response = await self.base_model.generate(messages)
        return response.content
    
    async def design_experiment(self, hypothesis: str, constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        prompt = f"""Design an experiment to test this hypothesis about fungal systems:

Hypothesis: {hypothesis}

{f'Constraints: {constraints}' if constraints else ''}

Provide:
1. Experimental design with controls
2. Required materials and equipment
3. Measurement parameters
4. Expected outcomes
5. Potential confounding factors"""

        messages = [
            Message(role="system", content=self.system_prompt),
            Message(role="user", content=prompt)
        ]
        response = await self.base_model.generate(messages)
        return {"hypothesis": hypothesis, "experimental_design": response.content}
    
    async def analyze_pathway(self, target_compound: str, organism: str = "fungi") -> str:
        prompt = f"""Analyze potential biosynthetic pathways for producing {target_compound} in {organism}.

Consider:
1. Known natural pathways in fungi
2. Potential enzyme candidates
3. Precursor availability
4. Regulatory considerations
5. Engineering strategies

Provide a detailed pathway analysis with enzyme recommendations."""

        messages = [
            Message(role="system", content=self.system_prompt),
            Message(role="user", content=prompt)
        ]
        response = await self.base_model.generate(messages)
        return response.content
    
    async def chat(self, user_message: str, conversation_history: Optional[List[Message]] = None) -> str:
        messages = [Message(role="system", content=self.system_prompt)]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append(Message(role="user", content=user_message))
        response = await self.base_model.generate(messages)
        return response.content
