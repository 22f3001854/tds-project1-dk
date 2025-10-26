#!/usr/bin/env python3

import requests
import json
import time

def test_hf_deployment():
    """Test the deployed Hugging Face app functionality."""
    
    print("🚀 Testing Hugging Face Deployment")
    print("=" * 50)
    
    # HF Space URL
    hf_url = "https://22f3001854-tds-project1-dk.hf.space"
    
    # Test 1: Check if the app is running
    print("📡 Test 1: Health Check")
    try:
        response = requests.get(f"{hf_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health check passed - App is running")
        else:
            print(f"⚠️  Health check returned status: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
    
    print()
    
    # Test 2: Test the universal prompt functionality
    print("🧪 Test 2: Universal Prompt Processing")
    
    test_payload = {
        "email": "22f3001854@ds.study.iitm.ac.in",
        "secret": "YaarThachaSattaiThathaThachaSattai",
        "task": "universal_test_hf",
        "brief": "Create a web app with multiple files: data.json, styles.css, and script.js. Include SEC API integration with these IDs: id=\"share-entity-name\", id=\"share-max-value\", id=\"share-min-value\". Make it responsive with Bootstrap.",
        "round": 1,
        "nonce": "nonce-hf-test-universal",
        "evaluation_url": "https://universal-hf-test.github.io",
        "attachments": [],
        "checks": ["share-entity-name", "share-max-value", "share-min-value"]
    }
    
    try:
        print(f"📤 Sending request to: {hf_url}/handle_task")
        response = requests.post(
            f"{hf_url}/handle_task",
            headers={
                "Content-Type": "application/json"
            },
            json=test_payload,
            timeout=60  # Increased timeout for HF
        )
        
        print(f"📥 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Universal processing successful!")
            print(f"📄 Response keys: {list(result.keys())}")
            
            if 'repo_url' in result:
                print(f"🔗 Repository URL: {result['repo_url']}")
            if 'pages_url' in result:
                print(f"🌐 Pages URL: {result['pages_url']}")
            if 'message' in result:
                print(f"💬 Message: {result['message']}")
                
        else:
            print(f"❌ Request failed with status: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out - HF might be starting up")
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    print()
    
    # Test 3: Check if generated repository exists
    print("🔍 Test 3: Repository Verification")
    repo_url = "https://universal-hf-test.github.io"
    try:
        response = requests.get(repo_url, timeout=10)
        if response.status_code == 200:
            print("✅ Generated repository is accessible")
            # Check for required IDs in the HTML
            html_content = response.text
            required_ids = ["share-entity-name", "share-max-value", "share-min-value"]
            found_ids = []
            
            for req_id in required_ids:
                if f'id="{req_id}"' in html_content:
                    found_ids.append(req_id)
            
            print(f"🎯 Required IDs found: {len(found_ids)}/{len(required_ids)}")
            if found_ids:
                print(f"   ✓ Found: {found_ids}")
            
            missing_ids = [id for id in required_ids if id not in found_ids]
            if missing_ids:
                print(f"   ⚠️  Missing: {missing_ids}")
                
        else:
            print(f"⚠️  Repository returned status: {response.status_code}")
    except Exception as e:
        print(f"❌ Repository check failed: {e}")
    
    print()
    print("🏁 HF Deployment Test Complete")

if __name__ == "__main__":
    test_hf_deployment()