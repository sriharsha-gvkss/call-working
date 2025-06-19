#!/usr/bin/env python3
"""
Test script to verify Twilio configuration
"""

import os
import sys
import django
from django.conf import settings

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_team.settings')
django.setup()

def test_twilio_config():
    """Test Twilio configuration"""
    print("Testing Twilio configuration...")
    
    # Check required settings
    required_settings = [
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN', 
        'TWILIO_PHONE_NUMBER',
        'PUBLIC_URL'
    ]
    
    missing_settings = []
    for setting in required_settings:
        if not hasattr(settings, setting) or not getattr(settings, setting):
            missing_settings.append(setting)
        else:
            value = getattr(settings, setting)
            # Mask sensitive values
            if 'AUTH_TOKEN' in setting:
                display_value = value[:4] + '***' if value else 'None'
            else:
                display_value = value
            print(f"✓ {setting}: {display_value}")
    
    if missing_settings:
        print(f"\n✗ Missing settings: {missing_settings}")
        return False
    
    # Test Twilio client creation
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        print("✓ Twilio client created successfully")
    except Exception as e:
        print(f"✗ Error creating Twilio client: {e}")
        return False
    
    # Test URL generation
    try:
        test_url = f"{settings.PUBLIC_URL}/voice?q=1&name=test"
        print(f"✓ URL generation works: {test_url}")
    except Exception as e:
        print(f"✗ Error generating URL: {e}")
        return False
    
    print("\n✓ Twilio configuration test passed!")
    return True

if __name__ == "__main__":
    test_twilio_config() 