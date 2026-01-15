#!/usr/bin/env python3
"""
Example usage script for the Fantasy Probability Calculator
Demonstrates basic functionality and usage patterns
"""

import os
import sys
from datetime import datetime
import logging

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fantasy_main import FantasyProbabilityApp
from fantasy_calculator import DatabaseManager
from models import PlayerStats
from odds_api import OddsManager
from espn_scraper import ESPNScraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def example_basic_usage():
    """Example of basic fantasy probability calculator usage"""
    print("=== Fantasy Probability Calculator - Basic Usage Example ===\n")
    
    # Initialize the app
    print("1. Initializing Fantasy Probability Calculator...")
    app = FantasyProbabilityApp()
    print("   Fantasy Probability Calculator initialized successfully\n")
    
    # Check API keys
    print("2. Checking API configuration...")
    required_key = 'THE_ODDS_API_KEY'
    optional_keys = ['ODDS_API_KEY', 'SPORTSDATA_API_KEY']
    
    if os.getenv(required_key) and os.getenv(required_key) != f'your_{required_key.lower()}_here':
        print(f"   {required_key} configured (REQUIRED)")
    else:
        print(f"   ERROR: {required_key} not configured (REQUIRED)")
        print("      Get your free key at: https://the-odds-api.com/")
    
    for key in optional_keys:
        if os.getenv(key) and os.getenv(key) != f'your_{key.lower()}_here':
            print(f"   {key} configured (optional)")
        else:
            print(f"   {key} not configured (optional - not required)")
    print()
    
    # Example: Update odds for NFL
    print("3. Updating NFL odds...")
    try:
        app.update_odds('nfl')
        print("   NFL odds updated successfully")
    except Exception as e:
        print(f"   WARNING: Error updating odds: {e}")
    print()
    
    # Example: Collect historical data
    print("4. Collecting historical data...")
    try:
        app.collect_historical_data('nfl', [2023])
        print("   Historical data collection completed")
    except Exception as e:
        print(f"   WARNING: Error collecting data: {e}")
    print()
    
    # Example: Analyze fantasy opportunities
    print("5. Analyzing fantasy opportunities...")
    try:
        opportunities = app.analyze_fantasy_opportunities('nfl')
        if opportunities:
            print(f"   Found {len(opportunities)} fantasy opportunities")
            print("   Top opportunities:")
            for i, opp in enumerate(opportunities[:3]):
                print(f"     {i+1}. {opp['selection']} @ {opp['odds']} (EV: {opp['expected_value']:.3f})")
        else:
            print("   No fantasy opportunities found")
    except Exception as e:
        print(f"   WARNING: Error analyzing opportunities: {e}")
    print()

def example_odds_conversion():
    """Example of odds conversion utilities"""
    print("=== Odds Conversion Example ===\n")
    
    odds_manager = OddsManager()
    
    # Example American odds
    american_odds = [150, -200, 110, -110]
    
    print("American Odds Conversion:")
    print("American | Decimal | Probability")
    print("-" * 35)
    
    for odds in american_odds:
        decimal = odds_manager.convert_american_to_decimal(odds)
        probability = odds_manager.convert_american_to_probability(odds)
        print(f"{odds:8} | {decimal:7.3f} | {probability:11.3f}")
    
    print()

def example_espn_scraping():
    """Example of ESPN data scraping"""
    print("=== ESPN Data Scraping Example ===\n")
    
    scraper = ESPNScraper(headless=True)
    
    print("1. Scraping NFL team standings...")
    try:
        teams = scraper.get_team_stats('nfl', '2023')
        if teams:
            print(f"   Scraped {len(teams)} NFL teams")
            print("   Top 5 teams by win percentage:")
            sorted_teams = sorted(teams, key=lambda x: x['win_percentage'], reverse=True)
            for i, team in enumerate(sorted_teams[:5]):
                print(f"     {i+1}. {team['team']}: {team['wins']}-{team['losses']} ({team['win_percentage']:.3f})")
        else:
            print("   WARNING: No team data retrieved")
    except Exception as e:
        print(f"   WARNING: Error scraping team data: {e}")
    
    print()

