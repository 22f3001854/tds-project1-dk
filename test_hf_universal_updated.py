#!/usr/bin/env python3

import requests
import json
import time

def test_hf_universal_deployment():
    """Test the updated HF deployment with universal generator."""
    
    print("🚀 Testing Updated Hugging Face Deployment")
    print("=" * 60)
    
    hf_url = "https://22f3001854-tds-project1-dk.hf.space"
    
    # Test the universal prompt
    test_payload = {
        "email": "22f3001854@ds.study.iitm.ac.in",
        "secret": "YaarThachaSattaiThathaThachaSattai",
        "task": "universal_hf_test",
        "brief": "Create a ShareVolume web app with SEC API integration. Include these specific IDs: id=\"share-entity-name\", id=\"share-max-value\", id=\"share-max-fy\", id=\"share-min-value\", and id=\"share-min-fy\". Create additional files: config.json, styles.css, and data.js for a complete multi-file application.",
        "round": 1,
        "nonce": "nonce-universal-hf-test-2025",
        "evaluation_url": "https://universal-hf-test-2025.github.io",
        "attachments": [],
        "checks": ["share-entity-name", "share-max-value", "share-max-fy", "share-min-value", "share-min-fy"]
    }
    
    # Try new endpoint first (/process)
    print("🧪 Testing new endpoint: /process")
    try:
        response = requests.post(
            f"{hf_url}/process",
            headers={
                "Content-Type": "application/json",
                "X-App-Secret": "test123"
            },
            json=test_payload,
            timeout=60
        )
        
        if response.status_code == 200:
            print("✅ New /process endpoint working!")
            result = response.json()
            print(f"📄 Response keys: {list(result.keys())}")
            
            if 'repo_url' in result:
                print(f"🔗 Repository: {result['repo_url']}")
            if 'pages_url' in result:
                print(f"🌐 Pages: {result['pages_url']}")
                
            return True
            
        elif response.status_code == 404:
            print("⚠️  /process endpoint not found, trying old endpoint...")
            
        else:
            print(f"❌ /process endpoint returned: {response.status_code}")
            
    except Exception as e:
        print(f"❌ /process endpoint failed: {e}")
    
    # Fallback to old endpoint (/handle_task)
    print("\n🔄 Testing old endpoint: /handle_task")
    try:
        response = requests.post(
            f"{hf_url}/handle_task",
            headers={"Content-Type": "application/json"},
            json=test_payload,
            timeout=60
        )
        
        if response.status_code == 200:
            print("✅ Old /handle_task endpoint working!")
            result = response.json()
            print(f"📄 Response keys: {list(result.keys())}")
            print("⚠️  Note: This is using the old implementation without universal generator")
            return False
            
        else:
            print(f"❌ /handle_task endpoint returned: {response.status_code}")
            
    except Exception as e:
        print(f"❌ /handle_task endpoint failed: {e}")
    
    print("\n❌ Both endpoints failed - deployment may still be updating")
    return False

def check_deployment_status():
    """Check if HF Spaces is still deploying."""
    print("\n🔍 Checking deployment status...")
    
    try:
        response = requests.get("https://22f3001854-tds-project1-dk.hf.space/health", timeout=10)
        if response.status_code == 200:
            print("✅ App is healthy and responding")
        else:
            print(f"⚠️  Health check returned: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")

if __name__ == "__main__":
    success = test_hf_universal_deployment()
    check_deployment_status()
    
    if not success:
        print("\n💡 Tip: HF Spaces deployment may take 5-10 minutes to update")
        print("   Try running this test again in a few minutes")
    else:
        print("\n🎉 Universal generator is working on HF Spaces!")