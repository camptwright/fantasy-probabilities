"""
Shared data models for Fantasy Probability Calculator
Contains common data structures used across modules
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

@dataclass
class Team:
    """Represents a sports team"""
    id: str
    name: str
    abbreviation: str
    sport: str
    conference: Optional[str] = None
    division: Optional[str] = None

@dataclass
class Player:
    """Represents a player"""
    id: str
    name: str
    team_id: str
    position: str
    sport: str

@dataclass
class Game:
    """Represents a sports game"""
    id: str
    home_team: str
    away_team: str
    sport: str
    start_time: datetime
    status: str = "scheduled"

@dataclass
class Odds:
    """Represents betting odds"""
    game_id: str
    bookmaker: str
    market_type: str  # moneyline, spread, total, etc.
    selection: str  # team name or over/under
    odds: float
    probability: float
    timestamp: datetime

@dataclass
class PlayerProp:
    """Represents a player prop bet"""
    player_id: str
    player_name: str
    team_id: str
    game_id: str
    prop_type: str  # passing_yards, rushing_yards, receiving_yards, points, rebounds, etc.
    line: float  # The over/under line
    over_odds: float
    under_odds: float
    timestamp: datetime

@dataclass
class PlayerStats:
    """Represents player statistics"""
    player_id: str
    player_name: str
    team_id: str
    position: str
    sport: str
    season: str
    games_played: int
    stats: Dict[str, float]  # Various statistical categories
    recent_form: List[float]  # Last 5 games performance
    season_average: float
    home_average: float
    away_average: float
    vs_opponent_average: float

@dataclass
class FantasyRecommendation:
    """Represents a fantasy recommendation"""
    game_id: str
    market_type: str
    selection: str
    odds: float
    probability: float
    expected_value: float
    confidence: float
    reasoning: str
    player_id: Optional[str] = None  # For player props
    prop_type: Optional[str] = None  # For player props
    line: Optional[float] = None  # For player props
