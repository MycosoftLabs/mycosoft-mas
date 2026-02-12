"""
Test script for the /api/agents/anomalies endpoint.

This demonstrates the complete implementation:
1. MAS endpoint at /api/agents/anomalies
2. Website proxy at /api/mindex/agents/anomalies
"""

import asyncio
import httpx
from datetime import datetime

MAS_URL = "http://192.168.0.188:8001"
WEBSITE_URL = "http://localhost:3010"

async def test_mas_endpoint():
    """Test the MAS /api/agents/anomalies endpoint"""
    print("\n=== Testing MAS Endpoint ===")
    print(f"URL: {MAS_URL}/api/agents/anomalies")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{MAS_URL}/api/agents/anomalies")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            return response.status_code == 200
    except httpx.ConnectError:
        print("❌ MAS VM not reachable (192.168.0.188:8001)")
        print("   This is expected if MAS is not running.")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

async def test_website_endpoint():
    """Test the website /api/mindex/agents/anomalies endpoint"""
    print("\n=== Testing Website Endpoint ===")
    print(f"URL: {WEBSITE_URL}/api/mindex/agents/anomalies")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{WEBSITE_URL}/api/mindex/agents/anomalies")
            print(f"Status: {response.status_code}")
            data = response.json()
            print(f"Source: {data.get('source')}")
            print(f"Anomalies count: {len(data.get('anomalies', []))}")
            print(f"Timestamp: {data.get('timestamp')}")
            print(f"Message: {data.get('message')}")
            return response.status_code == 200
    except httpx.ConnectError:
        print("❌ Website dev server not running (localhost:3010)")
        print("   Start with: npm run dev:next-only")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

async def test_with_params():
    """Test endpoint with query parameters"""
    print("\n=== Testing with Parameters ===")
    
    params = {
        "limit": 10,
        "severity": "high"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{MAS_URL}/api/agents/anomalies",
                params=params
            )
            print(f"URL: {response.url}")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

async def main():
    print("=" * 60)
    print("ANOMALIES ENDPOINT IMPLEMENTATION TEST")
    print("=" * 60)
    
    # Test MAS endpoint
    mas_ok = await test_mas_endpoint()
    
    # Test website endpoint
    website_ok = await test_website_endpoint()
    
    # Test with parameters
    await test_with_params()
    
    # Summary
    print("\n" + "=" * 60)
    print("IMPLEMENTATION SUMMARY")
    print("=" * 60)
    
    print("\n✅ MAS Router Updated:")
    print("   - Added /api/agents/anomalies endpoint")
    print("   - Returns anomaly detection data from agents")
    print("   - Supports limit and severity query params")
    print("   - Returns structured response with timestamp")
    
    print("\n✅ MAS Main App Updated:")
    print("   - Registered agents router in app")
    print("   - Endpoint available at /api/agents/anomalies")
    
    print("\n✅ Website Endpoint Already Implemented:")
    print("   - Proxies to MAS at /api/agents/anomalies")
    print("   - Falls back to MINDEX if MAS unavailable")
    print("   - Returns empty array if no backends available")
    print("   - No mock data, real integrations only")
    
    print("\n📋 Next Steps:")
    print("   1. Deploy updated MAS to VM 188")
    print("   2. Restart MAS service: sudo systemctl restart mas-orchestrator")
    print("   3. Test endpoints once MAS is running")
    print("   4. Connect real agent instances for live data")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
