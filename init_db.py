#!/usr/bin/env python
"""
Database initialization script for Render deployment
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_team.settings')
django.setup()

from django.core.management import execute_from_command_line
from django.db import connection
from django.db.utils import OperationalError

def check_database():
    """Check if database is accessible"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            print("✅ Database connection successful")
            return True
    except OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        return False

def run_migrations():
    """Run all migrations"""
    print("🔄 Running migrations...")
    try:
        execute_from_command_line(['manage.py', 'migrate', '--verbosity=2'])
        print("✅ Migrations completed successfully")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def verify_tables():
    """Verify that required tables exist"""
    print("🔍 Verifying tables...")
    try:
        with connection.cursor() as cursor:
            # Check if call_callresponse table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='call_callresponse'
            """)
            result = cursor.fetchone()
            if result:
                print("✅ call_callresponse table exists")
            else:
                print("❌ call_callresponse table does not exist")
                return False
            
            # Check if django_session table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='django_session'
            """)
            result = cursor.fetchone()
            if result:
                print("✅ django_session table exists")
            else:
                print("❌ django_session table does not exist")
                return False
                
            return True
    except Exception as e:
        print(f"❌ Table verification failed: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Starting database initialization...")
    
    # Check database connection
    if not check_database():
        sys.exit(1)
    
    # Run migrations
    if not run_migrations():
        sys.exit(1)
    
    # Verify tables
    if not verify_tables():
        print("⚠️  Some tables are missing. Trying to recreate database...")
        # Try to recreate the database
        try:
            execute_from_command_line(['manage.py', 'migrate', '--run-syncdb'])
            print("✅ Database recreated successfully")
        except Exception as e:
            print(f"❌ Database recreation failed: {e}")
            sys.exit(1)
    
    print("🎉 Database initialization completed successfully!") 