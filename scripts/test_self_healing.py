#!/usr/bin/env python3
"""
Test script for Self-Healing MAS Infrastructure
Tests: SecurityCodeReviewer, CodeModificationService, VulnerabilityScanner, SelfHealingMonitor
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_security_code_reviewer():
    """Test SecurityCodeReviewer functionality"""
    print("\n[1/4] Testing SecurityCodeReviewer...")
    
    from mycosoft_mas.security.code_reviewer import SecurityCodeReviewer
    
    reviewer = SecurityCodeReviewer()
    
    # Test 1: Protected file detection
    result = await reviewer.review_code_change({
        "requester_id": "test-agent",
        "change_type": "edit",
        "description": "Test change",
        "target_files": ["mycosoft_mas/core/orchestrator.py"],
        "code_content": None
    })
    assert result["approved"] == False, "Should block protected file"
    print("  [OK] Protected file detection works")
    
    # Test 2: Secret detection
    result = await reviewer.review_code_change({
        "requester_id": "test-agent",
        "change_type": "new_code",
        "description": "Add config",
        "target_files": ["config.py"],
        "code_content": 'api_key = "sk-abc123456789"'
    })
    assert result["approved"] == False, "Should detect hardcoded secret"
    print("  [OK] Secret detection works")
    
    # Test 3: Safe code should pass
    result = await reviewer.review_code_change({
        "requester_id": "test-agent",
        "change_type": "edit",
        "description": "Fix typo",
        "target_files": ["mycosoft_mas/utils/helpers.py"],
        "code_content": "def helper(): return True"
    })
    assert result["approved"] == True, "Safe code should be approved"
    print("  [OK] Safe code approved")
    
    print("  SecurityCodeReviewer: ALL TESTS PASSED")
    return True

async def test_vulnerability_scanner():
    """Test VulnerabilityScanner functionality"""
    print("\n[2/4] Testing VulnerabilityScanner...")
    
    from mycosoft_mas.security.vulnerability_scanner import VulnerabilityScanner
    
    scanner = VulnerabilityScanner()
    
    # Test 1: Check scanner has required methods
    assert hasattr(scanner, 'scan_file'), "Should have scan_file method"
    assert hasattr(scanner, 'scan_directory'), "Should have scan_directory method"
    assert hasattr(scanner, 'full_scan'), "Should have full_scan method"
    print("  [OK] Scanner has required methods")
    
    # Test 2: Check scanner patterns are configured
    assert len(scanner.OWASP_PATTERNS) > 0, "Should have OWASP patterns"
    assert len(scanner.SECRET_PATTERNS) > 0, "Should have secret patterns"
    print("  [OK] Scanner patterns configured")
    
    # Test 3: Check scanner can initialize
    assert scanner.scan_history is not None, "Should have scan history"
    print("  [OK] Scanner initialized correctly")
    
    print("  VulnerabilityScanner: ALL TESTS PASSED")
    return True

async def test_code_modification_service():
    """Test CodeModificationService structure"""
    print("\n[3/4] Testing CodeModificationService...")
    
    from mycosoft_mas.services.code_modification_service import CodeModificationService
    
    service = CodeModificationService()
    
    # Test service initialization
    assert hasattr(service, 'request_code_change'), "Should have request_code_change method"
    assert hasattr(service, 'get_change_status'), "Should have get_change_status method"
    assert hasattr(service, 'halt_all_changes'), "Should have halt_all_changes method"
    print("  [OK] Service has required methods")
    
    # Test class-level constants
    assert hasattr(CodeModificationService, 'MAX_BUDGET_PER_REQUEST'), "Should have MAX_BUDGET_PER_REQUEST"
    assert hasattr(CodeModificationService, 'PR_REQUIRED_PATHS'), "Should have PR_REQUIRED_PATHS"
    assert CodeModificationService.MAX_BUDGET_PER_REQUEST == 5.0, "Budget limit should be $5"
    assert "mycosoft_mas/core/" in CodeModificationService.PR_REQUIRED_PATHS, "Core path should require PR"
    print("  [OK] Service constants configured correctly")
    
    print("  CodeModificationService: ALL TESTS PASSED")
    return True

async def test_self_healing_monitor():
    """Test SelfHealingMonitor structure"""
    print("\n[4/4] Testing SelfHealingMonitor...")
    
    from mycosoft_mas.services.self_healing_monitor import SelfHealingMonitor
    
    monitor = SelfHealingMonitor()
    
    # Test monitor initialization
    assert hasattr(monitor, 'start_monitoring'), "Should have start_monitoring method"
    assert hasattr(monitor, 'handle_agent_crash'), "Should have handle_agent_crash method"
    assert hasattr(monitor, 'handle_security_vulnerability'), "Should have handle_security_vulnerability method"
    print("  [OK] Monitor has required methods")
    
    # Test class-level constants
    assert hasattr(SelfHealingMonitor, 'ERROR_THRESHOLD'), "Should have ERROR_THRESHOLD"
    assert hasattr(SelfHealingMonitor, 'CHECK_INTERVAL'), "Should have CHECK_INTERVAL"
    assert SelfHealingMonitor.ERROR_THRESHOLD == 3, "Error threshold should be 3"
    assert SelfHealingMonitor.CHECK_INTERVAL == 60, "Check interval should be 60 seconds"
    print("  [OK] Monitor constants configured correctly")
    
    print("  SelfHealingMonitor: ALL TESTS PASSED")
    return True

async def main():
    print("=" * 60)
    print("SELF-HEALING MAS INFRASTRUCTURE - TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("SecurityCodeReviewer", test_security_code_reviewer),
        ("VulnerabilityScanner", test_vulnerability_scanner),
        ("CodeModificationService", test_code_modification_service),
        ("SelfHealingMonitor", test_self_healing_monitor),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            result = await test_fn()
            if result:
                passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("\n[SUCCESS] All self-healing infrastructure tests passed!")
        print("\nNext steps:")
        print("  1. Push code to GitHub: git push origin main")
        print("  2. Deploy to MAS VM: ssh mycosoft@192.168.0.188")
        print("     cd /home/mycosoft/mycosoft/mas && git pull")
        print("     sudo systemctl restart mas-orchestrator")
        print("  3. Test endpoints at http://192.168.0.188:8001/api/code/")
        return 0
    else:
        print("\n[ERROR] Some tests failed. Please fix before deploying.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
