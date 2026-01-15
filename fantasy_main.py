"""
Main CLI Application for Fantasy Probability Calculator
Command-line interface for the fantasy sports probability analysis tool
"""

import click
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import schedule
import time
from threading import Thread

# Import our modules
from fantasy_calculator import DatabaseManager
from models import Team, Player, Game, Odds, FantasyRecommendation
from odds_api import OddsManager
from espn_scraper import ESPNScraper, HistoricalDataManager
from probability_calculator import FantasyProbabilityCalculator, FantasyValueAnalyzer, TeamStats, GameContext

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

class FantasyProbabilityApp:
    """Main application class for the fantasy probability calculator"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.odds_manager = OddsManager()
        self.espn_scraper = ESPNScraper()
        self.historical_manager = HistoricalDataManager(self.db_manager)
        self.prob_calculator = FantasyProbabilityCalculator(self.db_manager)
        self.value_analyzer = FantasyValueAnalyzer(self.prob_calculator)
        
        # Check for API keys
        self._check_api_keys()
    
    def _check_api_keys(self):
        """Check if required API keys are configured"""
        # Only THE_ODDS_API_KEY is required - ODDS_API_KEY is optional
        required_key = 'THE_ODDS_API_KEY'
        optional_keys = ['ODDS_API_KEY', 'SPORTSDATA_API_KEY']
        
        has_required = os.getenv(required_key) and os.getenv(required_key) != f'your_{required_key.lower()}_here'
        
        if not has_required:
            logger.warning(f"Missing required API key: {required_key}")
            logger.warning("The Odds API key is required for fetching odds and player props")
            logger.warning("Get your free key at: https://the-odds-api.com/")
        
        # Check optional keys
        missing_optional = []
        for key in optional_keys:
            if not os.getenv(key) or os.getenv(key) == f'your_{key.lower()}_here':
                missing_optional.append(key)
        
        if missing_optional:
            logger.info(f"Optional API keys not configured: {', '.join(missing_optional)}")
            logger.info("These are optional - The Odds API alone is sufficient")
    
    def update_odds(self, sport: str = None):
        """Update odds for all sports or specific sport"""
        sports = [sport] if sport else ['ncaaf', 'ncaab']  # Default to NCAA sports
        
        for sport_name in sports:
            try:
                logger.info(f"Updating odds for {sport_name}")
                
                # Get odds from all APIs
                all_odds = self.odds_manager.get_odds_for_sport(sport_name)
                
                if not all_odds:
                    logger.warning(f"No odds data received for {sport_name}")
                    continue
                
                # Process and store odds
                for api_name, odds_list in all_odds.items():
                    for odds_data in odds_list:
                        self._process_odds_data(odds_data, api_name)
                
                logger.info(f"Successfully updated odds for {sport_name}")
                
            except Exception as e:
                logger.error(f"Error updating odds for {sport_name}: {e}")
    
    def _process_odds_data(self, odds_data: Dict, api_name: str):
        """Process and store odds data"""
        try:
            # Extract game information
            game_id = odds_data.get('id', f"{api_name}_{datetime.now().timestamp()}")
            home_team = odds_data.get('home_team', 'Unknown')
            away_team = odds_data.get('away_team', 'Unknown')
            sport = odds_data.get('sport_key', 'unknown')
            start_time = datetime.fromisoformat(odds_data.get('commence_time', datetime.now().isoformat()))
            
            # Create game if it doesn't exist
            game = Game(
                id=game_id,
                home_team=home_team,
                away_team=away_team,
                sport=sport,
                start_time=start_time
            )
            self.db_manager.add_game(game)
            
            # Process odds for each bookmaker
            bookmakers = odds_data.get('bookmakers', [])
            for bookmaker in bookmakers:
                bookmaker_name = bookmaker.get('title', 'Unknown')
                
                # Process different markets
                markets = bookmaker.get('markets', [])
                for market in markets:
                    market_type = market.get('key', 'unknown')
                    outcomes = market.get('outcomes', [])
                    
                    for outcome in outcomes:
                        selection = outcome.get('name', 'Unknown')
                        odds_value = outcome.get('price', 0)
                        probability = self.odds_manager.convert_american_to_probability(odds_value)
                        
                        odds_obj = Odds(
                            game_id=game_id,
                            bookmaker=bookmaker_name,
                            market_type=market_type,
                            selection=selection,
                            odds=odds_value,
                            probability=probability,
                            timestamp=datetime.now()
                        )
                        
                        self.db_manager.add_fantasy_odds(odds_obj)
        
        except Exception as e:
            logger.error(f"Error processing odds data: {e}")
    
    def collect_historical_data(self, sport: str, seasons: List[int] = None):
        """Collect historical data for analysis"""
        try:
            logger.info(f"Collecting historical data for {sport}")
            
            if seasons is None:
                current_year = datetime.now().year
                seasons = [current_year - 1, current_year]
            
            # Collect team data
            self.historical_manager.collect_team_data(sport, seasons)
            
            # Collect game data for teams
            teams = self.db_manager.get_teams_by_sport(sport)
            team_names = [team.name for team in teams]
            
            if team_names:
                self.historical_manager.collect_game_data(sport, team_names, str(seasons[-1]))
            
            logger.info(f"Historical data collection completed for {sport}")
            
        except Exception as e:
            logger.error(f"Error collecting historical data for {sport}: {e}")
    
    def analyze_fantasy_opportunities(self, sport: str = None) -> List[Dict]:
        """Analyze fantasy opportunities and find value picks"""
        try:
            logger.info("Analyzing fantasy opportunities")
            
            sports = [sport] if sport else ['ncaaf', 'ncaab']  # Default to NCAA sports
            all_recommendations = []
            
            for sport_name in sports:
                # Get upcoming games
                games = self.db_manager.get_upcoming_games(sport_name, days_ahead=7)
                
                for game in games:
                    # Get odds for this game
                    game_odds = self._get_game_odds(game.id)
                    
                    if not game_odds:
                        continue
                    
                    # Analyze each market
                    recommendations = self._analyze_game_markets(game, game_odds)
                    all_recommendations.extend(recommendations)
            
            # Sort by expected value
            all_recommendations.sort(key=lambda x: x.get('expected_value', 0), reverse=True)
            
            logger.info(f"Found {len(all_recommendations)} fantasy opportunities")
            return all_recommendations
            
        except Exception as e:
            logger.error(f"Error analyzing fantasy opportunities: {e}")
            return []
    
    def _get_game_odds(self, game_id: str) -> List[Odds]:
        """Get odds for a specific game"""
        # This would query the database for odds
        # For now, return empty list
        return []
    
    def _analyze_game_markets(self, game: Game, odds_list: List[Odds]) -> List[Dict]:
        """Analyze fantasy markets for a specific game"""
        recommendations = []
        
        try:
            # Create game context
            game_context = self._create_game_context(game)
            
            if not game_context:
                return recommendations
            
            # Analyze each market type
            market_groups = {}
            for odds in odds_list:
                market_type = odds.market_type
                if market_type not in market_groups:
                    market_groups[market_type] = []
                market_groups[market_type].append(odds)
            
            # Analyze game outcomes
            if 'h2h' in market_groups:
                ml_recommendations = self._analyze_game_outcomes(game_context, market_groups['h2h'])
                recommendations.extend(ml_recommendations)
            
            # Analyze point differentials
            if 'spreads' in market_groups:
                spread_recommendations = self._analyze_point_differentials(game_context, market_groups['spreads'])
                recommendations.extend(spread_recommendations)
            
            # Analyze total points
            if 'totals' in market_groups:
                total_recommendations = self._analyze_total_points(game_context, market_groups['totals'])
                recommendations.extend(total_recommendations)
        
        except Exception as e:
            logger.error(f"Error analyzing game markets: {e}")
        
        return recommendations
    
    def _create_game_context(self, game: Game) -> Optional[GameContext]:
        """Create game context for analysis"""
        try:
            # Get team stats
            home_team_stats = self._get_team_stats(game.home_team, game.sport)
            away_team_stats = self._get_team_stats(game.away_team, game.sport)
            
            if not home_team_stats or not away_team_stats:
                return None
            
            return GameContext(
                home_team=game.home_team,
                away_team=game.away_team,
                home_team_stats=home_team_stats,
                away_team_stats=away_team_stats
            )
        
        except Exception as e:
            logger.error(f"Error creating game context: {e}")
            return None
    
    def _get_team_stats(self, team_name: str, sport: str) -> Optional[TeamStats]:
        """Get team statistics"""
        # This would query the database for team stats
        # For now, return placeholder stats
        return TeamStats(
            team_id=f"{team_name}_{sport}",
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
    
    def _analyze_game_outcomes(self, game_context: GameContext, odds_list: List[Odds]) -> List[Dict]:
        """Analyze game outcome opportunities"""
        recommendations = []
        
        try:
            # Calculate true probabilities
            probabilities = self.prob_calculator.calculate_game_outcome_probability(game_context)
            
            for odds in odds_list:
                implied_prob = odds.probability
                true_prob = probabilities['home_win_probability'] if 'home' in odds.selection.lower() else probabilities['away_win_probability']
                
                # Calculate expected value
                expected_value = (true_prob * odds.odds) - (1 - true_prob)
                
                if expected_value > 0.05:  # 5% minimum value
                    recommendations.append({
                        'game_id': odds.game_id,
                        'market_type': 'game_outcome',
                        'selection': odds.selection,
                        'odds': odds.odds,
                        'true_probability': true_prob,
                        'implied_probability': implied_prob,
                        'expected_value': expected_value,
                        'confidence': probabilities['confidence'],
                        'bookmaker': odds.bookmaker,
                        'reasoning': f"True probability ({true_prob:.3f}) > Implied probability ({implied_prob:.3f})"
                    })
        
        except Exception as e:
            logger.error(f"Error analyzing game outcomes: {e}")
        
        return recommendations
    
    def _analyze_point_differentials(self, game_context: GameContext, odds_list: List[Odds]) -> List[Dict]:
        """Analyze point differential opportunities"""
        recommendations = []
        
        try:
            for odds in odds_list:
                # Extract point differential from odds data
                spread = self._extract_spread_from_odds(odds)
                
                if spread is None:
                    continue
                
                # Calculate probability
                probabilities = self.prob_calculator.calculate_point_differential_probability(game_context, spread)
                
                implied_prob = odds.probability
                true_prob = probabilities['home_covers_probability'] if 'home' in odds.selection.lower() else probabilities['away_covers_probability']
                
                # Calculate expected value
                expected_value = (true_prob * odds.odds) - (1 - true_prob)
                
                if expected_value > 0.05:
                    recommendations.append({
                        'game_id': odds.game_id,
                        'market_type': 'point_differential',
                        'selection': odds.selection,
                        'odds': odds.odds,
                        'spread': spread,
                        'true_probability': true_prob,
                        'implied_probability': implied_prob,
                        'expected_value': expected_value,
                        'confidence': probabilities['confidence'],
                        'bookmaker': odds.bookmaker,
                        'reasoning': f"Point differential analysis shows value in {odds.selection}"
                    })
        
        except Exception as e:
            logger.error(f"Error analyzing point differentials: {e}")
        
        return recommendations
    
    def _analyze_total_points(self, game_context: GameContext, odds_list: List[Odds]) -> List[Dict]:
        """Analyze total points opportunities"""
        recommendations = []
        
        try:
            for odds in odds_list:
                # Extract total from odds data
                total = self._extract_total_from_odds(odds)
                
                if total is None:
                    continue
                
                # Calculate probability
                probabilities = self.prob_calculator.calculate_total_points_probability(game_context, total)
                
                implied_prob = odds.probability
                true_prob = probabilities['over_probability'] if 'over' in odds.selection.lower() else probabilities['under_probability']
                
                # Calculate expected value
                expected_value = (true_prob * odds.odds) - (1 - true_prob)
                
                if expected_value > 0.05:
                    recommendations.append({
                        'game_id': odds.game_id,
                        'market_type': 'total_points',
                        'selection': odds.selection,
                        'odds': odds.odds,
                        'total': total,
                        'true_probability': true_prob,
                        'implied_probability': implied_prob,
                        'expected_value': expected_value,
                        'confidence': probabilities['confidence'],
                        'bookmaker': odds.bookmaker,
                        'reasoning': f"Expected total ({probabilities['expected_total']:.1f}) vs line ({total})"
                    })
        
        except Exception as e:
            logger.error(f"Error analyzing total points: {e}")
        
        return recommendations
    
    def _extract_spread_from_odds(self, odds: Odds) -> Optional[float]:
        """Extract spread value from odds data"""
        # This would parse the spread from the odds selection
        # For now, return None
        return None
    
    def _extract_total_from_odds(self, odds: Odds) -> Optional[float]:
        """Extract total value from odds data"""
        # This would parse the total from the odds selection
        # For now, return None
        return None
    
    def train_models(self, sport: str):
        """Train machine learning models"""
        try:
            logger.info(f"Training models for {sport}")
            self.prob_calculator.train_models(sport)
            logger.info(f"Model training completed for {sport}")
        except Exception as e:
            logger.error(f"Error training models for {sport}: {e}")
    
    def update_player_props(self, sport: str = None):
        """Update player prop odds for all sports or specific sport"""
        sports = [sport] if sport else ['ncaaf', 'ncaab']  # Default to NCAA sports
        
        for sport_name in sports:
            try:
                logger.info(f"Updating player props for {sport_name}")
                
                # Get player props from all APIs
                all_props = self.odds_manager.get_player_props_for_sport(sport_name)
                
                if not all_props:
                    logger.warning(f"No player prop data received for {sport_name}")
                    continue
                
                # Process and store player props
                for api_name, props_list in all_props.items():
                    for prop_data in props_list:
                        self._process_player_prop_data(prop_data, api_name)
                
                logger.info(f"Successfully updated player props for {sport_name}")
                
            except Exception as e:
                logger.error(f"Error updating player props for {sport_name}: {e}")
    
    def _process_player_prop_data(self, prop_data: Dict, api_name: str):
        """Process and store player prop data"""
        try:
            # Extract player prop information
            player_name = prop_data.get('player_name', 'Unknown')
            team = prop_data.get('team', 'Unknown')
            game_id = prop_data.get('game_id', f"{api_name}_{datetime.now().timestamp()}")
            prop_type = prop_data.get('prop_type', 'unknown')
            line = prop_data.get('line', 0)
            over_odds = prop_data.get('over_odds', 0)
            under_odds = prop_data.get('under_odds', 0)
            
            # Create player prop object
            player_prop = PlayerProp(
                player_id=f"{player_name}_{team}",
                player_name=player_name,
                team_id=team,
                game_id=game_id,
                prop_type=prop_type,
                line=line,
                over_odds=over_odds,
                under_odds=under_odds,
                timestamp=datetime.now()
            )
            
            self.db_manager.add_player_performance_prop(player_prop)
        
        except Exception as e:
            logger.error(f"Error processing player prop data: {e}")
    
    def collect_player_data(self, sport: str, seasons: List[int] = None):
        """Collect player statistics for analysis"""
        try:
            logger.info(f"Collecting player data for {sport}")
            
            if seasons is None:
                current_year = datetime.now().year
                seasons = [current_year - 1, current_year]
            
            for season in seasons:
                logger.info(f"Collecting player stats for {sport} {season}")
                
                # Get player statistics
                players = self.espn_scraper.get_player_stats(sport, str(season))
                
                for player_data in players:
                    # Convert to PlayerStats object
                    player_stats = PlayerStats(
                        player_id=f"{player_data['player']}_{player_data['team']}_{season}",
                        player_name=player_data['player'],
                        team_id=player_data['team'],
                        position="Unknown",  # Would need to be extracted
                        sport=sport,
                        season=str(season),
                        games_played=10,  # Would need to be calculated
                        stats=player_data['stats'],
                        recent_form=[player_data['season_average']] * 5,  # Placeholder
                        season_average=player_data['season_average'],
                        home_average=player_data['season_average'] * 1.05,  # Placeholder
                        away_average=player_data['season_average'] * 0.95,  # Placeholder
                        vs_opponent_average=player_data['season_average']  # Placeholder
                    )
                    
                    self.db_manager.add_player_stats(player_stats)
                
                logger.info(f"Player data collection completed for {sport} {season}")
            
        except Exception as e:
            logger.error(f"Error collecting player data for {sport}: {e}")
    
    def analyze_player_prop_opportunities(self, sport: str = None) -> List[Dict]:
        """Analyze player prop betting opportunities"""
        try:
            logger.info("Analyzing player prop opportunities")
            
            sports = [sport] if sport else ['ncaaf', 'ncaab']  # Default to NCAA sports
            all_recommendations = []
            
            for sport_name in sports:
                # Get upcoming games
                games = self.db_manager.get_upcoming_games(sport_name, days_ahead=7)
                
                for game in games:
                    # Get player performance props for this game
                    player_props = self.db_manager.get_player_performance_props_for_game(game.id)
                    
                    if not player_props:
                        continue
                    
                    # Analyze each player prop
                    recommendations = self._analyze_player_props(game, player_props)
                    all_recommendations.extend(recommendations)
            
            # Sort by expected value
            all_recommendations.sort(key=lambda x: x.get('expected_value', 0), reverse=True)
            
            logger.info(f"Found {len(all_recommendations)} player prop opportunities")
            return all_recommendations
            
        except Exception as e:
            logger.error(f"Error analyzing player prop opportunities: {e}")
            return []
    
    def _analyze_player_props(self, game: Game, player_props: List[PlayerProp]) -> List[Dict]:
        """Analyze player props for a specific game"""
        recommendations = []
        
        try:
            # Create game context
            game_context = self._create_game_context(game)
            
            if not game_context:
                return recommendations
            
            for prop in player_props:
                # Get player stats
                player_stats = self.db_manager.get_player_stats(prop.player_id)
                
                if not player_stats:
                    continue
                
                # Calculate probabilities for over and under
                over_prob = self.prob_calculator.calculate_player_prop_probability(
                    player_stats, prop.prop_type, prop.line, game_context
                )
                
                # Analyze over bet
                over_implied_prob = self.odds_manager.convert_american_to_probability(prop.over_odds)
                over_expected_value = (over_prob['over_probability'] * prop.over_odds) - (1 - over_prob['over_probability'])
                
                if over_expected_value > 0.05:  # 5% minimum value
                    recommendations.append({
                        'player_name': prop.player_name,
                        'prop_type': prop.prop_type,
                        'selection': 'Over',
                        'line': prop.line,
                        'odds': prop.over_odds,
                        'true_probability': over_prob['over_probability'],
                        'implied_probability': over_implied_prob,
                        'expected_value': over_expected_value,
                        'confidence': over_prob['confidence'],
                        'bookmaker': 'Unknown',  # Would need to be extracted
                        'reasoning': f"Expected {over_prob['expected_value']:.1f} vs line {prop.line}"
                    })
                
                # Analyze under bet
                under_prob = self.prob_calculator.calculate_player_prop_probability(
                    player_stats, prop.prop_type, prop.line, game_context
                )
                
                under_implied_prob = self.odds_manager.convert_american_to_probability(prop.under_odds)
                under_expected_value = (under_prob['under_probability'] * prop.under_odds) - (1 - under_prob['under_probability'])
                
                if under_expected_value > 0.05:  # 5% minimum value
                    recommendations.append({
                        'player_name': prop.player_name,
                        'prop_type': prop.prop_type,
                        'selection': 'Under',
                        'line': prop.line,
                        'odds': prop.under_odds,
                        'true_probability': under_prob['under_probability'],
                        'implied_probability': under_implied_prob,
                        'expected_value': under_expected_value,
                        'confidence': under_prob['confidence'],
                        'bookmaker': 'Unknown',  # Would need to be extracted
                        'reasoning': f"Expected {under_prob['expected_value']:.1f} vs line {prop.line}"
                    })
        
        except Exception as e:
            logger.error(f"Error analyzing player props: {e}")
        
        return recommendations
    
    def start_monitoring(self, update_interval: int = 30):
        """Start continuous monitoring of odds and opportunities"""
        logger.info(f"Starting monitoring with {update_interval} minute intervals")
        
        # Schedule updates
        schedule.every(update_interval).minutes.do(self.update_odds)
        schedule.every(1).hours.do(self._log_opportunities)
        
        # Start monitoring loop
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def _log_opportunities(self):
        """Log current betting opportunities"""
        try:
            opportunities = self.analyze_betting_opportunities()
            
            if opportunities:
                logger.info(f"Found {len(opportunities)} betting opportunities")
                
                # Log top 5 opportunities
                for i, opp in enumerate(opportunities[:5]):
                    logger.info(f"#{i+1}: {opp['selection']} @ {opp['odds']} "
                              f"(EV: {opp['expected_value']:.3f}, "
                              f"Confidence: {opp['confidence']:.3f})")
            else:
                logger.info("No betting opportunities found")
        
        except Exception as e:
            logger.error(f"Error logging opportunities: {e}")

# CLI Commands
@click.group()
def cli():
    """Fantasy Probability Calculator - Analyze odds and find fantasy value opportunities"""
    pass

@cli.command()
@click.option('--sport', help='Sport to update odds for (ncaaf, ncaab, nfl, nba, mlb, nhl)')
def update_odds(sport):
    """Update odds from all available APIs"""
    app = FantasyProbabilityApp()
    app.update_odds(sport)

@cli.command()
@click.option('--sport', required=True, help='Sport to collect data for')
@click.option('--seasons', help='Comma-separated list of seasons (e.g., 2022,2023)')
def collect_data(sport, seasons):
    """Collect historical data from ESPN"""
    app = FantasyProbabilityApp()
    
    season_list = None
    if seasons:
        season_list = [int(s.strip()) for s in seasons.split(',')]
    
    app.collect_historical_data(sport, season_list)

@cli.command()
@click.option('--sport', help='Sport to analyze (ncaaf, ncaab, nfl, nba, mlb, nhl)')
@click.option('--min-value', default=0.05, help='Minimum expected value threshold')
def analyze(sport, min_value):
    """Analyze fantasy opportunities and find value picks"""
    app = FantasyProbabilityApp()
    opportunities = app.analyze_fantasy_opportunities(sport)
    
    if not opportunities:
        click.echo("No fantasy opportunities found")
        return
    
    click.echo(f"\nFound {len(opportunities)} fantasy opportunities:\n")
    
    for i, opp in enumerate(opportunities[:10]):  # Show top 10
        click.echo(f"{i+1}. {opp['selection']} @ {opp['odds']}")
        click.echo(f"   Expected Value: {opp['expected_value']:.3f}")
        click.echo(f"   True Probability: {opp['true_probability']:.3f}")
        click.echo(f"   Implied Probability: {opp['implied_probability']:.3f}")
        click.echo(f"   Confidence: {opp['confidence']:.3f}")
        click.echo(f"   Bookmaker: {opp['bookmaker']}")
        click.echo(f"   Reasoning: {opp['reasoning']}")
        click.echo()

@cli.command()
@click.option('--sport', required=True, help='Sport to train models for')
def train(sport):
    """Train machine learning models using historical data"""
    app = FantasyProbabilityApp()
    app.train_models(sport)

@cli.command()
@click.option('--sport', help='Sport to update player props for (ncaaf, ncaab)')
def update_player_props(sport):
    """Update player performance odds from all available APIs"""
    app = FantasyProbabilityApp()
    app.update_player_props(sport)

@cli.command()
@click.option('--sport', required=True, help='Sport to collect player data for')
@click.option('--seasons', help='Comma-separated list of seasons (e.g., 2022,2023)')
def collect_player_data(sport, seasons):
    """Collect player statistics from ESPN"""
    app = FantasyProbabilityApp()
    
    season_list = None
    if seasons:
        season_list = [int(s.strip()) for s in seasons.split(',')]
    
    app.collect_player_data(sport, season_list)

@cli.command()
@click.option('--sport', help='Sport to analyze player props for (ncaaf, ncaab)')
@click.option('--min-value', default=0.05, help='Minimum expected value threshold')
def analyze_player_props(sport, min_value):
    """Analyze player performance opportunities"""
    app = FantasyProbabilityApp()
    opportunities = app.analyze_player_prop_opportunities(sport)
    
    if not opportunities:
        click.echo("No player performance opportunities found")
        return
    
    click.echo(f"\nFound {len(opportunities)} player performance opportunities:\n")
    
    for i, opp in enumerate(opportunities[:10]):  # Show top 10
        click.echo(f"{i+1}. {opp['player_name']} - {opp['prop_type']} {opp['selection']} @ {opp['odds']}")
        click.echo(f"   Line: {opp['line']}")
        click.echo(f"   Expected Value: {opp['expected_value']:.3f}")
        click.echo(f"   True Probability: {opp['true_probability']:.3f}")
        click.echo(f"   Implied Probability: {opp['implied_probability']:.3f}")
        click.echo(f"   Confidence: {opp['confidence']:.3f}")
        click.echo(f"   Expected Performance: {opp['expected_value']:.1f}")
        click.echo(f"   Bookmaker: {opp['bookmaker']}")
        click.echo(f"   Reasoning: {opp['reasoning']}")
        click.echo()

@cli.command()
@click.option('--interval', default=30, help='Update interval in minutes')
def monitor(interval):
    """Start continuous monitoring of odds and opportunities"""
    app = FantasyProbabilityApp()
    app.start_monitoring(interval)

@cli.command()
def status():
    """Show current status and configuration"""
    app = FantasyProbabilityApp()
    
    click.echo("Fantasy Probability Calculator Status:")
    click.echo("=====================================")
    
    # Check API keys
    # Only THE_ODDS_API_KEY is required, others are optional
    required_key = 'THE_ODDS_API_KEY'
    optional_keys = ['ODDS_API_KEY', 'SPORTSDATA_API_KEY']
    click.echo("\nAPI Keys:")
    # Check required key
    status = "OK" if os.getenv(required_key) and os.getenv(required_key) != f'your_{required_key.lower()}_here' else "NOT SET"
    click.echo(f"  {required_key}: {status} (REQUIRED)")
    # Check optional keys
    for key in optional_keys:
        status = "OK" if os.getenv(key) and os.getenv(key) != f'your_{key.lower()}_here' else "NOT SET"
        click.echo(f"  {key}: {status} (optional)")
    
    # Check database
    click.echo(f"\nDatabase: fantasy_data.db")
    
    # Check available sports
    click.echo(f"\nAvailable Sports: NCAA Football (ncaaf), NCAA Basketball (ncaab), NFL, NBA, MLB, NHL")

if __name__ == '__main__':
    cli()
