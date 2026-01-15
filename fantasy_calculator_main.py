"""
Fantasy Sports Probability Calculator - Main Integration
Integrates ESPN scraper with probability calculations for Team and Player props
Supports: NFL, NBA, NHL, MLB, NCAAF, NCAAM
"""

import argparse
import json
from datetime import datetime
from typing import Dict, List, Optional
import logging

from fantasy_probability_calculator import (
    FantasyProbabilityCalculator,
    TeamStats,
    GameContext,
    PlayerGameStats
)
from models import PlayerProp, Odds
from odds_api import OddsManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FantasyCalculatorApp:
    """Main application class for fantasy probability calculations"""
    
    def __init__(self):
        self.calculator = FantasyProbabilityCalculator()
        self.odds_manager = OddsManager()
    
    def calculate_team_props(
        self,
        sport: str,
        home_team: str,
        away_team: str,
        home_stats: Optional[Dict] = None,
        away_stats: Optional[Dict] = None,
        spread: Optional[float] = None,
        total: Optional[float] = None
    ) -> Dict:
        """
        Calculate all team props for a game.
        
        Args:
            sport: Sport league (nfl, nba, nhl, mlb, ncaaf, ncaam)
            home_team: Home team name/abbreviation
            away_team: Away team name/abbreviation
            home_stats: Optional dict with home team stats
            away_stats: Optional dict with away team stats
            spread: Optional point spread
            total: Optional total points/goals/runs line
            
        Returns:
            Dict with all team prop probabilities
        """
        # Create team stats objects
        home_team_stats = self._create_team_stats(home_team, home_stats or {}, is_home=True)
        away_team_stats = self._create_team_stats(away_team, away_stats or {}, is_home=False)
        
        # Create game context
        game_context = GameContext(
            home_team=home_team,
            away_team=away_team,
            home_team_stats=home_team_stats,
            away_team_stats=away_team_stats,
            sport=sport
        )
        
        results = {}
        
        # Calculate moneyline
        moneyline = self.calculator.calculate_team_moneyline_probability(game_context)
        results["moneyline"] = moneyline
        
        # Calculate spread if provided
        if spread is not None:
            spread_result = self.calculator.calculate_team_spread_probability(
                game_context, spread
            )
            results["spread"] = spread_result
        
        # Calculate total if provided
        if total is not None:
            total_result = self.calculator.calculate_team_total_probability(
                game_context, total
            )
            results["total"] = total_result
        
        return results
    
    def calculate_player_props(
        self,
        sport: str,
        team: str,
        player_name: str,
        prop_types: List[str],
        lines: Optional[Dict[str, float]] = None,
        game_context: Optional[GameContext] = None
    ) -> Dict[str, Dict]:
        """
        Calculate player prop probabilities.
        
        Args:
            sport: Sport league
            team: Team name/abbreviation
            player_name: Player name
            prop_types: List of prop types to calculate
            lines: Optional dict mapping prop_type to line value
            game_context: Optional game context for matchup adjustments
            
        Returns:
            Dict mapping prop_type to probability results
        """
        results = {}
        
        for prop_type in prop_types:
            line = lines.get(prop_type) if lines else None
            
            if line is None:
                # Try to get a reasonable default line
                line = self._get_default_line(sport, prop_type)
            
            if line is None:
                logger.warning(f"No line provided for {prop_type}, skipping")
                continue
            
            try:
                prob_result = self.calculator.calculate_player_prop_probability(
                    league=sport,
                    team_query=team,
                    player_name=player_name,
                    prop_type=prop_type,
                    line=line,
                    game_context=game_context
                )
                results[prop_type] = prob_result
            except Exception as e:
                logger.error(f"Error calculating {prop_type} for {player_name}: {e}")
                results[prop_type] = {
                    "error": str(e),
                    "over_prob": 0.5,
                    "under_prob": 0.5
                }
        
        return results
    
    def analyze_prop_value(
        self,
        calculated_prob: float,
        odds: float
    ) -> Dict:
        """
        Analyze if a prop bet has value based on calculated probability vs odds.
        
        Args:
            calculated_prob: Calculated probability (0-1)
            odds: American odds
            
        Returns:
            Dict with value analysis
        """
        # Convert odds to implied probability
        implied_prob = self.odds_manager.convert_american_to_probability(odds)
        
        # Calculate expected value
        if odds > 0:
            payout = odds / 100
        else:
            payout = 100 / abs(odds)
        
        expected_value = (calculated_prob * payout) - (1 - calculated_prob)
        
        # Calculate value percentage
        value_pct = ((calculated_prob - implied_prob) / implied_prob * 100) if implied_prob > 0 else 0
        
        return {
            "calculated_probability": calculated_prob,
            "implied_probability": implied_prob,
            "expected_value": expected_value,
            "value_percentage": value_pct,
            "has_value": expected_value > 0.05,  # 5% minimum edge
            "recommendation": "BET" if expected_value > 0.05 else "PASS"
        }
    
    def _create_team_stats(
        self,
        team_name: str,
        stats_dict: Dict,
        is_home: bool
    ) -> TeamStats:
        """Create TeamStats object from dict"""
        return TeamStats(
            team_id=stats_dict.get("team_id", team_name),
            team_name=team_name,
            wins=stats_dict.get("wins", 0),
            losses=stats_dict.get("losses", 0),
            win_percentage=stats_dict.get("win_percentage", 0.5),
            home_record=tuple(stats_dict.get("home_record", [0, 0])),
            away_record=tuple(stats_dict.get("away_record", [0, 0])),
            recent_form=stats_dict.get("recent_form", []),
            avg_points_for=stats_dict.get("avg_points_for", 0.0),
            avg_points_against=stats_dict.get("avg_points_against", 0.0),
            is_home_team=is_home
        )
    
    def _get_default_line(self, sport: str, prop_type: str) -> Optional[float]:
        """Get default line for a prop type if not provided"""
        defaults = {
            "nfl": {
                "passing_yards": 250.0,
                "passing_tds": 1.5,
                "rushing_yards": 60.0,
                "rushing_tds": 0.5,
                "receiving_yards": 60.0,
                "receiving_tds": 0.5,
                "receptions": 4.5,
            },
            "nba": {
                "points": 20.0,
                "rebounds": 8.0,
                "assists": 5.0,
                "steals": 1.5,
                "blocks": 1.5,
                "three_pointers": 2.5,
            },
            "nhl": {
                "goals": 0.5,
                "assists": 0.5,
                "points": 0.5,
                "shots": 3.5,
            },
            "mlb": {
                "hits": 1.5,
                "home_runs": 0.5,
                "runs": 1.5,
                "runs_batted_in": 1.5,
                "strikeouts": 5.5,
            },
            "ncaaf": {
                "passing_yards": 250.0,
                "passing_tds": 2.5,
                "rushing_yards": 80.0,
                "rushing_tds": 1.5,
                "receiving_yards": 70.0,
                "receiving_tds": 0.5,
            },
            "ncaam": {
                "points": 15.0,
                "rebounds": 7.0,
                "assists": 4.0,
                "steals": 1.5,
                "blocks": 1.5,
            },
        }
        
        return defaults.get(sport, {}).get(prop_type)
    
    def print_team_props(self, results: Dict):
        """Pretty print team prop results"""
        print("\n" + "=" * 60)
        print("TEAM PROPS ANALYSIS")
        print("=" * 60)
        
        if "moneyline" in results:
            ml = results["moneyline"]
            print(f"\nMoneyline:")
            print(f"  Home Win Probability: {ml['home_win_prob']:.1%}")
            print(f"  Away Win Probability: {ml['away_win_prob']:.1%}")
            print(f"  Confidence: {ml['confidence']:.1%}")
        
        if "spread" in results:
            spread = results["spread"]
            print(f"\nSpread:")
            print(f"  Home Covers: {spread['home_covers_prob']:.1%}")
            print(f"  Away Covers: {spread['away_covers_prob']:.1%}")
            print(f"  Expected Margin: {spread['expected_margin']:.1f}")
            print(f"  Confidence: {spread['confidence']:.1%}")
        
        if "total" in results:
            total = results["total"]
            print(f"\nTotal:")
            print(f"  Over: {total['over_prob']:.1%}")
            print(f"  Under: {total['under_prob']:.1%}")
            print(f"  Expected Total: {total['expected_total']:.1f}")
            print(f"  Confidence: {total['confidence']:.1%}")
        
        print("\n" + "=" * 60 + "\n")
    
    def print_player_props(self, player_name: str, results: Dict):
        """Pretty print player prop results"""
        print("\n" + "=" * 60)
        print(f"PLAYER PROPS ANALYSIS: {player_name}")
        print("=" * 60)
        
        for prop_type, result in results.items():
            if "error" in result:
                print(f"\n{prop_type}: ERROR - {result['error']}")
                continue
            
            print(f"\n{prop_type}:")
            print(f"  Over Probability: {result['over_prob']:.1%}")
            print(f"  Under Probability: {result['under_prob']:.1%}")
            print(f"  Expected Value: {result['expected_value']:.2f}")
            if 'last_game_value' in result:
                print(f"  Last Game Value: {result['last_game_value']}")
            print(f"  Confidence: {result['confidence']:.1%}")
        
        print("\n" + "=" * 60 + "\n")


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(
        description="Fantasy Sports Probability Calculator"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Team props command
    team_parser = subparsers.add_parser("team-props", help="Calculate team props")
    team_parser.add_argument("--sport", required=True, 
                           choices=["nfl", "nba", "nhl", "mlb", "ncaaf", "ncaam"],
                           help="Sport league")
    team_parser.add_argument("--home-team", required=True, help="Home team")
    team_parser.add_argument("--away-team", required=True, help="Away team")
    team_parser.add_argument("--spread", type=float, help="Point spread")
    team_parser.add_argument("--total", type=float, help="Total points/goals/runs")
    
    # Player props command
    player_parser = subparsers.add_parser("player-props", help="Calculate player props")
    player_parser.add_argument("--sport", required=True,
                              choices=["nfl", "nba", "nhl", "mlb", "ncaaf", "ncaam"],
                              help="Sport league")
    player_parser.add_argument("--team", required=True, help="Team name/abbreviation")
    player_parser.add_argument("--player", required=True, help="Player name")
    player_parser.add_argument("--props", nargs="+", required=True,
                               help="Prop types (e.g., passing_yards points rebounds)")
    player_parser.add_argument("--lines", type=json.loads,
                               help="JSON dict of prop_type:line values")
    
    args = parser.parse_args()
    
    app = FantasyCalculatorApp()
    
    if args.command == "team-props":
        results = app.calculate_team_props(
            sport=args.sport,
            home_team=args.home_team,
            away_team=args.away_team,
            spread=args.spread,
            total=args.total
        )
        app.print_team_props(results)
    
    elif args.command == "player-props":
        lines = args.lines if args.lines else {}
        results = app.calculate_player_props(
            sport=args.sport,
            team=args.team,
            player_name=args.player,
            prop_types=args.props,
            lines=lines
        )
        app.print_player_props(args.player, results)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
