#!/usr/bin/env python3
"""
Simple test script to verify live reloading works
"""

import time
import requests

def test_health_endpoint():
    """Test the health endpoint"""
    try:
        response = requests.get("http://localhost:8000/api/v1/health/simple", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed!")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"❌ Health check failed with status: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check failed with error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Document Converter API...")
    test_health_endpoint()
