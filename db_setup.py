# db_setup.py
import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade

# Adjusting path to include the Flask app's directory
app_dir = '/var/www/nano_sync'
sys.path.append(app_dir)

from app import create_app, db  # Adjust if your import paths differ

app = create_app()

def setup_database():
    """Set up database by applying migrations."""
    with app.app_context():
        # Configure the migration directory
        migrations_dir = os.path.join(app_dir, 'migrations')
        migrate = Migrate(app, db, directory=migrations_dir)

        # Apply all migrations
        upgrade()
        print("Database is set up and migrations applied.")

if __name__ == "__main__":
    setup_database()
