#!/usr/bin/env python3
"""
Database initialization script for Render deployment
This script ensures the database is properly set up with all required tables
"""

import os
import sys
import django
from django.conf import settings
from django.db import connection
from django.core.management import execute_from_command_line

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_team.settings')
django.setup()

def init_database():
    """Initialize the database with all required tables"""
    print("🔧 Initializing database...")
    
    try:
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False
    
    # Check if CallResponse table exists
    try:
        with connection.cursor() as cursor:
            if 'sqlite' in settings.DATABASES['default']['ENGINE'].lower():
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='call_callresponse'")
            else:
                cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename='call_callresponse'")
            
            if cursor.fetchone():
                print("✓ CallResponse table already exists")
                return True
            else:
                print("⚠ CallResponse table does not exist, creating it...")
    except Exception as e:
        print(f"⚠ Error checking table existence: {e}")
    
    # Run migrations
    try:
        print("📦 Running migrations...")
        execute_from_command_line(['manage.py', 'migrate'])
        print("✓ Migrations completed successfully")
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        
        # Try to create table manually if migration fails
        try:
            print("🔨 Attempting to create table manually...")
            with connection.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS call_callresponse (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        phone_number VARCHAR(20) NOT NULL,
                        call_sid VARCHAR(50),
                        question TEXT,
                        response TEXT,
                        recording_sid VARCHAR(50),
                        recording_url TEXT,
                        recording_duration INTEGER,
                        transcript TEXT,
                        transcript_status VARCHAR(20) DEFAULT 'pending',
                        call_status VARCHAR(20) DEFAULT 'initiated',
                        call_duration INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print("✓ Table created manually")
        except Exception as manual_error:
            print(f"✗ Manual table creation failed: {manual_error}")
            return False
    
    # Verify table exists
    try:
        with connection.cursor() as cursor:
            if 'sqlite' in settings.DATABASES['default']['ENGINE'].lower():
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='call_callresponse'")
            else:
                cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename='call_callresponse'")
            
            if cursor.fetchone():
                print("✓ CallResponse table verified")
                return True
            else:
                print("✗ CallResponse table still does not exist")
                return False
    except Exception as e:
        print(f"✗ Error verifying table: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    if success:
        print("\n🎉 Database initialization completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Database initialization failed!")
        sys.exit(1) 