#!/usr/bin/env python3
"""
Debug Shift Templates - Check the actual template data
"""

import requests
import json

def debug_templates():
    # Authenticate
    auth_result = requests.post("http://localhost:8001/api/auth/login", json={
        "email": "admin@carlsburg.de", 
        "password": "Carlsburg2025!"
    })
    
    if auth_result.status_code != 200:
        print("❌ Authentication failed")
        return
    
    token = auth_result.json()["access_token"]
    headers = {'Authorization': f'Bearer {token}'}
    
    # Get templates
    templates_result = requests.get("http://localhost:8001/api/staff/shift-templates", headers=headers)
    
    if templates_result.status_code != 200:
        print("❌ Failed to get templates")
        return
    
    templates = templates_result.json()
    
    print(f"Found {len(templates)} templates:")
    print("=" * 80)
    
    for i, template in enumerate(templates, 1):
        print(f"{i}. {template.get('name', 'Unknown')}")
        print(f"   Department: {template.get('department', 'N/A')}")
        print(f"   Event Mode: {template.get('event_mode', 'N/A')}")
        print(f"   End Time Type: {template.get('end_time_type', 'N/A')}")
        print(f"   Close Plus Minutes: {template.get('close_plus_minutes', 'UNDEFINED')}")
        print(f"   End Time Fixed: {template.get('end_time_fixed', 'N/A')}")
        print("-" * 40)

if __name__ == "__main__":
    debug_templates()