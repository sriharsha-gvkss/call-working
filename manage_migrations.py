#!/usr/bin/env python
"""
Migration management script for Render deployment
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

if __name__ == '__main__':
    print("Running migrations...")
    execute_from_command_line(['manage.py', 'migrate'])
    print("Migrations completed!") 