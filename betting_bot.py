"""
Fantasy Probability Calculator - A comprehensive fantasy sports analysis tool
Analyzes odds from multiple sportsbooks and calculates fantasy performance probabilities
"""

import os
import sys
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fantasy_calculator.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

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

class DatabaseManager:
    """Manages SQLite database operations"""
    
    def __init__(self, db_path: str = "fantasy_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Teams table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teams (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                abbreviation TEXT NOT NULL,
                sport TEXT NOT NULL,
                conference TEXT,
                division TEXT
            )
        ''')
        
        # Players table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                team_id TEXT NOT NULL,
                position TEXT NOT NULL,
                sport TEXT NOT NULL,
                FOREIGN KEY (team_id) REFERENCES teams (id)
            )
        ''')
        
        # Games table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS games (
                id TEXT PRIMARY KEY,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                sport TEXT NOT NULL,
                start_time TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'scheduled'
            )
        ''')
        
        # Odds table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS odds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                bookmaker TEXT NOT NULL,
                market_type TEXT NOT NULL,
                selection TEXT NOT NULL,
                odds REAL NOT NULL,
                probability REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games (id)
            )
        ''')
        
        # Historical data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historical_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id TEXT NOT NULL,
                game_date DATE NOT NULL,
                opponent TEXT NOT NULL,
                result TEXT NOT NULL,
                score_for INTEGER,
                score_against INTEGER,
                sport TEXT NOT NULL,
                FOREIGN KEY (team_id) REFERENCES teams (id)
            )
        ''')
        
        # Player props table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_props (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                team_id TEXT NOT NULL,
                game_id TEXT NOT NULL,
                prop_type TEXT NOT NULL,
                line REAL NOT NULL,
                over_odds REAL NOT NULL,
                under_odds REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players (id),
                FOREIGN KEY (team_id) REFERENCES teams (id),
                FOREIGN KEY (game_id) REFERENCES games (id)
            )
        ''')
        
        # Player stats table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                team_id TEXT NOT NULL,
                position TEXT NOT NULL,
                sport TEXT NOT NULL,
                season TEXT NOT NULL,
                games_played INTEGER NOT NULL,
                stats_json TEXT NOT NULL,
                recent_form_json TEXT NOT NULL,
                season_average REAL NOT NULL,
                home_average REAL NOT NULL,
                away_average REAL NOT NULL,
                vs_opponent_average REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players (id),
                FOREIGN KEY (team_id) REFERENCES teams (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Fantasy database initialized successfully")
    
    def add_team(self, team: Team):
        """Add a team to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO teams 
            (id, name, abbreviation, sport, conference, division)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (team.id, team.name, team.abbreviation, team.sport, 
              team.conference, team.division))
        
        conn.commit()
        conn.close()
    
    def add_player(self, player: Player):
        """Add a player to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO players 
            (id, name, team_id, position, sport)
            VALUES (?, ?, ?, ?, ?)
        ''', (player.id, player.name, player.team_id, player.position, player.sport))
        
        conn.commit()
        conn.close()
    
    def add_game(self, game: Game):
        """Add a game to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO games 
            (id, home_team, away_team, sport, start_time, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (game.id, game.home_team, game.away_team, game.sport, 
              game.start_time, game.status))
        
        conn.commit()
        conn.close()
    
    def add_odds(self, odds: Odds):
        """Add odds to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO odds 
            (game_id, bookmaker, market_type, selection, odds, probability, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (odds.game_id, odds.bookmaker, odds.market_type, odds.selection,
              odds.odds, odds.probability, odds.timestamp))
        
        conn.commit()
        conn.close()
    
    def get_teams_by_sport(self, sport: str) -> List[Team]:
        """Get all teams for a specific sport"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM teams WHERE sport = ?', (sport,))
        rows = cursor.fetchall()
        
        teams = []
        for row in rows:
            teams.append(Team(
                id=row[0], name=row[1], abbreviation=row[2], 
                sport=row[3], conference=row[4], division=row[5]
            ))
        
        conn.close()
        return teams
    
    def get_upcoming_games(self, sport: str, days_ahead: int = 7) -> List[Game]:
        """Get upcoming games for a specific sport"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        end_date = datetime.now() + timedelta(days=days_ahead)
        cursor.execute('''
            SELECT * FROM games 
            WHERE sport = ? AND start_time BETWEEN ? AND ? AND status = 'scheduled'
            ORDER BY start_time
        ''', (sport, datetime.now(), end_date))
        
        rows = cursor.fetchall()
        games = []
        for row in rows:
            games.append(Game(
                id=row[0], home_team=row[1], away_team=row[2], 
                sport=row[3], start_time=datetime.fromisoformat(row[4]), 
                status=row[5]
            ))
        
        conn.close()
        return games
    
    def add_player_prop(self, player_prop: PlayerProp):
        """Add a player prop to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO player_props 
            (player_id, player_name, team_id, game_id, prop_type, line, over_odds, under_odds, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (player_prop.player_id, player_prop.player_name, player_prop.team_id,
              player_prop.game_id, player_prop.prop_type, player_prop.line,
              player_prop.over_odds, player_prop.under_odds, player_prop.timestamp))
        
        conn.commit()
        conn.close()
    
    def add_player_stats(self, player_stats: PlayerStats):
        """Add player statistics to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO player_stats 
            (player_id, player_name, team_id, position, sport, season, games_played,
             stats_json, recent_form_json, season_average, home_average, away_average, vs_opponent_average)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (player_stats.player_id, player_stats.player_name, player_stats.team_id,
              player_stats.position, player_stats.sport, player_stats.season,
              player_stats.games_played, json.dumps(player_stats.stats),
              json.dumps(player_stats.recent_form), player_stats.season_average,
              player_stats.home_average, player_stats.away_average, player_stats.vs_opponent_average))
        
        conn.commit()
        conn.close()
    
    def get_player_props_for_game(self, game_id: str) -> List[PlayerProp]:
        """Get all player props for a specific game"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT player_id, player_name, team_id, game_id, prop_type, line, 
                   over_odds, under_odds, timestamp
            FROM player_props 
            WHERE game_id = ?
            ORDER BY prop_type, line
        ''', (game_id,))
        
        rows = cursor.fetchall()
        player_props = []
        for row in rows:
            player_props.append(PlayerProp(
                player_id=row[0], player_name=row[1], team_id=row[2],
                game_id=row[3], prop_type=row[4], line=row[5],
                over_odds=row[6], under_odds=row[7], timestamp=datetime.fromisoformat(row[8])
            ))
        
        conn.close()
        return player_props
    
    def get_player_stats(self, player_id: str, season: str = None) -> Optional[PlayerStats]:
        """Get player statistics for a specific player"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if season:
            cursor.execute('''
                SELECT player_id, player_name, team_id, position, sport, season,
                       games_played, stats_json, recent_form_json, season_average,
                       home_average, away_average, vs_opponent_average
                FROM player_stats 
                WHERE player_id = ? AND season = ?
            ''', (player_id, season))
        else:
            cursor.execute('''
                SELECT player_id, player_name, team_id, position, sport, season,
                       games_played, stats_json, recent_form_json, season_average,
                       home_average, away_average, vs_opponent_average
                FROM player_stats 
                WHERE player_id = ?
                ORDER BY season DESC
                LIMIT 1
            ''', (player_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return PlayerStats(
                player_id=row[0], player_name=row[1], team_id=row[2],
                position=row[3], sport=row[4], season=row[5],
                games_played=row[6], stats=json.loads(row[7]),
                recent_form=json.loads(row[8]), season_average=row[9],
                home_average=row[10], away_average=row[11], vs_opponent_average=row[12]
            )
        return None
    
    def get_players_by_team(self, team_id: str, sport: str) -> List[Player]:
        """Get all players for a specific team"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, team_id, position, sport
            FROM players 
            WHERE team_id = ? AND sport = ?
        ''', (team_id, sport))
        
        rows = cursor.fetchall()
        players = []
        for row in rows:
            players.append(Player(
                id=row[0], name=row[1], team_id=row[2],
                position=row[3], sport=row[4]
            ))
        
        conn.close()
        return players

if __name__ == "__main__":
    # Initialize database
    db = DatabaseManager()
    logger.info("Fantasy Probability Calculator initialized successfully")
