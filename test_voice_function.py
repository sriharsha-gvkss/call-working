#!/usr/bin/env python3
"""
Test script to verify voice function works correctly
"""

import os
import sys
import django
from django.test import RequestFactory
from django.conf import settings

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_team.settings')
django.setup()

from call.views import voice

def test_voice_function():
    """Test the voice function with different scenarios"""
    print("Testing voice function...")
    
    # Create a request factory
    factory = RequestFactory()
    
    # Test scenarios
    test_cases = [
        {
            'name': 'Initial greeting (q=0)',
            'method': 'GET',
            'params': {'q': '0', 'name': 'John'},
            'expected': 'welcome to the HR interview'
        },
        {
            'name': 'First question (q=1)',
            'method': 'GET',
            'params': {'q': '1', 'name': 'John'},
            'expected': 'tell us your full name'
        },
        {
            'name': 'Second question (q=2)',
            'method': 'GET',
            'params': {'q': '2', 'name': 'John'},
            'expected': 'work experience'
        },
        {
            'name': 'Final question (q=4)',
            'method': 'GET',
            'params': {'q': '4', 'name': 'John'},
            'expected': 'Goodbye'
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        
        try:
            # Create request
            if test_case['method'] == 'GET':
                request = factory.get('/voice/', test_case['params'])
            else:
                request = factory.post('/voice/', test_case['params'])
            
            # Call the voice function
            response = voice(request)
            
            # Check response
            if response.status_code == 200:
                content = response.content.decode('utf-8')
                if test_case['expected'].lower() in content.lower():
                    print(f"✓ PASS: Found expected text '{test_case['expected']}'")
                else:
                    print(f"✗ FAIL: Expected '{test_case['expected']}' not found in response")
                    print(f"Response content: {content[:200]}...")
            else:
                print(f"✗ FAIL: Response status {response.status_code}")
                
        except Exception as e:
            print(f"✗ ERROR: {str(e)}")
    
    print("\nVoice function test completed!")

if __name__ == "__main__":
    test_voice_function() 