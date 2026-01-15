"""
Odds API Integration Module
Handles fetching odds from various sportsbooks and APIs
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import os
import json

logger = logging.getLogger(__name__)

class OddsAPI:
    """Base class for odds API integration"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = ""
        self.headers = {}
    
    def get_odds(self, sport: str, markets: List[str] = None) -> List[Dict]:
        """Get odds for a specific sport"""
        raise NotImplementedError
    
    def get_games(self, sport: str) -> List[Dict]:
        """Get upcoming games for a specific sport"""
        raise NotImplementedError

class TheOddsAPI(OddsAPI):
    """Integration with The Odds API (https://the-odds-api.com/)"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://api.the-odds-api.com/v4"
        # Note: The Odds API uses apiKey as a query parameter, not a header
    
    def get_sports(self) -> List[Dict]:
        """Get list of available sports"""
        try:
            params = {"apiKey": self.api_key}
            response = requests.get(f"{self.base_url}/sports", params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error(f"401 Unauthorized: Invalid or missing API key for The Odds API")
                logger.error(f"Please check your THE_ODDS_API_KEY in .env file")
            else:
                logger.error(f"Error fetching sports: {e}")
            return []
        except requests.RequestException as e:
            logger.error(f"Error fetching sports: {e}")
            return []
    
    def get_odds(self, sport: str, markets: List[str] = None, regions: List[str] = None) -> List[Dict]:
        """Get odds for a specific sport"""
        if markets is None:
            markets = ["h2h", "spreads", "totals"]
        if regions is None:
            regions = ["us"]
        
        api_sport = self._map_sport(sport)
        
        try:
            params = {
                "apiKey": self.api_key,
                "sport": api_sport,
                "markets": ",".join(markets),
                "regions": ",".join(regions),
                "oddsFormat": "american",
                "dateFormat": "iso"
            }
            
            response = requests.get(f"{self.base_url}/sports/{api_sport}/odds", 
                                 params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error(f"401 Unauthorized: Invalid or missing API key for The Odds API")
                logger.error(f"Please check your THE_ODDS_API_KEY in .env file")
                logger.error(f"Get your free API key at: https://the-odds-api.com/")
            else:
                logger.error(f"Error fetching odds for {sport}: {e}")
            return []
        except requests.RequestException as e:
            logger.error(f"Error fetching odds for {sport}: {e}")
            return []
    
    
    def get_games(self, sport: str) -> List[Dict]:
        """Get upcoming games for a specific sport"""
        api_sport = self._map_sport(sport)
        
        try:
            params = {"apiKey": self.api_key}
            response = requests.get(f"{self.base_url}/sports/{api_sport}/scores", 
                                 params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error(f"401 Unauthorized: Invalid or missing API key for The Odds API")
                logger.error(f"Please check your THE_ODDS_API_KEY in .env file")
            else:
                logger.error(f"Error fetching games for {sport}: {e}")
            return []
        except requests.RequestException as e:
            logger.error(f"Error fetching games for {sport}: {e}")
            return []
    
    def get_player_props(self, sport: str, markets: List[str] = None, regions: List[str] = None) -> List[Dict]:
        """Get player prop odds for a specific sport
        
        Supported player prop markets:
        NFL: player_pass_tds, player_pass_yds, player_pass_completions,
             player_rush_yds, player_rush_attempts, player_receptions,
             player_receiving_yds
        NBA: player_points, player_rebounds, player_assists, player_steals,
             player_blocks, player_threes
        MLB: player_hits, player_home_runs, player_total_bases, player_rbis,
             player_stolen_bases
        NHL: player_points, player_goals, player_assists, player_shots
        """
        if markets is None:
            # Default player prop markets based on sport
            api_sport = self._map_sport(sport)
            sport_defaults = {
                "americanfootball_nfl": ["player_pass_yds", "player_pass_tds", "player_rush_yds"],
                "basketball_nba": ["player_points", "player_rebounds", "player_assists"],
                "baseball_mlb": ["player_hits", "player_home_runs"],
                "icehockey_nhl": ["player_points", "player_goals"]
            }
            markets = sport_defaults.get(api_sport, ["player_points"])
        
        if regions is None:
            regions = ["us"]
        
        # Use get_odds with player prop markets
        return self.get_odds(sport, markets, regions)
    
    def _map_sport(self, sport: str) -> str:
        """Map sport name to API sport key"""
        sport_mapping = {
            "ncaaf": "americanfootball_ncaaf",
            "ncaab": "basketball_ncaab",
            "nfl": "americanfootball_nfl",
            "nba": "basketball_nba",
            "mlb": "baseball_mlb",
            "nhl": "icehockey_nhl"
        }
        return sport_mapping.get(sport, sport)

class OddsAPICom(OddsAPI):
    """Integration with OddsAPI.com"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://api.oddsapi.com/v1"
        self.headers = {"apikey": api_key}
    
    def get_odds(self, sport: str, markets: List[str] = None) -> List[Dict]:
        """Get odds for a specific sport"""
        if markets is None:
            markets = ["h2h", "spreads", "totals"]
        
        try:
            params = {
                "sport": sport,
                "region": "us",
                "mkt": ",".join(markets),
                "dateFormat": "iso"
            }
            
            response = requests.get(f"{self.base_url}/odds", 
                                 headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching odds for {sport}: {e}")
            return []
    
    def get_player_props(self, sport: str, markets: List[str] = None) -> List[Dict]:
        """Get player prop odds for a specific sport"""
        if markets is None:
            # Common player prop markets
            markets = [
                "player_pass_tds", "player_pass_yds", "player_pass_completions",
                "player_rush_yds", "player_rush_attempts", "player_receptions",
                "player_receiving_yds", "player_points", "player_rebounds",
                "player_assists", "player_steals", "player_blocks"
            ]
        
        try:
            params = {
                "sport": sport,
                "region": "us",
                "mkt": ",".join(markets),
                "dateFormat": "iso"
            }
            
            response = requests.get(f"{self.base_url}/odds", 
                                 headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching player props for {sport}: {e}")
            return []

class SportsDataIO(OddsAPI):
    """Integration with SportsData.io"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://api.sportsdata.io/v3"
        self.headers = {"Ocp-Apim-Subscription-Key": api_key}
    
    def get_odds(self, sport: str, markets: List[str] = None) -> List[Dict]:
        """Get odds for a specific sport"""
        # SportsData.io has different endpoints for different sports
        sport_endpoints = {
            "nfl": "nfl",
            "nba": "nba",
            "mlb": "mlb",
            "nhl": "nhl"
        }
        
        if sport not in sport_endpoints:
            logger.error(f"Sport {sport} not supported by SportsData.io")
            return []
        
        try:
            endpoint = sport_endpoints[sport]
            response = requests.get(f"{self.base_url}/{endpoint}/odds/json/GameOddsByWeek/2023/1", 
                                 headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching odds for {sport}: {e}")
            return []

class OddsManager:
    """Manages multiple odds APIs and provides unified interface"""
    
    def __init__(self):
        self.apis = {}
        self._initialize_apis()
    
    def _initialize_apis(self):
        """Initialize available APIs based on environment variables"""
        # The Odds API
        odds_api_key = os.getenv("THE_ODDS_API_KEY")
        if odds_api_key and odds_api_key != "your_the_odds_api_key_here" and odds_api_key.strip():
            self.apis["the_odds_api"] = TheOddsAPI(odds_api_key)
            logger.info("The Odds API initialized")
        elif not odds_api_key or odds_api_key == "your_the_odds_api_key_here":
            logger.warning("THE_ODDS_API_KEY not configured or using placeholder value")
            logger.warning("Get your free API key at: https://the-odds-api.com/")
            logger.warning("Add it to your .env file: THE_ODDS_API_KEY=your_key_here")
        
        # OddsAPI.com
        oddsapi_key = os.getenv("ODDS_API_KEY")
        if oddsapi_key:
            self.apis["oddsapi"] = OddsAPICom(oddsapi_key)
            logger.info("OddsAPI.com initialized")
        
        # SportsData.io
        sportsdata_key = os.getenv("SPORTSDATA_API_KEY")
        if sportsdata_key:
            self.apis["sportsdata"] = SportsDataIO(sportsdata_key)
            logger.info("SportsData.io initialized")
    
    def get_odds_for_sport(self, sport: str, markets: List[str] = None) -> Dict[str, List[Dict]]:
        """Get odds from all available APIs for a specific sport"""
        all_odds = {}
        
        for api_name, api in self.apis.items():
            try:
                odds = api.get_odds(sport, markets)
                if odds:
                    all_odds[api_name] = odds
                    logger.info(f"Retrieved {len(odds)} odds from {api_name}")
            except Exception as e:
                logger.error(f"Error getting odds from {api_name}: {e}")
        
        return all_odds
    
    def get_player_props_for_sport(self, sport: str, markets: List[str] = None) -> Dict[str, List[Dict]]:
        """Get player prop odds from all available APIs for a specific sport"""
        all_props = {}
        
        for api_name, api in self.apis.items():
            try:
                # Check if API supports player props method
                if hasattr(api, 'get_player_props'):
                    props = api.get_player_props(sport, markets)
                    if props:
                        all_props[api_name] = props
                        logger.info(f"Retrieved {len(props)} player props from {api_name}")
                else:
                    # Fallback: try to get player props using regular get_odds with player markets
                    player_markets = markets or [
                        "player_pass_tds", "player_pass_yds", "player_rush_yds",
                        "player_receptions", "player_receiving_yds", "player_points",
                        "player_rebounds", "player_assists"
                    ]
                    props = api.get_odds(sport, player_markets)
                    if props:
                        all_props[api_name] = props
                        logger.info(f"Retrieved {len(props)} player props from {api_name}")
            except Exception as e:
                logger.error(f"Error getting player props from {api_name}: {e}")
        
        return all_props
    
    def get_games_for_sport(self, sport: str) -> Dict[str, List[Dict]]:
        """Get games from all available APIs for a specific sport"""
        all_games = {}
        
        for api_name, api in self.apis.items():
            try:
                games = api.get_games(sport)
                if games:
                    all_games[api_name] = games
                    logger.info(f"Retrieved {len(games)} games from {api_name}")
            except Exception as e:
                logger.error(f"Error getting games from {api_name}: {e}")
        
        return all_games
    
    def convert_american_to_decimal(self, american_odds: float) -> float:
        """Convert American odds to decimal odds"""
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1
    
    def convert_american_to_probability(self, american_odds: float) -> float:
        """Convert American odds to implied probability"""
        decimal_odds = self.convert_american_to_decimal(american_odds)
        return 1 / decimal_odds
    
    def calculate_fair_odds(self, odds_list: List[float]) -> float:
        """Calculate fair odds from multiple bookmaker odds"""
        if not odds_list:
            return 0
        
        # Convert to probabilities
        probabilities = [self.convert_american_to_probability(odds) for odds in odds_list]
        
        # Calculate average probability
        avg_probability = sum(probabilities) / len(probabilities)
        
        # Convert back to American odds
        if avg_probability >= 0.5:
            return (avg_probability / (1 - avg_probability)) * -100
        else:
            return ((1 - avg_probability) / avg_probability) * 100

# Example usage and testing
if __name__ == "__main__":
    # Test the odds manager
    odds_manager = OddsManager()
    
    # Test with NFL
    nfl_odds = odds_manager.get_odds_for_sport("americanfootball_nfl")
    print(f"NFL Odds from {len(nfl_odds)} sources: {nfl_odds}")
    
    # Test odds conversion
    test_odds = 150
    decimal = odds_manager.convert_american_to_decimal(test_odds)
    probability = odds_manager.convert_american_to_probability(test_odds)
    print(f"American: {test_odds}, Decimal: {decimal:.3f}, Probability: {probability:.3f}")
