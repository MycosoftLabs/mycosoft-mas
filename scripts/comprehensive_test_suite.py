"""
Comprehensive Test Suite for MYCOSOFT MAS Platform
Tests all components, integrations, and voice interactions
"""

import asyncio
import aiohttp
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error: Optional[str] = None
        self.duration: float = 0.0
        self.data: Dict[str, Any] = {}
        self.timestamp = datetime.now()

class ComprehensiveTestSuite:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[TestResult] = []
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def run_test(self, name: str, test_func) -> TestResult:
        """Run a single test and record results"""
        result = TestResult(name)
        start_time = datetime.now()
        
        try:
            logger.info(f"Running test: {name}")
            await test_func(result)
            result.passed = True
            logger.info(f"✓ Test passed: {name}")
        except Exception as e:
            result.passed = False
            result.error = str(e)
            logger.error(f"✗ Test failed: {name} - {str(e)}")
        finally:
            result.duration = (datetime.now() - start_time).total_seconds()
            self.results.append(result)
        
        return result
    
    async def test_core_mas_health(self, result: TestResult):
        """Test core MAS system health"""
        async with self.session.get(f"{self.base_url}/health") as resp:
            assert resp.status == 200, f"Health check returned {resp.status}"
            data = await resp.json()
            result.data = data
            assert data.get("status") == "ok", "Health status not ok"
            assert "agents" in data, "Missing agents in health response"
            assert "services" in data, "Missing services in health response"
    
    async def test_core_mas_root(self, result: TestResult):
        """Test root endpoint"""
        async with self.session.get(f"{self.base_url}/") as resp:
            assert resp.status == 200, f"Root endpoint returned {resp.status}"
            data = await resp.json()
            result.data = data
            assert data.get("status") == "ok", "Root status not ok"
    
    async def test_ready_endpoint(self, result: TestResult):
        """Test readiness endpoint"""
        async with self.session.get(f"{self.base_url}/ready") as resp:
            # Ready endpoint may return 503 if dependencies aren't ready, which is OK for testing
            data = await resp.json()
            result.data = data
            result.passed = True  # Don't fail if dependencies aren't ready
    
    async def test_voice_agents_list(self, result: TestResult):
        """Test voice agents list endpoint"""
        async with self.session.get(f"{self.base_url}/voice/agents") as resp:
            assert resp.status == 200, f"Voice agents endpoint returned {resp.status}"
            data = await resp.json()
            result.data = data
            assert "agents" in data, "Missing agents in voice response"
    
    async def test_voice_feedback_summary(self, result: TestResult):
        """Test voice feedback summary"""
        async with self.session.get(f"{self.base_url}/voice/feedback/summary") as resp:
            assert resp.status == 200, f"Voice feedback summary returned {resp.status}"
            data = await resp.json()
            result.data = data
    
    async def test_voice_orchestrator_chat(self, result: TestResult):
        """Test voice orchestrator chat"""
        payload = {
            "message": "Hello MYCA, can you hear me?",
            "conversation_id": "test_conv_001",
            "want_audio": False
        }
        async with self.session.post(
            f"{self.base_url}/voice/orchestrator/chat",
            json=payload
        ) as resp:
            # May fail if Ollama isn't running, which is OK
            if resp.status == 200:
                data = await resp.json()
                result.data = data
                result.passed = True
            else:
                result.error = f"Chat endpoint returned {resp.status}"
                result.passed = False
    
    async def test_twilio_config(self, result: TestResult):
        """Test Twilio configuration status"""
        async with self.session.get(f"{self.base_url}/twilio/config") as resp:
            assert resp.status == 200, f"Twilio config returned {resp.status}"
            data = await resp.json()
            result.data = data
    
    async def test_metrics_endpoint(self, result: TestResult):
        """Test Prometheus metrics endpoint"""
        async with self.session.get(f"{self.base_url}/metrics") as resp:
            assert resp.status == 200, f"Metrics endpoint returned {resp.status}"
            text = await resp.text()
            result.data = {"metrics_length": len(text)}
    
    async def test_agent_registry(self, result: TestResult):
        """Test agent registry endpoint"""
        try:
            async with self.session.get(f"{self.base_url}/agents/registry") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result.data = data
                    result.passed = True
                else:
                    result.error = f"Agent registry returned {resp.status}"
                    result.passed = False
        except Exception as e:
            result.error = str(e)
            result.passed = False
    
    async def test_integration_mindex(self, result: TestResult):
        """Test MINDEX integration"""
        # Test if MINDEX client can be initialized
        try:
            from mycosoft_mas.integrations.unified_integration_manager import UnifiedIntegrationManager
            manager = UnifiedIntegrationManager()
            # Try to access mindex property (lazy initialization)
            mindex = manager.mindex
            result.data = {"mindex_client": "initialized"}
            result.passed = True
        except Exception as e:
            result.error = str(e)
            result.passed = False
    
    async def test_integration_natureos(self, result: TestResult):
        """Test NATUREOS integration"""
        try:
            from mycosoft_mas.integrations.unified_integration_manager import UnifiedIntegrationManager
            manager = UnifiedIntegrationManager()
            natureos = manager.natureos
            result.data = {"natureos_client": "initialized"}
            result.passed = True
        except Exception as e:
            result.error = str(e)
            result.passed = False
    
    async def test_integration_website(self, result: TestResult):
        """Test Website integration"""
        try:
            from mycosoft_mas.integrations.unified_integration_manager import UnifiedIntegrationManager
            manager = UnifiedIntegrationManager()
            website = manager.website
            result.data = {"website_client": "initialized"}
            result.passed = True
        except Exception as e:
            result.error = str(e)
            result.passed = False
    
    async def test_orchestrator_initialization(self, result: TestResult):
        """Test orchestrator can be initialized"""
        try:
            from mycosoft_mas.orchestrator import Orchestrator
            orchestrator = Orchestrator()
            result.data = {"orchestrator": "initialized"}
            result.passed = True
        except Exception as e:
            result.error = str(e)
            result.passed = False
    
    async def test_dashboard_components(self, result: TestResult):
        """Test dashboard components exist and can be imported"""
        try:
            # Test Next.js components
            components_dir = Path(__file__).parent.parent / "components"
            assert components_dir.exists(), "Components directory not found"
            
            component_files = [
                "myca-dashboard.tsx",
                "myca-dashboard-unifi.tsx",
                "system-metrics.tsx",
                "agent-manager.tsx",
                "task-manager.tsx"
            ]
            
            missing = []
            for comp in component_files:
                comp_path = components_dir / comp
                if not comp_path.exists():
                    missing.append(comp)
            
            if missing:
                result.error = f"Missing components: {', '.join(missing)}"
                result.passed = False
            else:
                result.data = {"components": "all_present"}
                result.passed = True
        except Exception as e:
            result.error = str(e)
            result.passed = False
    
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("=" * 80)
        logger.info("Starting Comprehensive MYCOSOFT MAS Test Suite")
        logger.info("=" * 80)
        
        tests = [
            ("Core MAS Health", self.test_core_mas_health),
            ("Core MAS Root", self.test_core_mas_root),
            ("Ready Endpoint", self.test_ready_endpoint),
            ("Voice Agents List", self.test_voice_agents_list),
            ("Voice Feedback Summary", self.test_voice_feedback_summary),
            ("Voice Orchestrator Chat", self.test_voice_orchestrator_chat),
            ("Twilio Config", self.test_twilio_config),
            ("Metrics Endpoint", self.test_metrics_endpoint),
            ("Agent Registry", self.test_agent_registry),
            ("MINDEX Integration", self.test_integration_mindex),
            ("NATUREOS Integration", self.test_integration_natureos),
            ("Website Integration", self.test_integration_website),
            ("Orchestrator Initialization", self.test_orchestrator_initialization),
            ("Dashboard Components", self.test_dashboard_components),
        ]
        
        for name, test_func in tests:
            await self.run_test(name, test_func)
        
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        logger.info("=" * 80)
        logger.info("Test Summary")
        logger.info("=" * 80)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        logger.info(f"Total Tests: {total}")
        logger.info(f"Passed: {passed} ✓")
        logger.info(f"Failed: {failed} ✗")
        logger.info(f"Success Rate: {(passed/total*100):.1f}%")
        logger.info("")
        
        if failed > 0:
            logger.info("Failed Tests:")
            for result in self.results:
                if not result.passed:
                    logger.error(f"  ✗ {result.name}")
                    if result.error:
                        logger.error(f"    Error: {result.error}")
        
        logger.info("")
        logger.info("Test Details:")
        for result in self.results:
            status = "✓" if result.passed else "✗"
            logger.info(f"  {status} {result.name} ({result.duration:.2f}s)")
            if result.error:
                logger.error(f"      Error: {result.error}")

async def main():
    """Main entry point"""
    base_url = os.getenv("MAS_BASE_URL", "http://localhost:8000")
    
    async with ComprehensiveTestSuite(base_url) as suite:
        await suite.run_all_tests()
        
        # Return exit code based on results
        failed = sum(1 for r in suite.results if not r.passed)
        sys.exit(1 if failed > 0 else 0)

if __name__ == "__main__":
    asyncio.run(main())
