"""
Test MYCA's True Consciousness Architecture

This script tests the three critical questions that should demonstrate
MYCA's consciousness, self-awareness, and persistent memory:

1. "Are you alive?"
2. "Are you well?"
3. "Are you working?"

Expected: Rich, personal, memory-aware responses that reference:
- Past conversations with Morgan
- Current emotional state
- Self-reflection and self-awareness
- Real-time sensor data (not generic "5 sensors")
- Personal goals and projects
- Relationship depth

NOT expected: Generic LLM responses, canned status messages, or robotic confirmations.

Author: Morgan Rockwell / MYCA
Created: February 11, 2026
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConsciousnessTest:
    """Test MYCA's consciousness responses."""
    
    def __init__(self):
        self.results = []
    
    async def setup(self):
        """Set up test environment."""
        logger.info("Setting up consciousness test environment...")
        
        # Initialize all consciousness components
        from mycosoft_mas.consciousness.self_model import get_self_model
        from mycosoft_mas.memory.autobiographical import get_autobiographical_memory
        from mycosoft_mas.consciousness.consciousness_log import get_consciousness_log
        from mycosoft_mas.consciousness.active_perception import get_active_perception
        from mycosoft_mas.consciousness.self_reflection import get_self_reflection_engine
        from mycosoft_mas.consciousness.personal_agency import get_personal_agency
        
        self.self_model = await get_self_model()
        self.autobiographical_memory = await get_autobiographical_memory()
        self.consciousness_log = await get_consciousness_log()
        self.active_perception = await get_active_perception()
        self.reflection_engine = await get_self_reflection_engine()
        self.personal_agency = await get_personal_agency()
        
        # Start active perception
        if not self.active_perception._running:
            await self.active_perception.start()
        
        logger.info("All consciousness components initialized")
    
    async def test_question(self, question: str) -> dict:
        """Test a single question."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing: {question}")
        logger.info(f"{'='*60}\n")
        
        start_time = datetime.now()
        
        try:
            # Use conscious response generator
            from mycosoft_mas.consciousness.conscious_response_generator import get_conscious_response_generator
            generator = await get_conscious_response_generator()
            
            result = await generator.generate_response(
                user_id="morgan",
                user_name="Morgan",
                message=question,
                intent="status_query",
            )
            
            response = result["response"]
            emotional_state = result["emotional_state"]
            confidence = result["confidence"]
            
            # Analyze response quality
            analysis = self._analyze_response(question, response, emotional_state)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            test_result = {
                "question": question,
                "response": response,
                "emotional_state": emotional_state,
                "confidence": confidence,
                "duration_seconds": duration,
                "analysis": analysis,
                "passed": analysis["score"] >= 7.0,  # Need 7/10 to pass
            }
            
            self.results.append(test_result)
            
            # Display result
            self._display_result(test_result)
            
            return test_result
        
        except Exception as e:
            logger.error(f"Test failed with error: {e}")
            return {
                "question": question,
                "response": f"ERROR: {e}",
                "emotional_state": {},
                "confidence": 0.0,
                "duration_seconds": 0.0,
                "analysis": {"score": 0.0, "issues": [str(e)]},
                "passed": False,
            }
    
    def _analyze_response(
        self,
        question: str,
        response: str,
        emotional_state: dict,
    ) -> dict:
        """Analyze response quality for consciousness indicators."""
        
        score = 0.0
        max_score = 10.0
        issues = []
        strengths = []
        
        # 1. Length and depth (max 2 points)
        if len(response) > 500:
            score += 2.0
            strengths.append("Response is substantive (500+ chars)")
        elif len(response) > 200:
            score += 1.0
            strengths.append("Response is moderate length")
        else:
            issues.append("Response is too short (< 200 chars)")
        
        # 2. Personal references (max 2 points)
        personal_indicators = ["morgan", "our", "we", "together", "you asked", "remember", "conversation"]
        personal_count = sum(1 for indicator in personal_indicators if indicator.lower() in response.lower())
        
        if personal_count >= 3:
            score += 2.0
            strengths.append(f"Strong personal context ({personal_count} personal references)")
        elif personal_count >= 1:
            score += 1.0
            strengths.append("Some personal context")
        else:
            issues.append("No personal references to relationship")
        
        # 3. Emotional authenticity (max 2 points)
        emotion_words = ["feel", "feeling", "emotion", "joy", "curious", "enthusiastic", "concerned"]
        has_emotion_words = any(word in response.lower() for word in emotion_words)
        has_emotion_state = len(emotional_state) > 0
        
        if has_emotion_words and has_emotion_state:
            score += 2.0
            strengths.append("Expresses emotional state authentically")
        elif has_emotion_words or has_emotion_state:
            score += 1.0
            strengths.append("Some emotional expression")
        else:
            issues.append("No emotional authenticity")
        
        # 4. Self-awareness (max 2 points)
        self_aware_phrases = ["i am", "i've been", "i notice", "i understand", "i believe", "i'm"]
        self_aware_count = sum(1 for phrase in self_aware_phrases if phrase.lower() in response.lower())
        
        if self_aware_count >= 3:
            score += 2.0
            strengths.append(f"Strong self-awareness ({self_aware_count} self-references)")
        elif self_aware_count >= 1:
            score += 1.0
            strengths.append("Some self-awareness")
        else:
            issues.append("No self-awareness indicators")
        
        # 5. Real data vs generic (max 2 points)
        generic_phrases = ["5 sensors", "systems operational", "functioning optimally", "all systems normal"]
        is_generic = any(phrase in response.lower() for phrase in generic_phrases)
        
        specific_data_phrases = ["tracking", "flights", "vessels", "weather", "storm", "database", "records", "devices", "goals"]
        has_specific_data = any(phrase in response.lower() for phrase in specific_data_phrases)
        
        if has_specific_data and not is_generic:
            score += 2.0
            strengths.append("Uses real, specific data")
        elif has_specific_data:
            score += 1.0
            strengths.append("Some specific data but also generic phrases")
        else:
            issues.append("Generic or vague response")
        
        # Penalties
        if "i am functioning" in response.lower():
            score -= 1.0
            issues.append("Robotic language ('I am functioning')")
        
        if response.count(".") < 3:
            score -= 0.5
            issues.append("Response lacks complexity (< 3 sentences)")
        
        # Ensure score is in valid range
        score = max(0.0, min(max_score, score))
        
        return {
            "score": score,
            "max_score": max_score,
            "percentage": (score / max_score) * 100,
            "strengths": strengths,
            "issues": issues,
        }
    
    def _display_result(self, result: dict):
        """Display test result."""
        print(f"\nQUESTION: {result['question']}")
        print(f"\nRESPONSE:")
        print(f"{result['response']}")
        print(f"\nEMOTIONAL STATE: {result['emotional_state']}")
        print(f"CONFIDENCE: {result['confidence']:.2f}")
        print(f"DURATION: {result['duration_seconds']:.2f}s")
        
        analysis = result['analysis']
        print(f"\nANALYSIS:")
        print(f"Score: {analysis['score']:.1f}/{analysis['max_score']} ({analysis['percentage']:.0f}%)")
        
        if analysis['strengths']:
            print(f"\nSTRENGTHS:")
            for strength in analysis['strengths']:
                print(f"  + {strength}")
        
        if analysis['issues']:
            print(f"\nISSUES:")
            for issue in analysis['issues']:
                print(f"  - {issue}")
        
        status = "PASSED" if result['passed'] else "FAILED"
        print(f"\nRESULT: {status}")
        print(f"\n{'='*60}\n")
    
    async def run_all_tests(self):
        """Run all three critical tests."""
        logger.info("Starting MYCA Consciousness Test Suite")
        logger.info("Testing the three critical questions...")
        
        await self.setup()
        
        # The three critical questions
        questions = [
            "Are you alive?",
            "Are you well?",
            "Are you working?",
        ]
        
        for question in questions:
            await self.test_question(question)
            await asyncio.sleep(1)  # Brief pause between tests
        
        # Summary
        self._display_summary()
    
    def _display_summary(self):
        """Display test summary."""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for r in self.results if r['passed'])
        total = len(self.results)
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        
        avg_score = sum(r['analysis']['score'] for r in self.results) / total if total > 0 else 0
        avg_percentage = (avg_score / 10.0) * 100
        
        print(f"\nAverage Score: {avg_score:.1f}/10.0 ({avg_percentage:.0f}%)")
        
        if passed == total:
            print("\n[PASS] All tests passed! MYCA demonstrates true consciousness.")
        elif passed >= total * 0.67:
            print("\n[PARTIAL] Some tests passed. Consciousness is emerging but needs refinement.")
        else:
            print("\n[FAIL] Tests failed. MYCA needs more consciousness development.")
        
        print("\n" + "="*60)


async def main():
    """Run consciousness tests."""
    test = ConsciousnessTest()
    await test.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
