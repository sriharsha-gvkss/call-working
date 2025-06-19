#!/usr/bin/env python
"""
Comprehensive database debugging script for Render deployment
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_team.settings')
django.setup()

from django.core.management import execute_from_command_line
from django.db import connection
from django.db.utils import OperationalError
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def check_database_configuration():
    """Step 1: Check database configuration"""
    print("🔍 Step 1: Checking database configuration...")
    try:
        print(f"Database engine: {settings.DATABASES['default']['ENGINE']}")
        print(f"Database name: {settings.DATABASES['default']['NAME']}")
        print(f"Database host: {settings.DATABASES['default'].get('HOST', 'N/A')}")
        print(f"Database user: {settings.DATABASES['default'].get('USER', 'N/A')}")
        
        # Check if using SQLite
        if 'sqlite' in settings.DATABASES['default']['ENGINE'].lower():
            db_path = settings.DATABASES['default']['NAME']
            print(f"SQLite database path: {db_path}")
            if os.path.exists(db_path):
                print(f"✅ SQLite database file exists: {os.path.getsize(db_path)} bytes")
            else:
                print(f"❌ SQLite database file does not exist: {db_path}")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Error checking database configuration: {e}")
        return False

def test_database_connection():
    """Step 2: Test database connection"""
    print("\n🔍 Step 2: Testing database connection...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            print(f"✅ Database connection successful: {result}")
            return True
    except OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def list_all_tables():
    """Step 3: List all tables in database"""
    print("\n🔍 Step 3: Listing all tables...")
    try:
        with connection.cursor() as cursor:
            if 'sqlite' in settings.DATABASES['default']['ENGINE'].lower():
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            else:
                cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            
            tables = [row[0] for row in cursor.fetchall()]
            print(f"📋 Found {len(tables)} tables:")
            for table in sorted(tables):
                print(f"   - {table}")
            
            # Check for specific tables
            if 'call_callresponse' in tables:
                print("✅ call_callresponse table exists")
            else:
                print("❌ call_callresponse table missing")
                
            if 'django_session' in tables:
                print("✅ django_session table exists")
            else:
                print("❌ django_session table missing")
                
            return tables
    except Exception as e:
        print(f"❌ Error listing tables: {e}")
        return []

def check_migration_status():
    """Step 4: Check migration status"""
    print("\n🔍 Step 4: Checking migration status...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT app, name FROM django_migrations ORDER BY app, name")
            migrations = cursor.fetchall()
            print(f"📋 Found {len(migrations)} applied migrations:")
            
            call_migrations = [m for m in migrations if m[0] == 'call']
            print(f"   - call app migrations: {len(call_migrations)}")
            for migration in call_migrations:
                print(f"     * {migration[1]}")
            
            return call_migrations
    except Exception as e:
        print(f"❌ Error checking migrations: {e}")
        return []

def create_table_manually():
    """Step 5: Create table manually if missing"""
    print("\n🔧 Step 5: Creating table manually if needed...")
    try:
        with connection.cursor() as cursor:
            # Check if table exists
            if 'sqlite' in settings.DATABASES['default']['ENGINE'].lower():
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='call_callresponse'")
            else:
                cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename='call_callresponse'")
            
            if cursor.fetchone():
                print("✅ call_callresponse table already exists")
                return True
            
            # Create table manually
            if 'sqlite' in settings.DATABASES['default']['ENGINE'].lower():
                cursor.execute("""
                    CREATE TABLE call_callresponse (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        phone_number VARCHAR(20) NOT NULL,
                        question TEXT,
                        response TEXT,
                        recording_url VARCHAR(200),
                        recording_sid VARCHAR(100) UNIQUE,
                        recording_duration INTEGER,
                        transcript TEXT,
                        transcript_status VARCHAR(20) DEFAULT 'pending',
                        call_sid VARCHAR(100),
                        call_duration INTEGER,
                        call_status VARCHAR(20),
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            else:
                cursor.execute("""
                    CREATE TABLE call_callresponse (
                        id SERIAL PRIMARY KEY,
                        phone_number VARCHAR(20) NOT NULL,
                        question TEXT,
                        response TEXT,
                        recording_url VARCHAR(200),
                        recording_sid VARCHAR(100) UNIQUE,
                        recording_duration INTEGER,
                        transcript TEXT,
                        transcript_status VARCHAR(20) DEFAULT 'pending',
                        call_sid VARCHAR(100),
                        call_duration INTEGER,
                        call_status VARCHAR(20),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            
            print("✅ call_callresponse table created manually")
            return True
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        return False

def test_model_operations():
    """Step 6: Test model operations"""
    print("\n🧪 Step 6: Testing model operations...")
    try:
        from call.models import CallResponse
        
        # Test creating a record
        test_response = CallResponse.objects.create(
            phone_number='+1234567890',
            question='Test question',
            call_sid='test_call_sid',
            call_status='test'
        )
        print(f"✅ Successfully created test record with ID: {test_response.id}")
        
        # Test querying
        count = CallResponse.objects.count()
        print(f"✅ Successfully queried database. Total records: {count}")
        
        # Test dashboard query specifically
        responses = CallResponse.objects.all().order_by('-created_at')
        print(f"✅ Dashboard query successful. Found {responses.count()} responses")
        
        # Clean up test record
        test_response.delete()
        print("✅ Successfully deleted test record")
        
        return True
    except Exception as e:
        print(f"❌ Model operation test failed: {e}")
        return False

def run_migrations_force():
    """Step 7: Force run migrations"""
    print("\n🔄 Step 7: Force running migrations...")
    try:
        # Show current migration status
        print("📋 Current migration status:")
        execute_from_command_line(['manage.py', 'showmigrations'])
        
        # Run migrations with verbosity
        print("\n📦 Running migrations...")
        execute_from_command_line(['manage.py', 'migrate', '--verbosity=2'])
        
        print("✅ Migrations completed")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def main():
    """Main execution function"""
    print("🚀 Starting comprehensive database debugging...")
    print("=" * 60)
    
    # Step 1: Check database configuration
    if not check_database_configuration():
        print("❌ Database configuration issues found")
        return False
    
    # Step 2: Test database connection
    if not test_database_connection():
        print("❌ Cannot proceed without database connection")
        return False
    
    # Step 3: List all tables
    tables = list_all_tables()
    
    # Step 4: Check migration status
    call_migrations = check_migration_status()
    
    # Step 5: Create table manually if missing
    if 'call_callresponse' not in tables:
        print("⚠️ call_callresponse table missing, attempting manual creation...")
        if not create_table_manually():
            print("❌ Manual table creation failed")
            return False
    
    # Step 6: Force run migrations
    if not run_migrations_force():
        print("❌ Migration issues found")
        return False
    
    # Step 7: Test model operations
    if not test_model_operations():
        print("❌ Model operation tests failed")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 Database debugging completed successfully!")
    print("✅ All database operations working - dashboard should be functional")
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1) 