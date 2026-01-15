#!/usr/bin/env python3
"""
NCAA Player Props Betting Bot - Example Usage
Demonstrates player prop analysis for NCAA Football and Basketball
"""

import os
import sys
from datetime import datetime
import logging

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import BettingBotApp
from betting_bot import DatabaseManager, PlayerProp, PlayerStats, Game, TeamStats
from odds_api import OddsManager
from espn_scraper import ESPNScraper
from probability_calculator import ProbabilityCalculator, GameContext

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def example_ncaa_football_player_props():
    """Example of NCAA Football player prop analysis"""
    print("=== NCAA Football Player Props Analysis ===\n")
    
    prob_calculator = ProbabilityCalculator(DatabaseManager())
    
    # Create example NCAA Football player stats
    qb_stats = PlayerStats(
        player_id="bryce_young_ala_2023",
        player_name="Bryce Young",
        team_id="ALA",
        position="QB",
        sport="ncaaf",
        season="2023",
        games_played=12,
        stats={
            'passing_yards': 3200,
            'passing_tds': 28,
            'passing_attempts': 380,
            'completion_pct': 68.5,
            'rushing_yards': 150,
            'rushing_tds': 3
        },
        recent_form=[285, 320, 295, 310, 275],  # Last 5 games passing yards
        season_average=266.7,  # Passing yards per game
        home_average=280.0,
        away_average=253.3,
        vs_opponent_average=270.0
    )
    
    # Create game context for SEC Championship
    home_team_stats = TeamStats(
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
    
    away_team_stats = TeamStats(
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
    
    game_context = GameContext(
        home_team="Alabama Crimson Tide",
        away_team="Georgia Bulldogs",
        home_team_stats=home_team_stats,
        away_team_stats=away_team_stats,
        sport="ncaaf",
        conference_game=True,
        rivalry_game=True
    )
    
    print("1. Bryce Young Passing Yards Analysis:")
    print(f"   Season Average: {qb_stats.season_average:.1f} yards/game")
    print(f"   Recent Form: {qb_stats.recent_form}")
    print(f"   Home Average: {qb_stats.home_average:.1f} yards/game")
    print(f"   Away Average: {qb_stats.away_average:.1f} yards/game")
    print()
    
    # Analyze different passing yard lines
    lines = [250, 275, 300, 325, 350]
    
    for line in lines:
        prob = prob_calculator.calculate_player_prop_probability(
            qb_stats, 'passing_yards', line, game_context
        )
        
        print(f"2. Over {line} Passing Yards:")
        print(f"   Over Probability: {prob['over_probability']:.3f}")
        print(f"   Under Probability: {prob['under_probability']:.3f}")
        print(f"   Expected Value: {prob['expected_value']:.1f}")
        print(f"   Confidence: {prob['confidence']:.3f}")
        print(f"   Matchup Adjustment: {prob['matchup_adjustment']:.1f}")
        print()
    
    # Analyze passing TDs
    td_prob = prob_calculator.calculate_player_prop_probability(
        qb_stats, 'passing_tds', 2.5, game_context
    )
    
    print("3. Passing Touchdowns Analysis:")
    print(f"   Over 2.5 TDs Probability: {td_prob['over_probability']:.3f}")
    print(f"   Under 2.5 TDs Probability: {td_prob['under_probability']:.3f}")
    print(f"   Expected TDs: {td_prob['expected_value']:.1f}")
    print(f"   Confidence: {td_prob['confidence']:.3f}")
    print()

def example_ncaa_basketball_player_props():
    """Example of NCAA Basketball player prop analysis"""
    print("=== NCAA Basketball Player Props Analysis ===\n")
    
    prob_calculator = ProbabilityCalculator(DatabaseManager())
    
    # Create example NCAA Basketball player stats
    player_stats = PlayerStats(
        player_id="caitlin_clark_iowa_2023",
        player_name="Caitlin Clark",
        team_id="IOWA",
        position="G",
        sport="ncaab",
        season="2023",
        games_played=30,
        stats={
            'points': 28.5,
            'rebounds': 7.2,
            'assists': 8.1,
            'steals': 1.8,
            'blocks': 0.5,
            'field_goal_pct': 45.2,
            'three_point_pct': 38.7
        },
        recent_form=[32, 28, 35, 24, 31],  # Last 5 games points
        season_average=28.5,
        home_average=30.2,
        away_average=26.8,
        vs_opponent_average=29.1
    )
    
    # Create game context for Big Ten Championship
    home_team_stats = TeamStats(
        team_id="IOWA",
        wins=25,
        losses=5,
        win_percentage=0.833,
        home_record=(15, 1),
        away_record=(10, 4),
        recent_form=[True, True, False, True, True],
        avg_points_for=85.2,
        avg_points_against=72.1,
        strength_of_schedule=0.75,
        conference="Big Ten",
        ranking=3,
        is_home_team=True
    )
    
    away_team_stats = TeamStats(
        team_id="OSU",
        wins=22,
        losses=8,
        win_percentage=0.733,
        home_record=(14, 2),
        away_record=(8, 6),
        recent_form=[True, False, True, True, False],
        avg_points_for=78.8,
        avg_points_against=70.3,
        strength_of_schedule=0.78,
        conference="Big Ten",
        ranking=8,
        is_home_team=False
    )
    
    game_context = GameContext(
        home_team="Iowa Hawkeyes",
        away_team="Ohio State Buckeyes",
        home_team_stats=home_team_stats,
        away_team_stats=away_team_stats,
        sport="ncaab",
        conference_game=True,
        rivalry_game=True
    )
    
    print("1. Caitlin Clark Points Analysis:")
    print(f"   Season Average: {player_stats.season_average:.1f} points/game")
    print(f"   Recent Form: {player_stats.recent_form}")
    print(f"   Home Average: {player_stats.home_average:.1f} points/game")
    print(f"   Away Average: {player_stats.away_average:.1f} points/game")
    print()
    
    # Analyze different point lines
    lines = [25, 27.5, 30, 32.5, 35]
    
    for line in lines:
        prob = prob_calculator.calculate_player_prop_probability(
            player_stats, 'points', line, game_context
        )
        
        print(f"2. Over {line} Points:")
        print(f"   Over Probability: {prob['over_probability']:.3f}")
        print(f"   Under Probability: {prob['under_probability']:.3f}")
        print(f"   Expected Points: {prob['expected_value']:.1f}")
        print(f"   Confidence: {prob['confidence']:.3f}")
        print(f"   Matchup Adjustment: {prob['matchup_adjustment']:.1f}")
        print()
    
    # Analyze rebounds
    rebound_prob = prob_calculator.calculate_player_prop_probability(
        player_stats, 'rebounds', 7.5, game_context
    )
    
    print("3. Rebounds Analysis:")
    print(f"   Over 7.5 Rebounds Probability: {rebound_prob['over_probability']:.3f}")
    print(f"   Under 7.5 Rebounds Probability: {rebound_prob['under_probability']:.3f}")
    print(f"   Expected Rebounds: {rebound_prob['expected_value']:.1f}")
    print(f"   Confidence: {rebound_prob['confidence']:.3f}")
    print()
    
    # Analyze assists
    assist_prob = prob_calculator.calculate_player_prop_probability(
        player_stats, 'assists', 8.5, game_context
    )
    
    print("4. Assists Analysis:")
    print(f"   Over 8.5 Assists Probability: {assist_prob['over_probability']:.3f}")
    print(f"   Under 8.5 Assists Probability: {assist_prob['under_probability']:.3f}")
    print(f"   Expected Assists: {assist_prob['expected_value']:.1f}")
    print(f"   Confidence: {assist_prob['confidence']:.3f}")
    print()

def example_player_prop_value_analysis():
    """Example of player prop value betting analysis"""
    print("=== Player Prop Value Betting Analysis ===\n")
    
    # Example player prop with odds
    player_props = [
        {
            'player_name': 'Bryce Young',
            'prop_type': 'passing_yards',
            'line': 275,
            'over_odds': -110,
            'under_odds': -110,
            'expected_value': 285.5,
            'confidence': 0.75
        },
        {
            'player_name': 'Caitlin Clark',
            'prop_type': 'points',
            'line': 28.5,
            'over_odds': -105,
            'under_odds': -115,
            'expected_value': 30.2,
            'confidence': 0.82
        },
        {
            'player_name': 'Caleb Williams',
            'prop_type': 'rushing_yards',
            'line': 45,
            'over_odds': -120,
            'under_odds': +100,
            'expected_value': 52.3,
            'confidence': 0.68
        }
    ]
    
    odds_manager = OddsManager()
    
    print("Player Prop Value Analysis:")
    print("Player | Prop Type | Line | Over Odds | Under Odds | Expected | Value")
    print("-" * 80)
    
    for prop in player_props:
        # Calculate probabilities
        over_prob = odds_manager.convert_american_to_probability(prop['over_odds'])
        under_prob = odds_manager.convert_american_to_probability(prop['under_odds'])
        
        # Calculate expected values
        over_ev = (over_prob * prop['over_odds']) - (1 - over_prob)
        under_ev = (under_prob * prop['under_odds']) - (1 - under_prob)
        
        # Determine best value
        if over_ev > under_ev and over_ev > 0.05:
            best_bet = f"Over {prop['line']} (+{over_ev:.3f})"
        elif under_ev > over_ev and under_ev > 0.05:
            best_bet = f"Under {prop['line']} (+{under_ev:.3f})"
        else:
            best_bet = "No Value"
        
        print(f"{prop['player_name']:12} | {prop['prop_type']:12} | {prop['line']:4} | "
              f"{prop['over_odds']:9} | {prop['under_odds']:10} | {prop['expected_value']:8.1f} | {best_bet}")
    
    print()

def example_player_prop_workflow():
    """Example of complete player prop workflow"""
    print("=== Complete Player Prop Workflow ===\n")
    
    app = BettingBotApp()
    
    print("1. Collecting player data...")
    try:
        # This would collect actual player data
        print("   Player data collection completed")
    except Exception as e:
        print(f"   WARNING: Error collecting player data: {e}")
    
    print("\n2. Updating player prop odds...")
    try:
        # This would update actual player prop odds
        print("   Player prop odds updated")
    except Exception as e:
        print(f"   WARNING: Error updating player prop odds: {e}")
    
    print("\n3. Analyzing player prop opportunities...")
    try:
        # This would analyze actual opportunities
        print("   Player prop analysis completed")
        print("   Found 5 value betting opportunities")
    except Exception as e:
        print(f"   WARNING: Error analyzing player props: {e}")
    
    print("\n4. Sample Player Prop Recommendations:")
    print("   a) Bryce Young Over 275 Passing Yards @ -110 (EV: +0.087)")
    print("   b) Caitlin Clark Over 28.5 Points @ -105 (EV: +0.063)")
    print("   c) Caleb Williams Under 45 Rushing Yards @ +100 (EV: +0.058)")
    print("   d) Jalen Hurts Over 2.5 Passing TDs @ -120 (EV: +0.045)")
    print("   e) Angel Reese Over 12.5 Rebounds @ -110 (EV: +0.042)")
    print()

def main():
    """Run all player prop examples"""
    print("NCAA Player Props Betting Bot - Example Usage\n")
    print("=" * 60)
    
    try:
        example_ncaa_football_player_props()
        example_ncaa_basketball_player_props()
        example_player_prop_value_analysis()
        example_player_prop_workflow()
        
        print("=" * 60)
        print("All player prop examples completed successfully!")
        print("\nTo get started with player props:")
        print("1. Set up your API keys in the .env file")
        print("2. Run: python main.py collect-player-data --sport ncaaf --seasons 2023")
        print("3. Run: python main.py update-player-props --sport ncaaf")
        print("4. Run: python main.py analyze-player-props --sport ncaaf")
        print("5. Run: python main.py analyze-player-props --sport ncaab")
        
    except Exception as e:
        logger.error(f"Error running player prop examples: {e}")
        print(f"\nError: {e}")
        print("Please check your configuration and try again.")

if __name__ == "__main__":
    main()
