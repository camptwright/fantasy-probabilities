"""
Fantasy Sports Probability Calculator
Integrates with ESPN scraper to calculate probabilities for Team and Player props
Supports: NFL, NBA, NHL, MLB, NCAAF, NCAAM
"""

from __future__ import annotations

import json
import math
import numpy as np
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

from espn_player_last_game import (
    find_latest_team_game_event,
    fetch_game_summary,
    find_player_stats_in_summary,
    ESPNError,
    get_league_config,
    LEAGUE_CONFIG
)

logger = logging.getLogger(__name__)


@dataclass
class TeamStats:
    """Team statistics for analysis"""
    team_id: str
    team_name: str
    wins: int = 0
    losses: int = 0
    win_percentage: float = 0.5
    home_record: Tuple[int, int] = (0, 0)
    away_record: Tuple[int, int] = (0, 0)
    recent_form: List[bool] = None  # Last 10 games results
    avg_points_for: float = 0.0
    avg_points_against: float = 0.0
    is_home_team: bool = True
    
    def __post_init__(self):
        if self.recent_form is None:
            self.recent_form = []


@dataclass
class PlayerGameStats:
    """Player statistics from a game"""
    player_name: str
    team_abbrev: str
    stats: Dict[str, Any]
    game_date: Optional[datetime] = None


@dataclass
class GameContext:
    """Context for a specific game"""
    home_team: str
    away_team: str
    home_team_stats: TeamStats
    away_team_stats: TeamStats
    sport: str
    game_date: Optional[datetime] = None
    is_neutral_site: bool = False


