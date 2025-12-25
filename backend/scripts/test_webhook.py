#!/usr/bin/env python3
"""
Test script for GitHub Triage Agent webhook
Simulates a GitHub webhook event for local testing
"""
import requests
import json
import hmac
import hashlib
import sys

# Test payload - simulates GitHub issue.opened event
PAYLOAD = {
    "action": "opened",
    "issue": {
        "id": 123456789,
        "number": 42,
        "title": "Bug: Application crashes on startup",
        "body": "When launching the application, it immediately crashes with a segmentation fault. This happens on Linux with Python 3.10. Steps to reproduce:\n1. Run `python main.py`\n2. Application crashes\n\nExpected: Application starts normally\nActual: Segmentation fault",
        "user": {
            "login": "test_user"
        },
        "state": "open",
        "labels": []
    },
    "repository": {
        "name": "test-repo",
        "full_name": "testuser/test-repo"
    }
}

def generate_signature(payload_bytes: bytes, secret: str) -> str:
    """Generate GitHub webhook signature"""
    signature = hmac.new(
        secret.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"

def test_webhook(url: str = "http://localhost:8000/webhook/github", secret: str = "test-secret"):
    """Send test webhook to backend"""
    payload_json = json.dumps(PAYLOAD)
    payload_bytes = payload_json.encode()
    
    signature = generate_signature(payload_bytes, secret)
    
    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": "issues",
        "X-Hub-Signature-256": signature
    }
    
    print(f"Sending test webhook to {url}...")
    print(f"Issue: #{PAYLOAD['issue']['number']} - {PAYLOAD['issue']['title']}")
    
    try:
        response = requests.post(url, data=payload_bytes, headers=headers)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
        if response.status_code == 200:
            print("\n✓ Webhook test successful!")
            print("Check the dashboard at http://localhost:3000 for real-time updates")
        else:
            print("\n✗ Webhook test failed!")
            
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Could not connect to backend")
        print("Make sure the backend is running: uvicorn main:app --reload")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test GitHub Triage Agent webhook")
    parser.add_argument("--url", default="http://localhost:8000/webhook/github", help="Webhook URL")
    parser.add_argument("--secret", default="test-secret", help="Webhook secret")
    
    args = parser.parse_args()
    
    test_webhook(args.url, args.secret)
