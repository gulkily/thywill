#!/usr/bin/env python3
"""
Quick debugging helper for finding schema migration issues.
Run this to test various endpoints and catch errors automatically.
"""

import requests
import time
import subprocess
import sys

def test_endpoint(url, description=""):
    """Test an endpoint and return any errors"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 500:
            return f"❌ {description}: 500 Server Error"
        elif response.status_code in [200, 401, 403]:
            return f"✅ {description}: {response.status_code} (OK)"
        else:
            return f"⚠️  {description}: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return f"❌ {description}: Connection error - {e}"

def check_server_logs():
    """Check recent server logs for AttributeError"""
    try:
        # Get last 20 lines of logs
        result = subprocess.run(
            ["tail", "-20", "/tmp/thywill.log"], 
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and "AttributeError" in result.stdout:
            return f"🔍 Found AttributeError in logs:\n{result.stdout}"
    except:
        pass
    return None

def main():
    base_url = "http://localhost:8000"
    
    print("🔧 ThyWill Schema Migration Debug Helper")
    print("=" * 50)
    
    # Test various endpoints that are likely to trigger errors
    endpoints = [
        ("/", "Homepage"),
        ("/claim/test", "Claim page"),
        ("/auth/notifications", "Auth notifications"),
        ("/login", "Login page"),
    ]
    
    for path, desc in endpoints:
        result = test_endpoint(f"{base_url}{path}", desc)
        print(result)
        time.sleep(0.1)  # Small delay between requests
    
    # Check logs for any new AttributeErrors
    log_check = check_server_logs()
    if log_check:
        print("\n" + log_check)
    
    print("\n💡 If you see 500 errors above, check the server logs:")
    print("   tail -f /var/log/thywill.log")
    print("   OR check the terminal where you're running the server")

if __name__ == "__main__":
    main()