class FantasyProbabilityCalculator:
    """Main class for calculating fantasy performance probabilities"""
    
    # Sport-specific prop mappings
    PLAYER_PROP_MAPPINGS = {
        "nfl": {
            "passing_yards": ["PASSING_YARDS", "PYDS", "passYds"],
            "passing_tds": ["PASSING_TDS", "PTD", "passTD"],
            "passing_completions": ["COMPLETIONS", "COMP", "completions"],
            "rushing_yards": ["RUSHING_YARDS", "RYDS", "rushYds"],
            "rushing_tds": ["RUSHING_TDS", "RTD", "rushTD"],
            "receiving_yards": ["RECEIVING_YARDS", "RECYDS", "recYds"],
            "receiving_tds": ["RECEIVING_TDS", "RECTD", "recTD"],
            "receptions": ["RECEPTIONS", "REC", "receptions"],
            "interceptions": ["INTERCEPTIONS", "INT", "interceptions"],
        },
        "nba": {
            "points": ["POINTS", "PTS", "points"],
            "rebounds": ["REBOUNDS", "REB", "rebounds"],
            "assists": ["ASSISTS", "AST", "assists"],
            "steals": ["STEALS", "STL", "steals"],
            "blocks": ["BLOCKS", "BLK", "blocks"],
            "three_pointers": ["THREE_POINTERS", "3PM", "threePointersMade"],
            "turnovers": ["TURNOVERS", "TO", "turnovers"],
        },
        "nhl": {
            "goals": ["GOALS", "G", "goals"],
            "assists": ["ASSISTS", "A", "assists"],
            "points": ["POINTS", "PTS", "points"],
            "shots": ["SHOTS", "SOG", "shotsOnGoal"],
            "saves": ["SAVES", "SV", "saves"],  # For goalies
            "goals_against": ["GOALS_AGAINST", "GA", "goalsAgainst"],  # For goalies
        },
        "mlb": {
            "hits": ["HITS", "H", "hits"],
            "home_runs": ["HOME_RUNS", "HR", "homeRuns"],
            "runs": ["RUNS", "R", "runs"],
            "runs_batted_in": ["RBI", "RBI", "runsBattedIn"],
            "strikeouts": ["STRIKEOUTS", "SO", "strikeouts"],
            "stolen_bases": ["STOLEN_BASES", "SB", "stolenBases"],
            "pitcher_strikeouts": ["STRIKEOUTS", "SO", "strikeouts"],  # For pitchers
            "pitcher_earned_runs": ["EARNED_RUNS", "ER", "earnedRuns"],  # For pitchers
        },
        "ncaaf": {
            "passing_yards": ["PASSING_YARDS", "PYDS", "passYds"],
            "passing_tds": ["PASSING_TDS", "PTD", "passTD"],
            "rushing_yards": ["RUSHING_YARDS", "RYDS", "rushYds"],
            "rushing_tds": ["RUSHING_TDS", "RTD", "rushTD"],
            "receiving_yards": ["RECEIVING_YARDS", "RECYDS", "recYds"],
            "receiving_tds": ["RECEIVING_TDS", "RECTD", "recTD"],
            "receptions": ["RECEPTIONS", "REC", "receptions"],
        },
        "ncaam": {
            "points": ["POINTS", "PTS", "points"],
            "rebounds": ["REBOUNDS", "REB", "rebounds"],
            "assists": ["ASSISTS", "AST", "assists"],
            "steals": ["STEALS", "STL", "steals"],
            "blocks": ["BLOCKS", "BLK", "blocks"],
            "three_pointers": ["THREE_POINTERS", "3PM", "threePointersMade"],
        },
    }
    
    # Sport-specific scoring averages and variances
    SPORT_STATS = {
        "nfl": {
            "avg_points": 23.0,
            "variance": 12.0,
            "home_advantage": 2.5,
        },
        "nba": {
            "avg_points": 112.0,
            "variance": 15.0,
            "home_advantage": 3.0,
        },
        "nhl": {
            "avg_points": 2.8,
            "variance": 1.5,
            "home_advantage": 0.2,
        },
        "mlb": {
            "avg_points": 4.5,
            "variance": 2.5,
            "home_advantage": 0.3,
        },
        "ncaaf": {
            "avg_points": 28.0,
            "variance": 14.0,
            "home_advantage": 3.5,
        },
        "ncaam": {
            "avg_points": 72.0,
            "variance": 12.0,
            "home_advantage": 4.0,
        },
    }
    
    def __init__(self):
        """Initialize the probability calculator"""
        self.player_stats_cache: Dict[str, List[PlayerGameStats]] = {}
    
    def get_player_last_game_stats(
        self,
        league: str,
        team_query: str,
        player_name: str,
        max_days_back: int = 30
    ) -> Optional[PlayerGameStats]:
        """
        Get player stats from their last game using ESPN scraper.
        
        Args:
            league: Sport league (nfl, nba, nhl, mlb, ncaaf, ncaam)
            team_query: Team name/abbreviation
            player_name: Player name
            max_days_back: Maximum days to look back for games
            
        Returns:
            PlayerGameStats object or None if not found
        """
        try:
            # Find the latest game for the team
            event_id, event, canonical_abbrev = find_latest_team_game_event(
                league,
                team_query,
                max_days_back
            )
            
            # Fetch game summary
            summary = fetch_game_summary(league, event_id)
            
            # Find player stats in the summary
            athlete, stats = find_player_stats_in_summary(
                league,
                summary,
                player_name,
                canonical_abbrev
            )
            
            # Parse game date
            event_date = None
            if event.get("date"):
                try:
                    event_date = datetime.fromisoformat(
                        event["date"].replace("Z", "+00:00")
                    )
                except Exception:
                    pass
            
            return PlayerGameStats(
                player_name=player_name,
                team_abbrev=canonical_abbrev,
                stats=stats,
                game_date=event_date
            )
            
        except ESPNError as e:
            logger.warning(f"Could not fetch player stats: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching player stats: {e}")
            return None
    
    def calculate_team_moneyline_probability(
        self,
        game_context: GameContext
    ) -> Dict[str, float]:
        """
        Calculate moneyline probabilities for both teams.
        
        Returns:
            Dict with 'home_win_prob' and 'away_win_prob'
        """
        home_stats = game_context.home_team_stats
        away_stats = game_context.away_team_stats
        
        # Calculate team strength
        home_strength = self._calculate_team_strength(home_stats, game_context.sport, is_home=True)
        away_strength = self._calculate_team_strength(away_stats, game_context.sport, is_home=False)
        
        # Normalize to probabilities
        total_strength = home_strength + away_strength
        if total_strength == 0:
            return {"home_win_prob": 0.5, "away_win_prob": 0.5}
        
        home_prob = home_strength / total_strength
        away_prob = away_strength / total_strength
        
        return {
            "home_win_prob": home_prob,
            "away_win_prob": away_prob,
            "confidence": self._calculate_confidence(home_stats, away_stats)
        }
    
    def calculate_team_spread_probability(
        self,
        game_context: GameContext,
        spread: float
    ) -> Dict[str, float]:
        """
        Calculate probability of covering the spread.
        
        Args:
            game_context: Game context
            spread: Point spread (positive means home team favored)
            
        Returns:
            Dict with 'home_covers_prob' and 'away_covers_prob'
        """
        home_stats = game_context.home_team_stats
        away_stats = game_context.away_team_stats
        
        # Calculate expected margin
        home_expected = home_stats.avg_points_for
        away_expected = away_stats.avg_points_for
        
        # Apply defensive adjustments
        home_expected = (home_expected + away_stats.avg_points_against) / 2
        away_expected = (away_expected + home_stats.avg_points_against) / 2
        
        # Apply home field advantage
        sport_stats = self.SPORT_STATS.get(game_context.sport, self.SPORT_STATS["nfl"])
        if not game_context.is_neutral_site:
            home_expected += sport_stats["home_advantage"]
        
        expected_margin = home_expected - away_expected
        
        # Calculate variance
        variance = sport_stats["variance"] ** 2
        
        # Calculate probability using normal distribution
        z_score = (spread - expected_margin) / np.sqrt(variance)
        home_covers_prob = 1 - self._normal_cdf(z_score)
        
        return {
            "home_covers_prob": home_covers_prob,
            "away_covers_prob": 1 - home_covers_prob,
            "expected_margin": expected_margin,
            "confidence": self._calculate_confidence(home_stats, away_stats)
        }
    
    def calculate_team_total_probability(
        self,
        game_context: GameContext,
        total: float
    ) -> Dict[str, float]:
        """
        Calculate over/under probability for game total.
        
        Args:
            game_context: Game context
            total: Total points/goals/runs line
            
        Returns:
            Dict with 'over_prob' and 'under_prob'
        """
        home_stats = game_context.home_team_stats
        away_stats = game_context.away_team_stats
        
        # Calculate expected total
        home_expected = (home_stats.avg_points_for + away_stats.avg_points_against) / 2
        away_expected = (away_stats.avg_points_for + home_stats.avg_points_against) / 2
        
        expected_total = home_expected + away_expected
        
        # Calculate variance
        sport_stats = self.SPORT_STATS.get(game_context.sport, self.SPORT_STATS["nfl"])
        variance = sport_stats["variance"] ** 2 * 2  # Both teams contribute
        
        # Calculate probability using normal distribution
        z_score = (total - expected_total) / np.sqrt(variance)
        over_prob = 1 - self._normal_cdf(z_score)
        
        return {
            "over_prob": over_prob,
            "under_prob": 1 - over_prob,
            "expected_total": expected_total,
            "confidence": self._calculate_confidence(home_stats, away_stats)
        }
    
    def calculate_player_prop_probability(
        self,
        league: str,
        team_query: str,
        player_name: str,
        prop_type: str,
        line: float,
        game_context: Optional[GameContext] = None
    ) -> Dict[str, float]:
        """
        Calculate probability for a player prop.
        
        Args:
            league: Sport league
            team_query: Team name/abbreviation
            player_name: Player name
            prop_type: Type of prop (e.g., 'passing_yards', 'points')
            line: The over/under line
            game_context: Optional game context for matchup adjustments
            
        Returns:
            Dict with 'over_prob', 'under_prob', 'expected_value', etc.
        """
        # Get player's last game stats
        player_stats = self.get_player_last_game_stats(league, team_query, player_name)
        
        if not player_stats:
            logger.warning(f"Could not find stats for {player_name}")
            return {
                "over_prob": 0.5,
                "under_prob": 0.5,
                "expected_value": line,
                "confidence": 0.0
            }
        
        # Extract the relevant stat value
        stat_value = self._extract_stat_value(player_stats.stats, league, prop_type)
        
        if stat_value is None:
            logger.warning(f"Could not find stat '{prop_type}' for {player_name}")
            return {
                "over_prob": 0.5,
                "under_prob": 0.5,
                "expected_value": line,
                "confidence": 0.0
            }
        
        # Calculate expected value (use last game as baseline, adjust for matchup)
        expected_value = float(stat_value)
        
        # Apply matchup adjustments if game context provided
        if game_context:
            expected_value += self._calculate_matchup_adjustment(
                league, prop_type, player_stats.team_abbrev, game_context
            )
        
        # Calculate variance based on sport and prop type
        variance = self._calculate_player_variance(league, prop_type, expected_value)
        
        # Calculate probability using normal distribution
        z_score = (line - expected_value) / np.sqrt(variance)
        over_prob = 1 - self._normal_cdf(z_score)
        
        # Calculate confidence
        confidence = self._calculate_player_confidence(league, prop_type, variance, expected_value)
        
        return {
            "over_prob": over_prob,
            "under_prob": 1 - over_prob,
            "expected_value": expected_value,
            "last_game_value": stat_value,
            "confidence": confidence,
            "variance": variance
        }
    
    def _extract_stat_value(
        self,
        stats: Dict[str, Any],
        league: str,
        prop_type: str
    ) -> Optional[float]:
        """Extract stat value from stats dict using prop mappings"""
        if league not in self.PLAYER_PROP_MAPPINGS:
            return None
        
        prop_mapping = self.PLAYER_PROP_MAPPINGS[league]
        if prop_type not in prop_mapping:
            return None
        
        # Try each possible key name
        for key_variant in prop_mapping[prop_type]:
            # Try exact match
            if key_variant in stats:
                value = stats[key_variant]
                try:
                    return float(value)
                except (ValueError, TypeError):
                    continue
            
            # Try case-insensitive match
            for stat_key, stat_value in stats.items():
                if stat_key.upper() == key_variant.upper():
                    try:
                        return float(stat_value)
                    except (ValueError, TypeError):
                        continue
        
        return None
    
    def _calculate_team_strength(
        self,
        team_stats: TeamStats,
        sport: str,
        is_home: bool
    ) -> float:
        """Calculate overall team strength"""
        # Base strength from win percentage
        strength = team_stats.win_percentage
        
        # Adjust for recent form
        if team_stats.recent_form:
            recent_win_pct = sum(team_stats.recent_form) / len(team_stats.recent_form)
            strength = (strength * 0.6) + (recent_win_pct * 0.4)
        
        # Adjust for home/away record
        if is_home and sum(team_stats.home_record) > 0:
            home_pct = team_stats.home_record[0] / sum(team_stats.home_record)
            strength = (strength * 0.7) + (home_pct * 0.3)
        elif not is_home and sum(team_stats.away_record) > 0:
            away_pct = team_stats.away_record[0] / sum(team_stats.away_record)
            strength = (strength * 0.7) + (away_pct * 0.3)
        
        # Adjust for point differential
        point_diff = team_stats.avg_points_for - team_stats.avg_points_against
        sport_stats = self.SPORT_STATS.get(sport, self.SPORT_STATS["nfl"])
        normalized_diff = point_diff / (sport_stats["avg_points"] * 2)
        strength += normalized_diff * 0.2
        
        return max(0.0, min(1.0, strength))
    
    def _calculate_matchup_adjustment(
        self,
        league: str,
        prop_type: str,
        player_team: str,
        game_context: GameContext
    ) -> float:
        """Calculate matchup-based adjustment for player props"""
        adjustment = 0.0
        
        # Determine if player is on home or away team
        is_home_player = (
            player_team.upper() == game_context.home_team_stats.team_id.upper() or
            player_team.upper() in game_context.home_team.upper()
        )
        
        opponent_stats = game_context.away_team_stats if is_home_player else game_context.home_team_stats
        
        # Sport-specific adjustments
        if league in ["nfl", "ncaaf"]:
            if prop_type == "passing_yards":
                # Adjust based on opponent's pass defense (points against)
                adjustment -= opponent_stats.avg_points_against * 0.05
            elif prop_type == "rushing_yards":
                adjustment -= opponent_stats.avg_points_against * 0.03
            elif prop_type == "receiving_yards":
                adjustment -= opponent_stats.avg_points_against * 0.04
        
        elif league in ["nba", "ncaam"]:
            if prop_type == "points":
                # Adjust based on opponent's defense
                adjustment -= opponent_stats.avg_points_against * 0.02
            elif prop_type == "rebounds":
                # Slight adjustment for pace
                adjustment += (opponent_stats.avg_points_for - opponent_stats.avg_points_against) * 0.01
        
        elif league == "nhl":
            if prop_type in ["goals", "assists", "points"]:
                adjustment -= opponent_stats.avg_points_against * 0.1
        
        elif league == "mlb":
            if prop_type in ["hits", "home_runs", "runs"]:
                adjustment -= opponent_stats.avg_points_against * 0.05
        
        return adjustment
    
    def _calculate_player_variance(
        self,
        league: str,
        prop_type: str,
        expected_value: float
    ) -> float:
        """Calculate variance for player performance"""
        # Base variance as percentage of expected value
        base_variance_pct = {
            "nfl": 0.25,
            "nba": 0.20,
            "nhl": 0.30,
            "mlb": 0.25,
            "ncaaf": 0.30,
            "ncaam": 0.22,
        }.get(league, 0.25)
        
        variance = (expected_value * base_variance_pct) ** 2
        
        # Prop-specific adjustments
        high_variance_props = ["goals", "home_runs", "steals", "blocks", "saves"]
        if prop_type in high_variance_props:
            variance *= 1.5
        
        return max(variance, 1.0)
    
    def _calculate_player_confidence(
        self,
        league: str,
        prop_type: str,
        variance: float,
        expected_value: float
    ) -> float:
        """Calculate confidence in player prediction"""
        if expected_value == 0:
            return 0.0
        
        # Lower variance relative to expected value = higher confidence
        coefficient_of_variation = np.sqrt(variance) / expected_value
        confidence = max(0.0, min(1.0, 1.0 - coefficient_of_variation))
        
        return confidence
    
    def _calculate_confidence(
        self,
        home_stats: TeamStats,
        away_stats: TeamStats
    ) -> float:
        """Calculate confidence in team prediction"""
        # More games played = higher confidence
        home_games = home_stats.wins + home_stats.losses
        away_games = away_stats.wins + away_stats.losses
        
        if home_games == 0 or away_games == 0:
            return 0.3
        
        # Average confidence based on sample size
        avg_games = (home_games + away_games) / 2
        confidence = min(1.0, avg_games / 20.0)  # Max confidence at 20+ games
        
        return confidence
    
    def _normal_cdf(self, x: float) -> float:
        """Calculate normal cumulative distribution function"""
        return 0.5 * (1 + math.erf(x / np.sqrt(2)))


