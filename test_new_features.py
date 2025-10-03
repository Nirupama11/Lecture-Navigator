#!/usr/bin/env python3
"""
Simple test script to verify the new features work correctly.
Run this after starting the backend server.
"""

import requests
import json

API_BASE = "http://localhost:8000/api"

def test_history_endpoint():
    """Test the history endpoint"""
    print("Testing history endpoint...")
    try:
        response = requests.get(f"{API_BASE}/history")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ History endpoint works! Found {len(data.get('videos', []))} videos")
            return True
        else:
            print(f"❌ History endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ History endpoint error: {e}")
        return False

def test_upload_endpoint():
    """Test the upload endpoint (without actually uploading)"""
    print("Testing upload endpoint structure...")
    try:
        # This will fail but should give us a proper error about missing file
        response = requests.post(f"{API_BASE}/upload_video")
        if response.status_code == 422:  # Validation error for missing file
            print("✅ Upload endpoint is properly configured (expects file)")
            return True
        else:
            print(f"❌ Upload endpoint unexpected response: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Upload endpoint error: {e}")
        return False

def main():
    print("Testing new Lecture Navigator features...\n")
    
    history_ok = test_history_endpoint()
    upload_ok = test_upload_endpoint()
    
    print(f"\nResults:")
    print(f"History API: {'✅ Working' if history_ok else '❌ Failed'}")
    print(f"Upload API: {'✅ Working' if upload_ok else '❌ Failed'}")
    
    if history_ok and upload_ok:
        print("\n🎉 All new features are ready to use!")
        print("\nYou can now:")
        print("1. View your video history/library in the frontend")
        print("2. Upload local video files for processing")
    else:
        print("\n⚠️  Some features may not work properly. Check the backend server.")

if __name__ == "__main__":
    main()