def example_database_operations():
    """Example of database operations"""
    print("=== Database Operations Example ===\n")
    
    db_manager = DatabaseManager()
    
    print("1. Database initialized successfully")
    print("2. Available tables:")
    print("   - teams: Team information")
    print("   - players: Player information")
    print("   - games: Game schedules")
    print("   - odds: Fantasy odds")
    print("   - historical_data: Historical game results")
    print()

def example_probability_calculation():
    """Example of probability calculation"""
    print("=== Probability Calculation Example ===\n")
    
    from probability_calculator import FantasyProbabilityCalculator, TeamStats, GameContext
    
    db_manager = DatabaseManager()
    prob_calculator = FantasyProbabilityCalculator(db_manager)
    
    # Create example team stats
    home_stats = TeamStats(
        team_id="KC",
        wins=12,
        losses=5,
        win_percentage=0.706,
        home_record=(7, 1),
        away_record=(5, 4),
        recent_form=[True, True, False, True, True],
        avg_points_for=28.5,
        avg_points_against=22.1,
        strength_of_schedule=0.6
    )
    
    away_stats = TeamStats(
        team_id="BUF",
        wins=11,
        losses=6,
        win_percentage=0.647,
        home_record=(6, 2),
        away_record=(5, 4),
        recent_form=[True, False, True, True, False],
        avg_points_for=26.8,
        avg_points_against=21.3,
        strength_of_schedule=0.55
    )
    
    # Create game context
    game_context = GameContext(
        home_team="Kansas City Chiefs",
        away_team="Buffalo Bills",
        home_team_stats=home_stats,
        away_team_stats=away_stats
    )
    
    print("1. Calculating game outcome probabilities...")
    try:
        ml_prob = prob_calculator.calculate_game_outcome_probability(game_context)
        print(f"   Home team win probability: {ml_prob['home_win_probability']:.3f}")
        print(f"   Away team win probability: {ml_prob['away_win_probability']:.3f}")
        print(f"   Confidence: {ml_prob['confidence']:.3f}")
    except Exception as e:
        print(f"   WARNING: Error calculating game outcome probability: {e}")
    
    print("\n2. Calculating point differential probability...")
    try:
        spread_prob = prob_calculator.calculate_point_differential_probability(game_context, -3.5)
        print(f"   Home team covers (-3.5): {spread_prob['home_covers_probability']:.3f}")
        print(f"   Away team covers (+3.5): {spread_prob['away_covers_probability']:.3f}")
        print(f"   Confidence: {spread_prob['confidence']:.3f}")
    except Exception as e:
        print(f"   WARNING: Error calculating point differential probability: {e}")
    
    print("\n3. Calculating total points probability...")
    try:
        total_prob = prob_calculator.calculate_total_points_probability(game_context, 48.5)
        print(f"   Over 48.5 probability: {total_prob['over_probability']:.3f}")
        print(f"   Under 48.5 probability: {total_prob['under_probability']:.3f}")
        print(f"   Expected total: {total_prob['expected_total']:.1f}")
        print(f"   Confidence: {total_prob['confidence']:.3f}")
    except Exception as e:
        print(f"   WARNING: Error calculating total points probability: {e}")
    
    print()

def main():
    """Run all examples"""
    print("Fantasy Probability Calculator - Example Usage\n")
    print("=" * 55)
    
    try:
        example_basic_usage()
        example_odds_conversion()
        example_espn_scraping()
        example_database_operations()
        example_probability_calculation()
        
        print("=" * 55)
        print("All examples completed successfully!")
        print("\nTo get started:")
        print("1. Set up your API keys in the .env file")
        print("2. Run: python fantasy_main.py update-odds --sport nfl")
        print("3. Run: python fantasy_main.py analyze --sport nfl")
        
    except Exception as e:
        logger.error(f"Error running examples: {e}")
        print(f"\nError: {e}")
        print("Please check your configuration and try again.")

if __name__ == "__main__":
    main()
