"""
Configuration file for RitaliTime Dash application
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# App configuration
APP_CONFIG = {
    'title': 'RitaliTime - Medication Timeline Simulator',
    'description': 'Simulate and visualize medication and stimulant effects throughout the day',
    'version': '2.0.0',
    'debug': True,
    'host': '127.0.0.1',
    'port': 8080,
    'external_stylesheets': ['https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css'],
    'external_scripts': [
        'https://unpkg.com/dexie@4.2.0/dist/dexie.js',
        'assets/persistence.js'
    ]
}

# Database configuration
DB_CONFIG = {
    'name': 'RitaliTimeDB',
    'version': 1,
    'tables': {
        'medications': '++id, time, medication_name, dosage, onset_time_min, peak_time_min, duration_min',
        'stimulants': '++id, time, stimulant_name, quantity, component_name, onset_time_min, peak_time_min, duration_min',
        'painkillers': '++id, time_hours, name, pills, dosage, onset_min, peak_time_min, duration_min',
        'app_settings': 'key, value',
        'user_preferences': 'key, value'
    }
}

# File paths
DATA_FILES = {
    'medications': BASE_DIR / 'medications.json',
    'profiles': BASE_DIR / 'profiles.json',
    'painkillers': BASE_DIR / 'painkillers.json'
}

# UI configuration
UI_CONFIG = {
    'theme': 'bootstrap',
    'primary_color': '#007bff',
    'secondary_color': '#6c757d',
    'success_color': '#28a745',
    'warning_color': '#ffc107',
    'danger_color': '#dc3545',
    'info_color': '#17a2b8'
}

# Timeline configuration
TIMELINE_CONFIG = {
    'default_hours': 24,
    'time_interval': 0.1,  # 6 minutes
    'max_doses': 20,
    'default_sleep_threshold': 0.3
}

# Validation rules
VALIDATION_RULES = {
    'dosage_min': 0.1,
    'dosage_max': 1000.0,
    'time_min': 0,
    'time_max': 1440,  # 24 hours in minutes
    'duration_min': 1,
    'duration_max': 1440
}

# Export/Import configuration
DATA_EXPORT_CONFIG = {
    'supported_formats': ['json'],
    'max_file_size': 10 * 1024 * 1024,  # 10MB
    'auto_backup': True,
    'backup_interval': 24 * 60 * 60  # 24 hours in seconds
}

# Development configuration
DEV_CONFIG = {
    'hot_reload': True,
    'debug_toolbar': True,
    'profiling': False,
    'log_level': 'INFO'
}

# Production configuration
PROD_CONFIG = {
    'hot_reload': False,
    'debug_toolbar': False,
    'profiling': False,
    'log_level': 'WARNING'
}

# Get current environment
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development').lower()

# Use appropriate config based on environment
if ENVIRONMENT == 'production':
    CURRENT_CONFIG = {**APP_CONFIG, **PROD_CONFIG}
else:
    CURRENT_CONFIG = {**APP_CONFIG, **DEV_CONFIG}
