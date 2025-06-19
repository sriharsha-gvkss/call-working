#!/usr/bin/env python
"""
Quick database fix script for Render
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_team.settings')
django.setup()

from django.core.management import execute_from_command_line
from django.db import connection

def fix_database():
    print("🔧 Fixing database...")
    
    try:
        # Run migrations
        print("📦 Running migrations...")
        execute_from_command_line(['manage.py', 'migrate'])
        print("✅ Migrations completed!")
        
        # Verify tables exist
        print("🔍 Checking tables...")
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            if 'call_callresponse' in tables:
                print("✅ call_callresponse table exists!")
            else:
                print("❌ call_callresponse table missing!")
                
            if 'django_session' in tables:
                print("✅ django_session table exists!")
            else:
                print("❌ django_session table missing!")
        
        print("🎉 Database fix completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == '__main__':
    fix_database() 