#!/usr/bin/env python3
"""
Test script for Sports Betting Bot
Runs basic tests to verify functionality
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from betting_bot import DatabaseManager, Team, Player, Game, Odds
from odds_api import OddsManager
from probability_calculator import ProbabilityCalculator, TeamStats, GameContext

class TestBettingBot(unittest.TestCase):
    """Test cases for the betting bot"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.db_manager = DatabaseManager(":memory:")  # Use in-memory database for testing
    
    def test_database_initialization(self):
        """Test database initialization"""
        self.assertIsNotNone(self.db_manager)
        # Database should be initialized with tables
    
    def test_team_creation(self):
        """Test team creation and storage"""
        team = Team(
            id="test_team",
            name="Test Team",
            abbreviation="TT",
            sport="nfl"
        )
        
        self.db_manager.add_team(team)
        teams = self.db_manager.get_teams_by_sport("nfl")
        
        self.assertEqual(len(teams), 1)
        self.assertEqual(teams[0].name, "Test Team")
    
    def test_game_creation(self):
        """Test game creation and storage"""
        from datetime import datetime
        
        game = Game(
            id="test_game",
            home_team="Home Team",
            away_team="Away Team",
            sport="nfl",
            start_time=datetime.now()
        )
        
        self.db_manager.add_game(game)
        games = self.db_manager.get_upcoming_games("nfl")
        
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0].home_team, "Home Team")
    
    def test_odds_conversion(self):
        """Test odds conversion utilities"""
        odds_manager = OddsManager()
        
        # Test American to decimal conversion
        decimal = odds_manager.convert_american_to_decimal(150)
        self.assertAlmostEqual(decimal, 2.5, places=2)
        
        decimal = odds_manager.convert_american_to_decimal(-200)
        self.assertAlmostEqual(decimal, 1.5, places=2)
        
        # Test American to probability conversion
        prob = odds_manager.convert_american_to_probability(150)
        self.assertAlmostEqual(prob, 0.4, places=2)
        
        prob = odds_manager.convert_american_to_probability(-200)
        self.assertAlmostEqual(prob, 0.667, places=2)
    
    def test_probability_calculation(self):
        """Test probability calculation"""
        prob_calculator = ProbabilityCalculator(self.db_manager)
        
        # Create test team stats
        home_stats = TeamStats(
            team_id="home",
            wins=10,
            losses=6,
            win_percentage=0.625,
            home_record=(6, 2),
            away_record=(4, 4),
            recent_form=[True, True, False, True, True],
            avg_points_for=25.0,
            avg_points_against=22.0,
            strength_of_schedule=0.5
        )
        
        away_stats = TeamStats(
            team_id="away",
            wins=8,
            losses=8,
            win_percentage=0.5,
            home_record=(4, 4),
            away_record=(4, 4),
            recent_form=[True, False, True, False, True],
            avg_points_for=23.0,
            avg_points_against=24.0,
            strength_of_schedule=0.5
        )
        
        # Create game context
        game_context = GameContext(
            home_team="Home Team",
            away_team="Away Team",
            home_team_stats=home_stats,
            away_team_stats=away_stats
        )
        
        # Test moneyline probability calculation
        ml_prob = prob_calculator.calculate_moneyline_probability(game_context)
        
        self.assertIn('home_win_probability', ml_prob)
        self.assertIn('away_win_probability', ml_prob)
        self.assertIn('confidence', ml_prob)
        
        # Probabilities should sum to approximately 1
        total_prob = ml_prob['home_win_probability'] + ml_prob['away_win_probability']
        self.assertAlmostEqual(total_prob, 1.0, places=1)
        
        # Home team should have higher probability (better record)
        self.assertGreater(ml_prob['home_win_probability'], ml_prob['away_win_probability'])
    
    def test_spread_probability_calculation(self):
        """Test spread probability calculation"""
        prob_calculator = ProbabilityCalculator(self.db_manager)
        
        # Create test team stats
        home_stats = TeamStats(
            team_id="home",
            wins=10,
            losses=6,
            win_percentage=0.625,
            home_record=(6, 2),
            away_record=(4, 4),
            recent_form=[True, True, False, True, True],
            avg_points_for=25.0,
            avg_points_against=22.0,
            strength_of_schedule=0.5
        )
        
        away_stats = TeamStats(
            team_id="away",
            wins=8,
            losses=8,
            win_percentage=0.5,
            home_record=(4, 4),
            away_record=(4, 4),
            recent_form=[True, False, True, False, True],
            avg_points_for=23.0,
            avg_points_against=24.0,
            strength_of_schedule=0.5
        )
        
        game_context = GameContext(
            home_team="Home Team",
            away_team="Away Team",
            home_team_stats=home_stats,
            away_team_stats=away_stats
        )
        
        # Test spread probability calculation
        spread_prob = prob_calculator.calculate_spread_probability(game_context, -3.5)
        
        self.assertIn('home_covers_probability', spread_prob)
        self.assertIn('away_covers_probability', spread_prob)
        self.assertIn('confidence', spread_prob)
        
        # Probabilities should sum to 1
        total_prob = spread_prob['home_covers_probability'] + spread_prob['away_covers_probability']
        self.assertAlmostEqual(total_prob, 1.0, places=1)
    
    def test_total_probability_calculation(self):
        """Test total probability calculation"""
        prob_calculator = ProbabilityCalculator(self.db_manager)
        
        # Create test team stats
        home_stats = TeamStats(
            team_id="home",
            wins=10,
            losses=6,
            win_percentage=0.625,
            home_record=(6, 2),
            away_record=(4, 4),
            recent_form=[True, True, False, True, True],
            avg_points_for=25.0,
            avg_points_against=22.0,
            strength_of_schedule=0.5
        )
        
        away_stats = TeamStats(
            team_id="away",
            wins=8,
            losses=8,
            win_percentage=0.5,
            home_record=(4, 4),
            away_record=(4, 4),
            recent_form=[True, False, True, False, True],
            avg_points_for=23.0,
            avg_points_against=24.0,
            strength_of_schedule=0.5
        )
        
        game_context = GameContext(
            home_team="Home Team",
            away_team="Away Team",
            home_team_stats=home_stats,
            away_team_stats=away_stats
        )
        
        # Test total probability calculation
        total_prob = prob_calculator.calculate_total_probability(game_context, 48.5)
        
        self.assertIn('over_probability', total_prob)
        self.assertIn('under_probability', total_prob)
        self.assertIn('expected_total', total_prob)
        self.assertIn('confidence', total_prob)
        
        # Probabilities should sum to 1
        total_prob_sum = total_prob['over_probability'] + total_prob['under_probability']
        self.assertAlmostEqual(total_prob_sum, 1.0, places=1)
        
        # Expected total should be reasonable
        self.assertGreater(total_prob['expected_total'], 0)
        self.assertLess(total_prob['expected_total'], 100)

class TestOddsManager(unittest.TestCase):
    """Test cases for odds manager"""
    
    def test_odds_manager_initialization(self):
        """Test odds manager initialization"""
        odds_manager = OddsManager()
        self.assertIsNotNone(odds_manager)
    
    def test_fair_odds_calculation(self):
        """Test fair odds calculation"""
        odds_manager = OddsManager()
        
        # Test with multiple odds
        odds_list = [150, 160, 140, 155]
        fair_odds = odds_manager.calculate_fair_odds(odds_list)
        
        self.assertIsNotNone(fair_odds)
        self.assertGreater(fair_odds, 0)

def run_tests():
    """Run all tests"""
    print("Running Sports Betting Bot Tests")
    print("=" * 40)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestBettingBot))
    test_suite.addTest(unittest.makeSuite(TestOddsManager))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 40)
    if result.wasSuccessful():
        print("All tests passed!")
        return True
    else:
        print(f"ERROR: {len(result.failures)} test(s) failed")
        print(f"ERROR: {len(result.errors)} error(s) occurred")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
