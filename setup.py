#!/usr/bin/env python3
"""
Setup script for Fantasy Probability Calculator
Helps users configure the calculator and get started quickly
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("ERROR: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"Python version: {sys.version.split()[0]}")
    return True

def install_dependencies():
    """Install required dependencies"""
        print("\nInstalling dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Error installing dependencies: {e}")
        return False

def setup_environment():
    """Set up environment configuration"""
    print("\nSetting up environment configuration...")
    
    env_file = Path(".env")
    example_file = Path("config.env.example")
    
    if env_file.exists():
        print(".env file already exists")
        return True
    
    if not example_file.exists():
        print("ERROR: config.env.example file not found")
        return False
    
    # Copy example to .env
    try:
        with open(example_file, 'r') as src, open(env_file, 'w') as dst:
            dst.write(src.read())
        print("Created .env file from template")
        print("Please edit .env file with your API keys")
        return True
    except Exception as e:
        print(f"ERROR: Error creating .env file: {e}")
        return False

def check_api_keys():
    """Check if API keys are configured"""
    print("\nChecking API key configuration...")
    
    required_keys = {
        'THE_ODDS_API_KEY': 'The Odds API (https://the-odds-api.com/) - REQUIRED'
    }
    optional_keys = {
        'ODDS_API_KEY': 'OddsAPI.com (https://oddsapi.com/) - Optional',
        'SPORTSDATA_API_KEY': 'SportsData.io (https://sportsdata.io/) - Optional'
    }
    
    configured_keys = []
    missing_keys = []
    
    # Check required keys
    for key, description in required_keys.items():
        value = os.getenv(key)
        if value and value != f'your_{key.lower()}_here':
            configured_keys.append(key)
            print(f"{key}: Configured")
        else:
            missing_keys.append(key)
            print(f"ERROR: {key}: Not configured (REQUIRED)")
    
    # Check optional keys
    for key, description in optional_keys.items():
        value = os.getenv(key)
        if value and value != f'your_{key.lower()}_here':
            configured_keys.append(key)
            print(f"{key}: Configured (optional)")
        else:
            print(f"{key}: Not configured (optional - not required)")
    
    if missing_keys:
        print(f"\nTo get required API keys:")
        for key, description in required_keys.items():
            if key in missing_keys:
                print(f"   {key}: {description}")
    
    return len([k for k in configured_keys if k in required_keys]) > 0

def test_installation():
    """Test if the installation works"""
    print("\nTesting installation...")
    
    try:
        # Test imports
        from betting_bot import DatabaseManager
        from odds_api import OddsManager
        from espn_scraper import ESPNScraper
        from probability_calculator import FantasyProbabilityCalculator
        from main import FantasyProbabilityApp
        
        print("All modules imported successfully")
        
        # Test database initialization
        db = DatabaseManager()
        print("Database initialized successfully")
        
        # Test app initialization
        app = FantasyProbabilityApp()
        print("Fantasy probability calculator app initialized successfully")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Error testing installation: {e}")
        return False

def show_next_steps():
    """Show next steps to the user"""
    print("\nSetup completed successfully!")
    print("\nNext steps:")
    print("1. Edit .env file with your API keys")
    print("2. Run: python main.py status")
    print("3. Run: python main.py update-odds --sport nfl")
    print("4. Run: python main.py analyze --sport nfl")
    print("\nFor more information, see README.md")
    print("For issues, check the logs in fantasy_calculator.log")

def main():
    """Main setup function"""
    print("Fantasy Probability Calculator Setup")
    print("=" * 45)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Setup environment
    if not setup_environment():
        return False
    
    # Check API keys
    has_keys = check_api_keys()
    
    # Test installation
    if not test_installation():
        return False
    
    # Show next steps
    show_next_steps()
    
    if not has_keys:
        print("\nWARNING: No API keys configured. Some features may not work.")
        print("   Please add your API keys to the .env file before using the bot.")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
