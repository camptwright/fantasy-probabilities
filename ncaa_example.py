#!/usr/bin/env python3
"""
NCAA Sports Betting Bot - Example Usage
Demonstrates NCAA Football and Basketball specific functionality
"""

import os
import sys
from datetime import datetime
import logging

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import BettingBotApp
from betting_bot import DatabaseManager
from odds_api import OddsManager
from espn_scraper import ESPNScraper
from probability_calculator import ProbabilityCalculator, TeamStats, GameContext

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def example_ncaa_football_analysis():
    """Example of NCAA Football analysis"""
    print("=== NCAA Football Analysis Example ===\n")
    
    prob_calculator = ProbabilityCalculator(DatabaseManager())
    
    # Create example NCAA Football team stats
    alabama_stats = TeamStats(
        team_id="ALA",
        wins=11,
        losses=1,
        win_percentage=0.917,
        home_record=(6, 0),
        away_record=(5, 1),
        recent_form=[True, True, True, True, True],
        avg_points_for=35.2,
        avg_points_against=18.5,
        strength_of_schedule=0.85,
        conference="SEC",
        ranking=2,
        is_home_team=True
    )
    
    georgia_stats = TeamStats(
        team_id="UGA",
        wins=12,
        losses=0,
        win_percentage=1.000,
        home_record=(7, 0),
        away_record=(5, 0),
        recent_form=[True, True, True, True, True],
        avg_points_for=38.1,
        avg_points_against=16.2,
        strength_of_schedule=0.80,
        conference="SEC",
        ranking=1,
        is_home_team=False
    )
    
    # Create game context for SEC Championship
    game_context = GameContext(
        home_team="Alabama Crimson Tide",
        away_team="Georgia Bulldogs",
        home_team_stats=alabama_stats,
        away_team_stats=georgia_stats,
        sport="ncaaf",
        conference_game=True,
        rivalry_game=True,
        weather={"temperature": 45, "wind_speed": 8}
    )
    
    print("1. SEC Championship Game Analysis:")
    print(f"   {game_context.home_team} vs {game_context.away_team}")
    print(f"   Conference Game: {game_context.conference_game}")
    print(f"   Rivalry Game: {game_context.rivalry_game}")
    print(f"   Weather: {game_context.weather['temperature']}°F, {game_context.weather['wind_speed']} mph wind")
    print()
    
    # Calculate moneyline probability
    print("2. Moneyline Probability Calculation:")
    ml_prob = prob_calculator.calculate_moneyline_probability(game_context)
    print(f"   Alabama win probability: {ml_prob['home_win_probability']:.3f}")
    print(f"   Georgia win probability: {ml_prob['away_win_probability']:.3f}")
    print(f"   Confidence: {ml_prob['confidence']:.3f}")
    print()
    
    # Calculate spread probability
    print("3. Spread Analysis (-3.5 Alabama):")
    spread_prob = prob_calculator.calculate_spread_probability(game_context, -3.5)
    print(f"   Alabama covers (-3.5): {spread_prob['home_covers_probability']:.3f}")
    print(f"   Georgia covers (+3.5): {spread_prob['away_covers_probability']:.3f}")
    print(f"   Confidence: {spread_prob['confidence']:.3f}")
    print()
    
    # Calculate total probability
    print("4. Total Analysis (Over/Under 58.5):")
    total_prob = prob_calculator.calculate_total_probability(game_context, 58.5)
    print(f"   Over 58.5 probability: {total_prob['over_probability']:.3f}")
    print(f"   Under 58.5 probability: {total_prob['under_probability']:.3f}")
    print(f"   Expected total: {total_prob['expected_total']:.1f}")
    print(f"   Confidence: {total_prob['confidence']:.3f}")
    print()

def example_ncaa_basketball_analysis():
    """Example of NCAA Basketball analysis"""
    print("=== NCAA Basketball Analysis Example ===\n")
    
    prob_calculator = ProbabilityCalculator(DatabaseManager())
    
    # Create example NCAA Basketball team stats
    duke_stats = TeamStats(
        team_id="DUKE",
        wins=24,
        losses=6,
        win_percentage=0.800,
        home_record=(15, 1),
        away_record=(9, 5),
        recent_form=[True, True, False, True, True],
        avg_points_for=78.5,
        avg_points_against=68.2,
        strength_of_schedule=0.75,
        conference="ACC",
        ranking=8,
        is_home_team=True
    )
    
    unc_stats = TeamStats(
        team_id="UNC",
        wins=22,
        losses=8,
        win_percentage=0.733,
        home_record=(14, 2),
        away_record=(8, 6),
        recent_form=[True, False, True, True, False],
        avg_points_for=76.8,
        avg_points_against=70.1,
        strength_of_schedule=0.78,
        conference="ACC",
        ranking=12,
        is_home_team=False
    )
    
    # Create game context for Duke vs UNC rivalry
    game_context = GameContext(
        home_team="Duke Blue Devils",
        away_team="North Carolina Tar Heels",
        home_team_stats=duke_stats,
        away_team_stats=unc_stats,
        sport="ncaab",
        conference_game=True,
        rivalry_game=True
    )
    
    print("1. Duke vs UNC Rivalry Analysis:")
    print(f"   {game_context.home_team} vs {game_context.away_team}")
    print(f"   Conference Game: {game_context.conference_game}")
    print(f"   Rivalry Game: {game_context.rivalry_game}")
    print()
    
    # Calculate moneyline probability
    print("2. Moneyline Probability Calculation:")
    ml_prob = prob_calculator.calculate_moneyline_probability(game_context)
    print(f"   Duke win probability: {ml_prob['home_win_probability']:.3f}")
    print(f"   UNC win probability: {ml_prob['away_win_probability']:.3f}")
    print(f"   Confidence: {ml_prob['confidence']:.3f}")
    print()
    
    # Calculate spread probability
    print("3. Spread Analysis (-4.5 Duke):")
    spread_prob = prob_calculator.calculate_spread_probability(game_context, -4.5)
    print(f"   Duke covers (-4.5): {spread_prob['home_covers_probability']:.3f}")
    print(f"   UNC covers (+4.5): {spread_prob['away_covers_probability']:.3f}")
    print(f"   Confidence: {spread_prob['confidence']:.3f}")
    print()
    
    # Calculate total probability
    print("4. Total Analysis (Over/Under 152.5):")
    total_prob = prob_calculator.calculate_total_probability(game_context, 152.5)
    print(f"   Over 152.5 probability: {total_prob['over_probability']:.3f}")
    print(f"   Under 152.5 probability: {total_prob['under_probability']:.3f}")
    print(f"   Expected total: {total_prob['expected_total']:.1f}")
    print(f"   Confidence: {total_prob['confidence']:.3f}")
    print()

