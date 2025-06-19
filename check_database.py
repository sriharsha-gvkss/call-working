#!/usr/bin/env python3
"""
Database health check script
"""

import os
import sys
import django
from django.conf import settings
from django.db import connection

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_team.settings')
django.setup()

def check_database():
    """Check database health and table existence"""
    print("🔍 Checking database health...")
    
    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            print("✓ Database connection: OK")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False
    
    # Check CallResponse table
    try:
        with connection.cursor() as cursor:
            if 'sqlite' in settings.DATABASES['default']['ENGINE'].lower():
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='call_callresponse'")
            else:
                cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename='call_callresponse'")
            
            if cursor.fetchone():
                print("✓ CallResponse table: EXISTS")
                
                # Check table structure
                cursor.execute("PRAGMA table_info(call_callresponse)" if 'sqlite' in settings.DATABASES['default']['ENGINE'].lower() else "SELECT column_name FROM information_schema.columns WHERE table_name='call_callresponse'")
                columns = cursor.fetchall()
                print(f"✓ Table columns: {len(columns)} columns found")
                
                return True
            else:
                print("✗ CallResponse table: MISSING")
                return False
    except Exception as e:
        print(f"✗ Error checking table: {e}")
        return False

if __name__ == "__main__":
    success = check_database()
    if success:
        print("\n🎉 Database is healthy!")
        sys.exit(0)
    else:
        print("\n❌ Database has issues!")
        sys.exit(1) 