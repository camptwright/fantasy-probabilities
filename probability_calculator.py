"""
Fantasy Probability Calculator Module
Calculates fantasy performance probabilities using historical data and statistical models
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import sqlite3
import json

logger = logging.getLogger(__name__)

# Import shared models
from models import PlayerStats

@dataclass
class TeamStats:
    """Team statistics for analysis"""
    team_id: str
    wins: int
    losses: int
    win_percentage: float
    home_record: Tuple[int, int]
    away_record: Tuple[int, int]
    recent_form: List[bool]  # Last 10 games results
    avg_points_for: float
    avg_points_against: float
    strength_of_schedule: float
    conference: Optional[str] = None  # NCAA conference
    ranking: Optional[int] = None  # AP/Coaches poll ranking
    is_home_team: bool = True

@dataclass
class GameContext:
    """Context for a specific game"""
    home_team: str
    away_team: str
    home_team_stats: TeamStats
    away_team_stats: TeamStats
    sport: str = "ncaaf"  # Default to NCAA Football
    weather: Optional[Dict] = None
    injuries: List[str] = None
    rest_days: Tuple[int, int] = None  # (home_rest, away_rest)
    rivalry_game: bool = False  # NCAA rivalry games
    conference_game: bool = False  # Conference matchup

class FantasyProbabilityCalculator:
    """Main class for calculating fantasy performance probabilities"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.models = {}
        self.scalers = {}
        self.feature_importance = {}
    
    def calculate_game_outcome_probability(self, game_context: GameContext) -> Dict[str, float]:
        """Calculate game outcome probabilities for both teams"""
        try:
            # Extract features
            features = self._extract_game_features(game_context)
            
            # Use trained model if available
            if 'game_outcome' in self.models:
                probabilities = self._predict_with_model(features, 'game_outcome')
            else:
                # Fallback to statistical calculation
                probabilities = self._calculate_statistical_probability(game_context)
            
            return {
                'home_win_probability': probabilities[0],
                'away_win_probability': probabilities[1],
                'confidence': self._calculate_confidence(features)
            }
            
        except Exception as e:
            logger.error(f"Error calculating game outcome probability: {e}")
            return {'home_win_probability': 0.5, 'away_win_probability': 0.5, 'confidence': 0.0}
    
    def calculate_point_differential_probability(self, game_context: GameContext, spread: float) -> Dict[str, float]:
        """Calculate point differential probability"""
        try:
            # Adjust team stats based on spread
            adjusted_context = self._adjust_for_spread(game_context, spread)
            
            # Calculate probability that home team covers the point differential
            features = self._extract_game_features(adjusted_context)
            
            if 'point_differential' in self.models:
                probability = self._predict_point_differential_with_model(features, spread)
            else:
                probability = self._calculate_point_differential_statistical(game_context, spread)
            
            return {
                'home_covers_probability': probability,
                'away_covers_probability': 1 - probability,
                'confidence': self._calculate_confidence(features)
            }
            
        except Exception as e:
            logger.error(f"Error calculating point differential probability: {e}")
            return {'home_covers_probability': 0.5, 'away_covers_probability': 0.5, 'confidence': 0.0}
    
    def calculate_total_points_probability(self, game_context: GameContext, total: float) -> Dict[str, float]:
        """Calculate total points probability"""
        try:
            # Calculate expected total based on team stats
            expected_total = self._calculate_expected_total(game_context)
            
            # Calculate probability based on historical variance
            variance = self._calculate_scoring_variance(game_context)
            
            # Use normal distribution approximation
            z_score = (total - expected_total) / np.sqrt(variance)
            over_probability = 1 - self._normal_cdf(z_score)
            
            return {
                'over_probability': over_probability,
                'under_probability': 1 - over_probability,
                'expected_total': expected_total,
                'confidence': min(abs(z_score) * 0.1, 1.0)
            }
            
        except Exception as e:
            logger.error(f"Error calculating total points probability: {e}")
            return {'over_probability': 0.5, 'under_probability': 0.5, 'confidence': 0.0}
    
    def calculate_player_performance_probability(self, player_stats: PlayerStats, prop_type: str, line: float, game_context: GameContext) -> Dict[str, float]:
        """Calculate player performance probability"""
        try:
            # Get the relevant stat from player stats
            stat_value = self._get_performance_stat_value(player_stats, prop_type)
            
            if stat_value is None:
                return {'over_probability': 0.5, 'under_probability': 0.5, 'confidence': 0.0}
            
            # Calculate expected value based on recent form and matchup
            expected_value = self._calculate_player_expected_performance(player_stats, game_context, prop_type)
            
            # Calculate variance based on player's consistency
            variance = self._calculate_player_performance_variance(player_stats, prop_type)
            
            # Apply matchup factors
            matchup_adjustment = self._calculate_matchup_adjustment(player_stats, game_context, prop_type)
            expected_value += matchup_adjustment
            
            # Calculate probability using normal distribution
            z_score = (line - expected_value) / np.sqrt(variance)
            over_probability = 1 - self._normal_cdf(z_score)
            
            # Calculate confidence based on sample size and consistency
            confidence = self._calculate_player_performance_confidence(player_stats, prop_type)
            
            return {
                'over_probability': over_probability,
                'under_probability': 1 - over_probability,
                'expected_value': expected_value,
                'confidence': confidence,
                'matchup_adjustment': matchup_adjustment
            }
            
        except Exception as e:
            logger.error(f"Error calculating player performance probability: {e}")
            return {'over_probability': 0.5, 'under_probability': 0.5, 'confidence': 0.0}
    
    def _get_performance_stat_value(self, player_stats: PlayerStats, prop_type: str) -> Optional[float]:
        """Get the relevant stat value for a performance type"""
        stat_mapping = {
            'passing_yards': 'passing_yards',
            'passing_tds': 'passing_tds',
            'rushing_yards': 'rushing_yards',
            'rushing_tds': 'rushing_tds',
            'receiving_yards': 'receiving_yards',
            'receiving_tds': 'receiving_tds',
            'receptions': 'receptions',
            'points': 'points',
            'rebounds': 'rebounds',
            'assists': 'assists',
            'steals': 'steals',
            'blocks': 'blocks'
        }
        
        stat_key = stat_mapping.get(prop_type)
        if stat_key and stat_key in player_stats.stats:
            return player_stats.stats[stat_key]
        
        return None
    
    def _calculate_player_expected_performance(self, player_stats: PlayerStats, game_context: GameContext, prop_type: str) -> float:
        """Calculate expected performance for player"""
        # Start with season average
        base_value = player_stats.season_average
        
        # Weight recent form more heavily
        if player_stats.recent_form:
            recent_avg = sum(player_stats.recent_form[-5:]) / min(len(player_stats.recent_form), 5)
            base_value = (base_value * 0.6) + (recent_avg * 0.4)
        
        # Apply home/away adjustment
        if game_context.home_team_stats.is_home_team:
            home_away_factor = player_stats.home_average / player_stats.season_average if player_stats.season_average > 0 else 1.0
        else:
            home_away_factor = player_stats.away_average / player_stats.season_average if player_stats.season_average > 0 else 1.0
        
        base_value *= home_away_factor
        
        return base_value
    
    def _calculate_player_performance_variance(self, player_stats: PlayerStats, prop_type: str) -> float:
        """Calculate variance for player performance"""
        # Use recent form to calculate variance
        if len(player_stats.recent_form) >= 3:
            variance = np.var(player_stats.recent_form)
        else:
            # Fallback to season average * 0.2 for typical variance
            variance = player_stats.season_average * 0.2
        
        # Sport-specific variance adjustments
        if player_stats.sport == "ncaaf":
            if prop_type in ['passing_yards', 'rushing_yards', 'receiving_yards']:
                variance *= 1.2  # Higher variance in college football
        elif player_stats.sport == "ncaab":
            if prop_type in ['points', 'rebounds', 'assists']:
                variance *= 0.8  # Lower variance in college basketball
        
        return max(variance, 1.0)  # Minimum variance of 1.0
    
    def _calculate_matchup_adjustment(self, player_stats: PlayerStats, game_context: GameContext, prop_type: str) -> float:
        """Calculate matchup-based adjustment"""
        adjustment = 0.0
        
        # Opponent defense adjustment
        if game_context.sport == "ncaaf":
            if prop_type == 'passing_yards':
                # Adjust based on opponent's pass defense
                opponent_pass_defense = game_context.away_team_stats.avg_points_against
                adjustment -= opponent_pass_defense * 0.1
            elif prop_type == 'rushing_yards':
                # Adjust based on opponent's rush defense
                opponent_rush_defense = game_context.away_team_stats.avg_points_against
                adjustment -= opponent_rush_defense * 0.05
        
        elif game_context.sport == "ncaab":
            if prop_type == 'points':
                # Adjust based on opponent's defense
                opponent_defense = game_context.away_team_stats.avg_points_against
                adjustment -= opponent_defense * 0.02
        
        # Conference strength adjustment
        if game_context.conference_game:
            conference_strength = self._get_conference_strength(player_stats.team_id.split('_')[0])
            adjustment += conference_strength * 0.1
        
        return adjustment
    
    def _calculate_player_performance_confidence(self, player_stats: PlayerStats, prop_type: str) -> float:
        """Calculate confidence in player performance prediction"""
        confidence = 0.5  # Base confidence
        
        # Sample size factor
        if player_stats.games_played >= 10:
            confidence += 0.2
        elif player_stats.games_played >= 5:
            confidence += 0.1
        
        # Consistency factor (lower variance = higher confidence)
        if len(player_stats.recent_form) >= 3:
            variance = np.var(player_stats.recent_form)
            consistency_factor = max(0, 1 - (variance / player_stats.season_average)) if player_stats.season_average > 0 else 0
            confidence += consistency_factor * 0.3
        
        return min(confidence, 1.0)
    
    def train_models(self, sport: str):
        """Train machine learning models using historical data"""
        try:
            logger.info(f"Training models for {sport}")
            
            # Get historical data
            historical_data = self._get_historical_training_data(sport)
            
            if len(historical_data) < 100:  # Need sufficient data
                logger.warning(f"Insufficient data for {sport} model training")
                return
            
            # Prepare features and targets
            X, y_moneyline, y_spread = self._prepare_training_data(historical_data)
            
            # Split data
            X_train, X_test, y_train_ml, y_test_ml = train_test_split(X, y_moneyline, test_size=0.2, random_state=42)
            _, _, y_train_spread, y_test_spread = train_test_split(X, y_spread, test_size=0.2, random_state=42)
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train game outcome model
            ml_model = RandomForestClassifier(n_estimators=100, random_state=42)
            ml_model.fit(X_train_scaled, y_train_ml)
            
            # Train point differential model
            point_diff_model = RandomForestClassifier(n_estimators=100, random_state=42)
            point_diff_model.fit(X_train_scaled, y_train_spread)
            
            # Evaluate models
            ml_accuracy = accuracy_score(y_test_ml, ml_model.predict(X_test_scaled))
            point_diff_accuracy = accuracy_score(y_test_spread, point_diff_model.predict(X_test_scaled))
            
            logger.info(f"Game outcome model accuracy: {ml_accuracy:.3f}")
            logger.info(f"Point differential model accuracy: {point_diff_accuracy:.3f}")
            
            # Store models
            self.models[f'{sport}_game_outcome'] = ml_model
            self.models[f'{sport}_point_differential'] = point_diff_model
            self.scalers[f'{sport}'] = scaler
            
            # Store feature importance
            self.feature_importance[f'{sport}_game_outcome'] = dict(zip(
                self._get_feature_names(), ml_model.feature_importances_
            ))
            
        except Exception as e:
            logger.error(f"Error training models for {sport}: {e}")
    
    def _extract_game_features(self, game_context: GameContext) -> np.ndarray:
        """Extract features for machine learning model"""
        home_stats = game_context.home_team_stats
        away_stats = game_context.away_team_stats
        
        features = [
            home_stats.win_percentage,
            away_stats.win_percentage,
            home_stats.home_record[0] / (home_stats.home_record[0] + home_stats.home_record[1]) if sum(home_stats.home_record) > 0 else 0.5,
            away_stats.away_record[0] / (away_stats.away_record[0] + away_stats.away_record[1]) if sum(away_stats.away_record) > 0 else 0.5,
            sum(home_stats.recent_form[-5:]) / 5,  # Last 5 games
            sum(away_stats.recent_form[-5:]) / 5,
            home_stats.avg_points_for,
            away_stats.avg_points_for,
            home_stats.avg_points_against,
            away_stats.avg_points_against,
            home_stats.strength_of_schedule,
            away_stats.strength_of_schedule,
        ]
        
        # Add rest days if available
        if game_context.rest_days:
            features.extend(game_context.rest_days)
        else:
            features.extend([0, 0])
        
        return np.array(features)
    
    def _calculate_statistical_probability(self, game_context: GameContext) -> Tuple[float, float]:
        """Calculate probability using statistical methods"""
        home_stats = game_context.home_team_stats
        away_stats = game_context.away_team_stats
        
        # Calculate team strength
        home_strength = home_stats.win_percentage * 0.4 + \
                       (home_stats.home_record[0] / (home_stats.home_record[0] + home_stats.home_record[1])) * 0.3 + \
                       sum(home_stats.recent_form[-5:]) / 5 * 0.3
        
        away_strength = away_stats.win_percentage * 0.4 + \
                       (away_stats.away_record[0] / (away_stats.away_record[0] + away_stats.away_record[1])) * 0.3 + \
                       sum(away_stats.recent_form[-5:]) / 5 * 0.3
        
        # Add NCAA-specific factors
        home_strength, away_strength = self._apply_ncaa_factors(
            home_strength, away_strength, game_context
        )
        
        # Calculate probabilities
        total_strength = home_strength + away_strength
        home_prob = home_strength / total_strength
        away_prob = away_strength / total_strength
        
        return home_prob, away_prob
    
    def _apply_ncaa_factors(self, home_strength: float, away_strength: float, 
                           game_context: GameContext) -> Tuple[float, float]:
        """Apply NCAA-specific factors to team strength calculations"""
        
        # Home field advantage varies by sport and conference
        if game_context.sport == "ncaaf":
            home_field_advantage = 0.07  # 7% for college football
        elif game_context.sport == "ncaab":
            home_field_advantage = 0.04  # 4% for college basketball
        else:
            home_field_advantage = 0.05  # Default 5%
        
        home_strength += home_field_advantage
        
        # Ranking factor (if teams are ranked)
        if game_context.home_team_stats.ranking and game_context.away_team_stats.ranking:
            ranking_diff = game_context.away_team_stats.ranking - game_context.home_team_stats.ranking
            ranking_factor = ranking_diff * 0.02  # 2% per ranking spot
            home_strength += ranking_factor
        
        # Conference strength factor
        if game_context.conference_game:
            conference_strength = self._get_conference_strength(game_context.home_team_stats.conference)
            if conference_strength:
                home_strength += conference_strength * 0.01
                away_strength += conference_strength * 0.01
        
        # Rivalry game factor
        if game_context.rivalry_game:
            rivalry_factor = 0.03  # 3% boost for rivalry games
            home_strength += rivalry_factor
        
        # Weather factor (for football)
        if game_context.sport == "ncaaf" and game_context.weather:
            weather_factor = self._calculate_weather_factor(game_context.weather)
            home_strength += weather_factor
        
        return home_strength, away_strength
    
    def _get_conference_strength(self, conference: str) -> float:
        """Get conference strength multiplier"""
        conference_strength = {
            "SEC": 1.0,
            "Big Ten": 0.95,
            "ACC": 0.90,
            "Big 12": 0.85,
            "Pac-12": 0.80,
            "AAC": 0.70,
            "Mountain West": 0.65,
            "MAC": 0.60,
            "Sun Belt": 0.55,
            "C-USA": 0.50
        }
        return conference_strength.get(conference, 0.75)
    
    def _calculate_weather_factor(self, weather: Dict) -> float:
        """Calculate weather impact factor"""
        # Simple weather factor - could be expanded
        if weather.get('temperature', 70) < 40:
            return 0.02  # Cold weather favors home team
        elif weather.get('wind_speed', 0) > 15:
            return 0.01  # Wind favors home team
        return 0.0
    
    def _calculate_point_differential_statistical(self, game_context: GameContext, spread: float) -> float:
        """Calculate point differential probability using statistical methods"""
        home_stats = game_context.home_team_stats
        away_stats = game_context.away_team_stats
        
        # Calculate expected margin
        expected_margin = (home_stats.avg_points_for - home_stats.avg_points_against) - \
                         (away_stats.avg_points_for - away_stats.avg_points_against)
        
        # Add sport-specific home field advantage
        if game_context.sport == "ncaaf":
            home_field_advantage = 3.5  # College football home field advantage
            variance = 16.0  # Higher variance in college football
        elif game_context.sport == "ncaab":
            home_field_advantage = 2.5  # College basketball home field advantage
            variance = 12.0  # Lower variance in college basketball
        else:
            home_field_advantage = 3.0  # Default
            variance = 14.0
        
        expected_margin += home_field_advantage
        
        # Add NCAA-specific adjustments
        if game_context.conference_game:
            expected_margin += 0.5  # Conference games tend to be closer
        
        if game_context.rivalry_game:
            expected_margin += 1.0  # Rivalry games can be unpredictable
        
        # Calculate probability using normal distribution
        z_score = (spread - expected_margin) / np.sqrt(variance)
        
        return 1 - self._normal_cdf(z_score)
    
    def _calculate_expected_total(self, game_context: GameContext) -> float:
        """Calculate expected total points"""
        home_stats = game_context.home_team_stats
        away_stats = game_context.away_team_stats
        
        # Calculate expected points for each team
        home_expected = (home_stats.avg_points_for + away_stats.avg_points_against) / 2
        away_expected = (away_stats.avg_points_for + home_stats.avg_points_against) / 2
        
        total = home_expected + away_expected
        
        # Apply sport-specific adjustments
        if game_context.sport == "ncaaf":
            # College football tends to have higher scoring
            total *= 1.05
        elif game_context.sport == "ncaab":
            # College basketball scoring varies by conference
            if game_context.conference_game:
                total *= 0.98  # Conference games can be lower scoring
        
        return total
    
    def _calculate_scoring_variance(self, game_context: GameContext) -> float:
        """Calculate variance in scoring"""
        # Sport-specific variance
        if game_context.sport == "ncaaf":
            return 30.0  # Higher variance in college football
        elif game_context.sport == "ncaab":
            return 20.0  # Lower variance in college basketball
        else:
            return 25.0  # Default variance
    
    def _calculate_player_expected_value(self, player_stats: List[float], game_context: GameContext, prop_type: str) -> float:
        """Calculate expected value for player prop"""
        # Weight recent games more heavily
        weights = np.exp(np.linspace(-1, 0, len(player_stats)))
        weights = weights / weights.sum()
        
        return np.average(player_stats, weights=weights)
    
    def _get_player_historical_stats(self, player_id: str, prop_type: str) -> List[float]:
        """Get historical stats for a player"""
        # This would query the database for player historical data
        # For now, return empty list
        return []
    
    def _get_historical_training_data(self, sport: str) -> List[Dict]:
        """Get historical data for training"""
        # This would query the database for historical games
        # For now, return empty list
        return []
    
    def _prepare_training_data(self, historical_data: List[Dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Prepare training data for machine learning"""
        # This would process historical data into features and targets
        # For now, return empty arrays
        return np.array([]), np.array([]), np.array([])
    
    def _get_feature_names(self) -> List[str]:
        """Get feature names for model interpretation"""
        return [
            'home_win_pct', 'away_win_pct', 'home_home_pct', 'away_away_pct',
            'home_recent_form', 'away_recent_form', 'home_pts_for', 'away_pts_for',
            'home_pts_against', 'away_pts_against', 'home_sos', 'away_sos',
            'home_rest_days', 'away_rest_days'
        ]
    
    def _predict_with_model(self, features: np.ndarray, model_type: str) -> Tuple[float, float]:
        """Predict using trained model"""
        # This would use the trained model to make predictions
        # For now, return equal probabilities
        return 0.5, 0.5
    
    def _predict_point_differential_with_model(self, features: np.ndarray, spread: float) -> float:
        """Predict point differential using trained model"""
        # This would use the trained model to predict point differential
        # For now, return 0.5
        return 0.5
    
    def _calculate_confidence(self, features: np.ndarray) -> float:
        """Calculate confidence in prediction"""
        # Simple confidence calculation based on feature variance
        return min(np.std(features) * 0.1, 1.0)
    
    def _adjust_for_spread(self, game_context: GameContext, spread: float) -> GameContext:
        """Adjust game context for point differential analysis"""
        # Adjust team stats based on spread
        adjusted_home_stats = game_context.home_team_stats
        adjusted_away_stats = game_context.away_team_stats
        
        # Adjust expected points based on spread
        adjusted_home_stats.avg_points_for -= spread / 2
        adjusted_away_stats.avg_points_for += spread / 2
        
        return GameContext(
            home_team=game_context.home_team,
            away_team=game_context.away_team,
            home_team_stats=adjusted_home_stats,
            away_team_stats=adjusted_away_stats,
            weather=game_context.weather,
            injuries=game_context.injuries,
            rest_days=game_context.rest_days
        )
    
    def _normal_cdf(self, x: float) -> float:
        """Calculate normal cumulative distribution function"""
        return 0.5 * (1 + np.math.erf(x / np.sqrt(2)))

class FantasyValueAnalyzer:
    """Analyzes fantasy value based on calculated probabilities"""
    
    def __init__(self, probability_calculator: FantasyProbabilityCalculator):
        self.prob_calculator = probability_calculator
    
    def find_fantasy_value_opportunities(self, odds_data: List[Dict], min_value: float = 0.05) -> List[Dict]:
        """Find fantasy value opportunities"""
        value_opportunities = []
        
        for odds in odds_data:
            try:
                # Calculate true probability
                true_prob = self._calculate_true_probability(odds)
                
                # Calculate implied probability from odds
                implied_prob = self.prob_calculator.convert_american_to_probability(odds['odds'])
                
                # Calculate expected value
                expected_value = (true_prob * odds['odds']) - (1 - true_prob)
                
                if expected_value > min_value:
                    value_opportunities.append({
                        'game_id': odds['game_id'],
                        'market_type': odds['market_type'],
                        'selection': odds['selection'],
                        'odds': odds['odds'],
                        'true_probability': true_prob,
                        'implied_probability': implied_prob,
                        'expected_value': expected_value,
                        'value_percentage': (true_prob - implied_prob) / implied_prob * 100
                    })
            
            except Exception as e:
                logger.error(f"Error analyzing odds: {e}")
                continue
        
        return sorted(value_opportunities, key=lambda x: x['expected_value'], reverse=True)
    
    def _calculate_true_probability(self, odds: Dict) -> float:
        """Calculate true probability for given odds"""
        # This would use the probability calculator to get true probability
        # For now, return a placeholder
        return 0.5

# Example usage
if __name__ == "__main__":
    # This would be used with actual database and game context
    print("Fantasy Probability Calculator Module Loaded")