def example_conference_strength():
    """Example of conference strength analysis"""
    print("=== Conference Strength Analysis ===\n")
    
    prob_calculator = ProbabilityCalculator(DatabaseManager())
    
    conferences = ["SEC", "Big Ten", "ACC", "Big 12", "Pac-12", "AAC", "Mountain West", "MAC", "Sun Belt", "C-USA"]
    
    print("Conference Strength Rankings:")
    print("Rank | Conference      | Strength")
    print("-" * 35)
    
    for i, conf in enumerate(conferences, 1):
        strength = prob_calculator._get_conference_strength(conf)
        print(f"{i:4} | {conf:15} | {strength:.2f}")
    
    print()

def example_espn_ncaa_scraping():
    """Example of ESPN NCAA data scraping"""
    print("=== ESPN NCAA Data Scraping Example ===\n")
    
    scraper = ESPNScraper(headless=True)
    
    print("1. Scraping NCAA Football standings...")
    try:
        teams = scraper.get_team_stats('ncaaf', '2023')
        if teams:
            print(f"   Scraped {len(teams)} NCAA Football teams")
            print("   Top 5 teams by win percentage:")
            sorted_teams = sorted(teams, key=lambda x: x['win_percentage'], reverse=True)
            for i, team in enumerate(sorted_teams[:5]):
                print(f"     {i+1}. {team['team']}: {team['wins']}-{team['losses']} ({team['win_percentage']:.3f})")
        else:
            print("   WARNING: No team data retrieved")
        except Exception as e:
            print(f"   WARNING: Error scraping team data: {e}")
    
    print("\n2. Scraping NCAA Basketball standings...")
    try:
        teams = scraper.get_team_stats('ncaab', '2023')
        if teams:
            print(f"   Scraped {len(teams)} NCAA Basketball teams")
            print("   Top 5 teams by win percentage:")
            sorted_teams = sorted(teams, key=lambda x: x['win_percentage'], reverse=True)
            for i, team in enumerate(sorted_teams[:5]):
                print(f"     {i+1}. {team['team']}: {team['wins']}-{team['losses']} ({team['win_percentage']:.3f})")
        else:
            print("   WARNING: No team data retrieved")
        except Exception as e:
            print(f"   WARNING: Error scraping team data: {e}")
    
    print()

def example_odds_conversion():
    """Example of odds conversion for NCAA betting"""
    print("=== NCAA Betting Odds Conversion Example ===\n")
    
    odds_manager = OddsManager()
    
    # Example NCAA betting odds
    ncaa_odds = [150, -200, 110, -110, 250, -300]
    
    print("NCAA Betting Odds Conversion:")
    print("American | Decimal | Probability | Implied %")
    print("-" * 45)
    
    for odds in ncaa_odds:
        decimal = odds_manager.convert_american_to_decimal(odds)
        probability = odds_manager.convert_american_to_probability(odds)
        implied_pct = probability * 100
        print(f"{odds:8} | {decimal:7.3f} | {probability:11.3f} | {implied_pct:8.1f}%")
    
    print()

def main():
    """Run all NCAA examples"""
    print("NCAA Sports Betting Bot - Example Usage\n")
    print("=" * 50)
    
    try:
        example_ncaa_football_analysis()
        example_ncaa_basketball_analysis()
        example_conference_strength()
        example_espn_ncaa_scraping()
        example_odds_conversion()
        
        print("=" * 50)
        print("All NCAA examples completed successfully!")
        print("\nTo get started with NCAA sports:")
        print("1. Set up your API keys in the .env file")
        print("2. Run: python main.py update-odds --sport ncaaf")
        print("3. Run: python main.py update-odds --sport ncaab")
        print("4. Run: python main.py analyze --sport ncaaf")
        print("5. Run: python main.py analyze --sport ncaab")
        
    except Exception as e:
        logger.error(f"Error running NCAA examples: {e}")
        print(f"\nError: {e}")
        print("Please check your configuration and try again.")

if __name__ == "__main__":
    main()
