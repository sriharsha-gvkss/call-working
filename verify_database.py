#!/usr/bin/env python
"""
Comprehensive database verification and fix script for Render deployment
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
from django.apps import apps

def check_database_connection():
    """Step 1: Verify database connection"""
    print("🔍 Step 1: Checking database connection...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            print("✅ Database connection successful")
            return True
    except OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        return False

def list_all_tables():
    """Step 2: List all tables in database"""
    print("\n🔍 Step 2: Listing all tables...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
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

def check_model_definition():
    """Step 3: Verify model definition"""
    print("\n🔍 Step 3: Checking model definition...")
    try:
        # Check if the app is installed
        if 'call' in apps.all_models:
            print("✅ 'call' app is properly installed")
            
            # Check if CallResponse model exists
            try:
                model = apps.get_model('call', 'CallResponse')
                print("✅ CallResponse model is properly defined")
                print(f"   - Model fields: {[field.name for field in model._meta.fields]}")
                return True
            except LookupError:
                print("❌ CallResponse model not found")
                return False
        else:
            print("❌ 'call' app not found in installed apps")
            return False
    except Exception as e:
        print(f"❌ Error checking model: {e}")
        return False

def run_migrations():
    """Step 4: Run Django migrations"""
    print("\n🔄 Step 4: Running Django migrations...")
    try:
        # First, check if there are any pending migrations
        print("📋 Checking for pending migrations...")
        execute_from_command_line(['manage.py', 'showmigrations'])
        
        # Run migrations
        print("📦 Running migrations...")
        execute_from_command_line(['manage.py', 'migrate', '--verbosity=2'])
        print("✅ Migrations completed successfully")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def verify_table_structure():
    """Step 5: Verify table structure"""
    print("\n🔍 Step 5: Verifying table structure...")
    try:
        with connection.cursor() as cursor:
            # Check call_callresponse table structure
            cursor.execute("PRAGMA table_info(call_callresponse)")
            columns = cursor.fetchall()
            print(f"📋 call_callresponse table has {len(columns)} columns:")
            for col in columns:
                print(f"   - {col[1]} ({col[2]})")
            
            # Check if essential columns exist
            column_names = [col[1] for col in columns]
            essential_columns = ['id', 'phone_number', 'question', 'call_sid', 'created_at']
            missing_columns = [col for col in essential_columns if col not in column_names]
            
            if missing_columns:
                print(f"❌ Missing essential columns: {missing_columns}")
                return False
            else:
                print("✅ All essential columns present")
                return True
    except Exception as e:
        print(f"❌ Error checking table structure: {e}")
        return False

def create_table_manually():
    """Step 6: Manually create table if needed"""
    print("\n🔧 Step 6: Attempting manual table creation...")
    try:
        with connection.cursor() as cursor:
            # Create call_callresponse table manually
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS call_callresponse (
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
            print("✅ call_callresponse table created manually")
            return True
    except Exception as e:
        print(f"❌ Manual table creation failed: {e}")
        return False

def test_database_operations():
    """Step 7: Test database operations"""
    print("\n🧪 Step 7: Testing database operations...")
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
        
        # Clean up test record
        test_response.delete()
        print("✅ Successfully deleted test record")
        
        return True
    except Exception as e:
        print(f"❌ Database operation test failed: {e}")
        return False

def main():
    """Main execution function"""
    print("🚀 Starting comprehensive database verification and fix...")
    print("=" * 60)
    
    # Step 1: Check database connection
    if not check_database_connection():
        print("❌ Cannot proceed without database connection")
        return False
    
    # Step 2: List all tables
    tables = list_all_tables()
    
    # Step 3: Check model definition
    if not check_model_definition():
        print("❌ Model definition issues found")
        return False
    
    # Step 4: Run migrations
    if not run_migrations():
        print("❌ Migration issues found")
        return False
    
    # Step 5: Verify table structure
    if 'call_callresponse' not in tables:
        print("⚠️ call_callresponse table still missing after migrations")
        if not create_table_manually():
            print("❌ Manual table creation failed")
            return False
    
    if not verify_table_structure():
        print("❌ Table structure verification failed")
        return False
    
    # Step 6: Test database operations
    if not test_database_operations():
        print("❌ Database operation tests failed")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 Database verification and fix completed successfully!")
    print("✅ All steps passed - database is ready for use")
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1) 