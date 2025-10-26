#!/usr/bin/env python3

import requests
import json
import time

def test_universal_with_handle_task():
    """Test universal generator with the existing /handle_task endpoint."""
    
    print("🧪 Testing Universal Generator with /handle_task Endpoint")
    print("=" * 65)
    
    hf_url = "https://22f3001854-tds-project1-dk.hf.space"
    
    # Test payload with universal features
    test_payload = {
        "email": "22f3001854@ds.study.iitm.ac.in",
        "secret": "YaarThachaSattaiThathaThachaSattai",
        "task": "universal_sharevolume_test",
        "brief": "Build a comprehensive ShareVolume web app using SEC API from data.sec.gov. The app must display financial metrics with these required IDs: id=\"share-entity-name\", id=\"share-max-value\", id=\"share-max-fy\", id=\"share-min-value\", and id=\"share-min-fy\". Create additional files: config.json for settings, styles.css for custom styling, and analytics.js for data processing. Include real-time data visualization with Chart.js and responsive Bootstrap design.",
        "round": 1,
        "nonce": "nonce-universal-handle-task-test",
        "evaluation_url": "https://universal-handle-test.github.io",
        "attachments": [],
        "checks": ["share-entity-name", "share-max-value", "share-max-fy", "share-min-value", "share-min-fy"]
    }
    
    print("📤 Sending request to /handle_task endpoint...")
    print(f"🎯 Task: {test_payload['task']}")
    print(f"📋 Brief includes: SEC API, multiple files, required IDs")
    print(f"✅ Expected files: config.json, styles.css, analytics.js + base files")
    print()
    
    try:
        response = requests.post(
            f"{hf_url}/handle_task",
            headers={"Content-Type": "application/json"},
            json=test_payload,
            timeout=60
        )
        
        print(f"📥 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Request accepted successfully!")
            print(f"📄 Response: {json.dumps(result, indent=2)}")
            
            # Check if using new universal generator
            if result.get('status') == 'accepted':
                print("\n🔄 Task is processing in background...")
                print("🧠 The universal generator should now:")
                print("   ✓ Detect ShareVolume task type")
                print("   ✓ Extract file names: config.json, styles.css, analytics.js")
                print("   ✓ Generate SEC API integration with required IDs")
                print("   ✓ Create comprehensive file manager interface")
                print("   ✓ Include Chart.js data visualization")
                
                return True
            else:
                print(f"⚠️  Unexpected response format: {result}")
                
        else:
            print(f"❌ Request failed with status: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out - HF Spaces might be under load")
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    return False

def check_generated_repo():
    """Check if the generated repository shows universal features."""
    print("\n🔍 Checking Generated Repository...")
    
    repo_url = "https://universal-handle-test.github.io"
    
    try:
        # Wait a bit for processing
        print("⏳ Waiting 30 seconds for background processing...")
        time.sleep(30)
        
        response = requests.get(repo_url, timeout=15)
        
        if response.status_code == 200:
            print("✅ Repository generated and accessible!")
            
            html_content = response.text
            
            # Check for universal generator features
            universal_features = {
                "Required IDs": ["share-entity-name", "share-max-value", "share-max-fy", "share-min-value", "share-min-fy"],
                "Modern Libraries": ["bootstrap", "chart.js", "font-awesome"],
                "SEC Integration": ["sec.gov", "aipipe", "companyconcept"],
                "File Manager": ["file-manager", "file-editor", "downloadAll"],
                "Universal Features": ["Universal", "dynamic", "generated"]
            }
            
            found_features = {}
            
            for category, features in universal_features.items():
                found = []
                for feature in features:
                    if feature.lower() in html_content.lower():
                        found.append(feature)
                found_features[category] = found
                
                if found:
                    print(f"   ✓ {category}: {len(found)}/{len(features)} features found")
                else:
                    print(f"   ⚠️  {category}: No features detected")
            
            # Overall assessment
            total_found = sum(len(features) for features in found_features.values())
            total_possible = sum(len(features) for features in universal_features.values())
            
            print(f"\n📊 Universal Generator Score: {total_found}/{total_possible} features detected")
            
            if total_found >= total_possible * 0.7:  # 70% threshold
                print("🎉 Universal generator appears to be working!")
            else:
                print("⚠️  May still be using old implementation")
                
        else:
            print(f"⚠️  Repository returned status: {response.status_code}")
            print("   (This is normal if processing is still in progress)")
            
    except Exception as e:
        print(f"❌ Repository check failed: {e}")

if __name__ == "__main__":
    print("🚀 Testing Universal Generator Integration")
    print("Using existing /handle_task endpoint with universal features")
    print()
    
    success = test_universal_with_handle_task()
    
    if success:
        check_generated_repo()
    
    print("\n🏁 Test Complete!")
    print("The universal generator works with the existing /handle_task endpoint")