def main():
    """Example usage"""
    print("=== Fantasy Sports Probability Calculator ===\n")
    
    calculator = FantasyProbabilityCalculator()
    
    # Example: Calculate player prop probability
    print("Example 1: Player Prop Probability")
    print("-" * 50)
    
    result = calculator.calculate_player_prop_probability(
        league="nfl",
        team_query="DAL",
        player_name="Dak Prescott",
        prop_type="passing_yards",
        line=275.5
    )
    
    print(f"Over Probability: {result['over_prob']:.3f}")
    print(f"Under Probability: {result['under_prob']:.3f}")
    print(f"Expected Value: {result['expected_value']:.1f}")
    print(f"Last Game Value: {result.get('last_game_value', 'N/A')}")
    print(f"Confidence: {result['confidence']:.3f}")
    
    print("\n" + "=" * 50 + "\n")
    
    # Example: Calculate team moneyline
    print("Example 2: Team Moneyline Probability")
    print("-" * 50)
    
    home_stats = TeamStats(
        team_id="DAL",
        team_name="Dallas Cowboys",
        wins=10,
        losses=3,
        win_percentage=0.769,
        avg_points_for=28.5,
        avg_points_against=20.2,
        is_home_team=True
    )
    
    away_stats = TeamStats(
        team_id="PHI",
        team_name="Philadelphia Eagles",
        wins=9,
        losses=4,
        win_percentage=0.692,
        avg_points_for=26.8,
        avg_points_against=22.1,
        is_home_team=False
    )
    
    game_context = GameContext(
        home_team="Dallas Cowboys",
        away_team="Philadelphia Eagles",
        home_team_stats=home_stats,
        away_team_stats=away_stats,
        sport="nfl"
    )
    
    moneyline = calculator.calculate_team_moneyline_probability(game_context)
    print(f"Home Win Probability: {moneyline['home_win_prob']:.3f}")
    print(f"Away Win Probability: {moneyline['away_win_prob']:.3f}")
    print(f"Confidence: {moneyline['confidence']:.3f}")
    
    print("\n" + "=" * 50 + "\n")
    
    # Example: Calculate spread probability
    print("Example 3: Team Spread Probability")
    print("-" * 50)
    
    spread = calculator.calculate_team_spread_probability(game_context, spread=-3.5)
    print(f"Home Covers Probability: {spread['home_covers_prob']:.3f}")
    print(f"Away Covers Probability: {spread['away_covers_prob']:.3f}")
    print(f"Expected Margin: {spread['expected_margin']:.1f}")
    print(f"Confidence: {spread['confidence']:.3f}")
    
    print("\n" + "=" * 50 + "\n")
    
    # Example: Calculate total probability
    print("Example 4: Team Total Probability")
    print("-" * 50)
    
    total = calculator.calculate_team_total_probability(game_context, total=48.5)
    print(f"Over Probability: {total['over_prob']:.3f}")
    print(f"Under Probability: {total['under_prob']:.3f}")
    print(f"Expected Total: {total['expected_total']:.1f}")
    print(f"Confidence: {total['confidence']:.3f}")


if __name__ == "__main__":
    main()
