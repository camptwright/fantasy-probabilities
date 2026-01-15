"""
ESPN Data Scraper Module
Scrapes historical data from ESPN for team and player statistics
"""

import requests
import logging
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os

logger = logging.getLogger(__name__)

class ESPNScraper:
    """Scrapes data from ESPN website"""
    
    def __init__(self, headless: bool = True):
        self.base_url = "https://www.espn.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.headless = headless
        self.driver = None
    
    def _init_selenium(self):
        """Initialize Selenium WebDriver"""
        if self.driver is None:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            self.driver = webdriver.Chrome(
                service=webdriver.chrome.service.Service(ChromeDriverManager().install()),
                options=chrome_options
            )
    
    def _close_selenium(self):
        """Close Selenium WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def get_team_stats(self, sport: str, season: str = None) -> List[Dict]:
        """Get team statistics for a specific sport and season"""
        if season is None:
            season = datetime.now().year
        
        sport_urls = {
            "nfl": f"/nfl/standings/_/season/{season}",
            "nba": f"/nba/standings/_/season/{season}",
            "mlb": f"/mlb/standings/_/season/{season}",
            "nhl": f"/nhl/standings/_/season/{season}",
            "ncaaf": f"/college-football/standings/_/season/{season}",
            "ncaab": f"/mens-college-basketball/standings/_/season/{season}"
        }
        
        if sport not in sport_urls:
            logger.error(f"Sport {sport} not supported")
            return []
        
        try:
            url = self.base_url + sport_urls[sport]
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            teams = []
            
            # Find team standings table
            standings_table = soup.find('table', class_='Table')
            if standings_table:
                rows = standings_table.find_all('tr')[1:]  # Skip header
                
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 8:  # Ensure we have enough columns
                        team_name = cells[0].get_text(strip=True)
                        wins = int(cells[1].get_text(strip=True))
                        losses = int(cells[2].get_text(strip=True))
                        
                        teams.append({
                            'team': team_name,
                            'wins': wins,
                            'losses': losses,
                            'win_percentage': wins / (wins + losses) if (wins + losses) > 0 else 0,
                            'sport': sport,
                            'season': season
                        })
            
            logger.info(f"Scraped {len(teams)} teams for {sport} {season}")
            return teams
            
        except Exception as e:
            logger.error(f"Error scraping team stats for {sport}: {e}")
            return []
    
    def get_game_results(self, sport: str, team: str, season: str = None) -> List[Dict]:
        """Get game results for a specific team"""
        if season is None:
            season = datetime.now().year
        
        try:
            # Use Selenium for dynamic content
            self._init_selenium()
            
            # Construct URL for team schedule
            team_slug = team.lower().replace(' ', '-')
            url = f"{self.base_url}/{sport}/team/{team_slug}/schedule"
            
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "Table"))
            )
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            games = []
            
            # Find games table
            games_table = soup.find('table', class_='Table')
            if games_table:
                rows = games_table.find_all('tr')[1:]  # Skip header
                
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 4:
                        try:
                            date = cells[0].get_text(strip=True)
                            opponent = cells[1].get_text(strip=True)
                            result = cells[2].get_text(strip=True)
                            score = cells[3].get_text(strip=True)
                            
                            # Parse result (W/L)
                            won = 'W' in result
                            
                            # Parse score
                            score_parts = score.split('-')
                            if len(score_parts) == 2:
                                team_score = int(score_parts[0])
                                opponent_score = int(score_parts[1])
                            else:
                                team_score = opponent_score = 0
                            
                            games.append({
                                'date': date,
                                'opponent': opponent,
                                'won': won,
                                'team_score': team_score,
                                'opponent_score': opponent_score,
                                'team': team,
                                'sport': sport,
                                'season': season
                            })
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Error parsing game data: {e}")
                            continue
            
            logger.info(f"Scraped {len(games)} games for {team} {season}")
            return games
            
        except Exception as e:
            logger.error(f"Error scraping game results for {team}: {e}")
            return []
        finally:
            self._close_selenium()
    
    def get_player_stats(self, sport: str, season: str = None) -> List[Dict]:
        """Get player statistics for a specific sport and season"""
        if season is None:
            season = datetime.now().year
        
        try:
            self._init_selenium()
            
            # Get different stat categories for each sport
            stat_categories = self._get_stat_categories(sport)
            all_players = {}
            
            for category in stat_categories:
                try:
                    url = f"{self.base_url}/{sport}/stats/player/_/season/{season}/category/{category}"
                    self.driver.get(url)
                    
                    # Wait for stats table to load
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "Table"))
                    )
                    
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    
                    # Find player stats table
                    stats_table = soup.find('table', class_='Table')
                    if stats_table:
                        rows = stats_table.find_all('tr')[1:]  # Skip header
                        
                        for row in rows:
                            cells = row.find_all('td')
                            if len(cells) >= 5:
                                try:
                                    player_name = cells[0].get_text(strip=True)
                                    team = cells[1].get_text(strip=True)
                                    
                                    # Extract stats for this category
                                    category_stats = self._extract_player_stats_by_category(sport, category, cells)
                                    
                                    if player_name not in all_players:
                                        all_players[player_name] = {
                                            'player': player_name,
                                            'team': team,
                                            'sport': sport,
                                            'season': season,
                                            'stats': {}
                                        }
                                    
                                    all_players[player_name]['stats'].update(category_stats)
                                    
                                except Exception as e:
                                    logger.warning(f"Error parsing player data: {e}")
                                    continue
                
                except Exception as e:
                    logger.warning(f"Error scraping category {category}: {e}")
                    continue
            
            # Convert to list and calculate averages
            players = []
            for player_data in all_players.values():
                # Calculate season averages
                season_avg = self._calculate_season_average(player_data['stats'], sport)
                player_data['season_average'] = season_avg
                players.append(player_data)
            
            logger.info(f"Scraped {len(players)} players for {sport} {season}")
            return players
            
        except Exception as e:
            logger.error(f"Error scraping player stats for {sport}: {e}")
            return []
        finally:
            self._close_selenium()
    
    def _get_stat_categories(self, sport: str) -> List[str]:
        """Get stat categories for each sport"""
        categories = {
            "ncaaf": ["passing", "rushing", "receiving", "defensive"],
            "ncaab": ["scoring", "rebounding", "assists", "steals", "blocks"],
            "nfl": ["passing", "rushing", "receiving", "defensive"],
            "nba": ["scoring", "rebounding", "assists", "steals", "blocks"],
            "mlb": ["batting", "pitching"],
            "nhl": ["scoring", "goaltending"]
        }
        return categories.get(sport, ["scoring"])
    
    def _extract_player_stats_by_category(self, sport: str, category: str, cells: List) -> Dict:
        """Extract stats for a specific category"""
        stats = {}
        
        if sport == "ncaaf":
            if category == "passing":
                stats.update({
                    'passing_yards': self._safe_int(cells[2].get_text(strip=True)),
                    'passing_tds': self._safe_int(cells[3].get_text(strip=True)),
                    'passing_attempts': self._safe_int(cells[4].get_text(strip=True)),
                    'completion_pct': self._safe_float(cells[5].get_text(strip=True))
                })
            elif category == "rushing":
                stats.update({
                    'rushing_yards': self._safe_int(cells[2].get_text(strip=True)),
                    'rushing_tds': self._safe_int(cells[3].get_text(strip=True)),
                    'rushing_attempts': self._safe_int(cells[4].get_text(strip=True)),
                    'yards_per_carry': self._safe_float(cells[5].get_text(strip=True))
                })
            elif category == "receiving":
                stats.update({
                    'receiving_yards': self._safe_int(cells[2].get_text(strip=True)),
                    'receiving_tds': self._safe_int(cells[3].get_text(strip=True)),
                    'receptions': self._safe_int(cells[4].get_text(strip=True)),
                    'yards_per_reception': self._safe_float(cells[5].get_text(strip=True))
                })
        
        elif sport == "ncaab":
            if category == "scoring":
                stats.update({
                    'points': self._safe_float(cells[2].get_text(strip=True)),
                    'field_goals_made': self._safe_int(cells[3].get_text(strip=True)),
                    'field_goal_pct': self._safe_float(cells[4].get_text(strip=True)),
                    'three_point_pct': self._safe_float(cells[5].get_text(strip=True))
                })
            elif category == "rebounding":
                stats.update({
                    'rebounds': self._safe_float(cells[2].get_text(strip=True)),
                    'offensive_rebounds': self._safe_int(cells[3].get_text(strip=True)),
                    'defensive_rebounds': self._safe_int(cells[4].get_text(strip=True))
                })
            elif category == "assists":
                stats.update({
                    'assists': self._safe_float(cells[2].get_text(strip=True)),
                    'turnovers': self._safe_int(cells[3].get_text(strip=True)),
                    'assist_to_turnover_ratio': self._safe_float(cells[4].get_text(strip=True))
                })
            elif category == "steals":
                stats.update({
                    'steals': self._safe_float(cells[2].get_text(strip=True)),
                    'blocks': self._safe_float(cells[3].get_text(strip=True))
                })
        
        return stats
    
    def _calculate_season_average(self, stats: Dict, sport: str) -> float:
        """Calculate season average for the primary stat"""
        if sport == "ncaaf":
            # For football, prioritize passing yards, then rushing, then receiving
            if 'passing_yards' in stats and stats['passing_yards'] > 0:
                return stats['passing_yards']
            elif 'rushing_yards' in stats and stats['rushing_yards'] > 0:
                return stats['rushing_yards']
            elif 'receiving_yards' in stats and stats['receiving_yards'] > 0:
                return stats['receiving_yards']
        elif sport == "ncaab":
            # For basketball, use points
            return stats.get('points', 0)
        
        return 0.0
    
    def get_player_game_log(self, sport: str, player_name: str, season: str = None) -> List[Dict]:
        """Get individual game logs for a player"""
        if season is None:
            season = datetime.now().year
        
        try:
            self._init_selenium()
            
            # Construct player URL
            player_slug = player_name.lower().replace(' ', '-')
            url = f"{self.base_url}/{sport}/player/{player_slug}/stats/_/season/{season}"
            
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "Table"))
            )
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            games = []
            
            # Find game log table
            games_table = soup.find('table', class_='Table')
            if games_table:
                rows = games_table.find_all('tr')[1:]  # Skip header
                
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 4:
                        try:
                            date = cells[0].get_text(strip=True)
                            opponent = cells[1].get_text(strip=True)
                            
                            # Extract game stats based on sport
                            game_stats = self._extract_game_stats(sport, cells)
                            
                            games.append({
                                'date': date,
                                'opponent': opponent,
                                'player': player_name,
                                'sport': sport,
                                'season': season,
                                **game_stats
                            })
                        except Exception as e:
                            logger.warning(f"Error parsing game log: {e}")
                            continue
            
            logger.info(f"Scraped {len(games)} games for {player_name}")
            return games
            
        except Exception as e:
            logger.error(f"Error scraping game log for {player_name}: {e}")
            return []
        finally:
            self._close_selenium()
    
    def _extract_game_stats(self, sport: str, cells: List) -> Dict:
        """Extract game stats from game log"""
        stats = {}
        
        if sport == "ncaaf":
            if len(cells) >= 6:
                stats.update({
                    'passing_yards': self._safe_int(cells[2].get_text(strip=True)),
                    'rushing_yards': self._safe_int(cells[3].get_text(strip=True)),
                    'receiving_yards': self._safe_int(cells[4].get_text(strip=True)),
                    'total_tds': self._safe_int(cells[5].get_text(strip=True))
                })
        elif sport == "ncaab":
            if len(cells) >= 8:
                stats.update({
                    'points': self._safe_int(cells[2].get_text(strip=True)),
                    'rebounds': self._safe_int(cells[3].get_text(strip=True)),
                    'assists': self._safe_int(cells[4].get_text(strip=True)),
                    'steals': self._safe_int(cells[5].get_text(strip=True)),
                    'blocks': self._safe_int(cells[6].get_text(strip=True)),
                    'field_goal_pct': self._safe_float(cells[7].get_text(strip=True))
                })
        
        return stats
    
    def _extract_player_stats(self, sport: str, cells: List) -> Dict:
        """Extract relevant stats based on sport"""
        stats = {}
        
        if sport == "nfl":
            # NFL stats: passing yards, rushing yards, receiving yards, etc.
            if len(cells) >= 8:
                stats.update({
                    'passing_yards': self._safe_int(cells[2].get_text(strip=True)),
                    'passing_tds': self._safe_int(cells[3].get_text(strip=True)),
                    'rushing_yards': self._safe_int(cells[4].get_text(strip=True)),
                    'rushing_tds': self._safe_int(cells[5].get_text(strip=True)),
                    'receiving_yards': self._safe_int(cells[6].get_text(strip=True)),
                    'receiving_tds': self._safe_int(cells[7].get_text(strip=True))
                })
        
        elif sport == "nba":
            # NBA stats: points, rebounds, assists, etc.
            if len(cells) >= 8:
                stats.update({
                    'points': self._safe_float(cells[2].get_text(strip=True)),
                    'rebounds': self._safe_float(cells[3].get_text(strip=True)),
                    'assists': self._safe_float(cells[4].get_text(strip=True)),
                    'steals': self._safe_float(cells[5].get_text(strip=True)),
                    'blocks': self._safe_float(cells[6].get_text(strip=True)),
                    'field_goal_pct': self._safe_float(cells[7].get_text(strip=True))
                })
        
        elif sport == "mlb":
            # MLB stats: batting average, home runs, RBIs, etc.
            if len(cells) >= 8:
                stats.update({
                    'batting_avg': self._safe_float(cells[2].get_text(strip=True)),
                    'home_runs': self._safe_int(cells[3].get_text(strip=True)),
                    'rbis': self._safe_int(cells[4].get_text(strip=True)),
                    'runs': self._safe_int(cells[5].get_text(strip=True)),
                    'hits': self._safe_int(cells[6].get_text(strip=True)),
                    'stolen_bases': self._safe_int(cells[7].get_text(strip=True))
                })
        
        elif sport == "nhl":
            # NHL stats: goals, assists, points, etc.
            if len(cells) >= 8:
                stats.update({
                    'goals': self._safe_int(cells[2].get_text(strip=True)),
                    'assists': self._safe_int(cells[3].get_text(strip=True)),
                    'points': self._safe_int(cells[4].get_text(strip=True)),
                    'plus_minus': self._safe_int(cells[5].get_text(strip=True)),
                    'penalty_minutes': self._safe_int(cells[6].get_text(strip=True)),
                    'shots': self._safe_int(cells[7].get_text(strip=True))
                })
        
        elif sport == "ncaaf":
            # NCAA Football stats: passing yards, rushing yards, receiving yards, etc.
            if len(cells) >= 8:
                stats.update({
                    'passing_yards': self._safe_int(cells[2].get_text(strip=True)),
                    'passing_tds': self._safe_int(cells[3].get_text(strip=True)),
                    'rushing_yards': self._safe_int(cells[4].get_text(strip=True)),
                    'rushing_tds': self._safe_int(cells[5].get_text(strip=True)),
                    'receiving_yards': self._safe_int(cells[6].get_text(strip=True)),
                    'receiving_tds': self._safe_int(cells[7].get_text(strip=True))
                })
        
        elif sport == "ncaab":
            # NCAA Basketball stats: points, rebounds, assists, etc.
            if len(cells) >= 8:
                stats.update({
                    'points': self._safe_float(cells[2].get_text(strip=True)),
                    'rebounds': self._safe_float(cells[3].get_text(strip=True)),
                    'assists': self._safe_float(cells[4].get_text(strip=True)),
                    'steals': self._safe_float(cells[5].get_text(strip=True)),
                    'blocks': self._safe_float(cells[6].get_text(strip=True)),
                    'field_goal_pct': self._safe_float(cells[7].get_text(strip=True))
                })
        
        return stats
    
    def _safe_int(self, value: str) -> int:
        """Safely convert string to int"""
        try:
            return int(re.sub(r'[^\d-]', '', value))
        except ValueError:
            return 0
    
    def _safe_float(self, value: str) -> float:
        """Safely convert string to float"""
        try:
            return float(re.sub(r'[^\d.-]', '', value))
        except ValueError:
            return 0.0
    
    def get_injury_reports(self, sport: str) -> List[Dict]:
        """Get injury reports for teams"""
        try:
            url = f"{self.base_url}/{sport}/injuries"
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            injuries = []
            
            # Find injury reports
            injury_sections = soup.find_all('div', class_='injuries')
            
            for section in injury_sections:
                team_name = section.find('h3').get_text(strip=True)
                injury_list = section.find_all('li')
                
                for injury in injury_list:
                    player_name = injury.find('span', class_='name').get_text(strip=True)
                    injury_status = injury.find('span', class_='status').get_text(strip=True)
                    
                    injuries.append({
                        'team': team_name,
                        'player': player_name,
                        'status': injury_status,
                        'sport': sport,
                        'date': datetime.now().strftime('%Y-%m-%d')
                    })
            
            logger.info(f"Scraped {len(injuries)} injury reports for {sport}")
            return injuries
            
        except Exception as e:
            logger.error(f"Error scraping injury reports for {sport}: {e}")
            return []

class HistoricalDataManager:
    """Manages historical data collection and analysis"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.scraper = ESPNScraper()
    
    def collect_team_data(self, sport: str, seasons: List[int] = None):
        """Collect historical team data"""
        if seasons is None:
            current_year = datetime.now().year
            seasons = [current_year - 1, current_year]  # Last 2 seasons
        
        for season in seasons:
            logger.info(f"Collecting team data for {sport} {season}")
            teams = self.scraper.get_team_stats(sport, str(season))
            
            for team_data in teams:
                # Convert to Team object and save to database
                team = Team(
                    id=f"{team_data['team']}_{sport}_{season}",
                    name=team_data['team'],
                    abbreviation=self._get_team_abbreviation(team_data['team']),
                    sport=sport
                )
                self.db_manager.add_team(team)
    
    def collect_game_data(self, sport: str, teams: List[str], season: str = None):
        """Collect historical game data for teams"""
        if season is None:
            season = str(datetime.now().year)
        
        for team in teams:
            logger.info(f"Collecting game data for {team} {sport} {season}")
            games = self.scraper.get_game_results(sport, team, season)
            
            for game_data in games:
                # Save game data to database
                # This would need to be implemented in the database manager
                pass
    
    def _get_team_abbreviation(self, team_name: str) -> str:
        """Get team abbreviation from team name"""
        # NCAA Football abbreviations
        ncaaf_abbreviations = {
            "Alabama Crimson Tide": "ALA",
            "Georgia Bulldogs": "UGA",
            "Ohio State Buckeyes": "OSU",
            "Michigan Wolverines": "MICH",
            "Clemson Tigers": "CLEM",
            "LSU Tigers": "LSU",
            "Oklahoma Sooners": "OU",
            "Texas Longhorns": "TEX",
            "Florida Gators": "UF",
            "Auburn Tigers": "AUB",
            "Notre Dame Fighting Irish": "ND",
            "Penn State Nittany Lions": "PSU",
            "Wisconsin Badgers": "WISC",
            "Iowa Hawkeyes": "IOWA",
            "Michigan State Spartans": "MSU",
            "Oregon Ducks": "ORE",
            "USC Trojans": "USC",
            "Washington Huskies": "UW",
            "Utah Utes": "UTAH",
            "Oklahoma State Cowboys": "OKST",
            "Texas A&M Aggies": "TAMU",
            "Florida State Seminoles": "FSU",
            "Miami Hurricanes": "MIA",
            "Virginia Tech Hokies": "VT",
            "North Carolina Tar Heels": "UNC",
            "Duke Blue Devils": "DUKE",
            "Kentucky Wildcats": "UK",
            "Tennessee Volunteers": "TENN",
            "South Carolina Gamecocks": "SCAR",
            "Mississippi State Bulldogs": "MSST",
            "Ole Miss Rebels": "MISS",
            "Arkansas Razorbacks": "ARK",
            "Missouri Tigers": "MIZ",
            "Vanderbilt Commodores": "VANDY"
        }
        
        # NCAA Basketball abbreviations
        ncaab_abbreviations = {
            "Gonzaga Bulldogs": "GONZ",
            "Baylor Bears": "BAYL",
            "Kansas Jayhawks": "KU",
            "Duke Blue Devils": "DUKE",
            "North Carolina Tar Heels": "UNC",
            "Kentucky Wildcats": "UK",
            "UCLA Bruins": "UCLA",
            "Arizona Wildcats": "ARIZ",
            "Michigan Wolverines": "MICH",
            "Ohio State Buckeyes": "OSU",
            "Purdue Boilermakers": "PUR",
            "Illinois Fighting Illini": "ILL",
            "Wisconsin Badgers": "WISC",
            "Iowa Hawkeyes": "IOWA",
            "Michigan State Spartans": "MSU",
            "Indiana Hoosiers": "IU",
            "Maryland Terrapins": "MD",
            "Rutgers Scarlet Knights": "RUTG",
            "Penn State Nittany Lions": "PSU",
            "Minnesota Golden Gophers": "MINN",
            "Nebraska Cornhuskers": "NEB",
            "Northwestern Wildcats": "NU",
            "Villanova Wildcats": "NOVA",
            "Connecticut Huskies": "UCONN",
            "Creighton Bluejays": "CREI",
            "Seton Hall Pirates": "SHU",
            "Providence Friars": "PROV",
            "St. John's Red Storm": "SJU",
            "Georgetown Hoyas": "GTWN",
            "Marquette Golden Eagles": "MARQ",
            "Butler Bulldogs": "BUT",
            "Xavier Musketeers": "XAV",
            "DePaul Blue Demons": "DPU"
        }
        
        # Combine all abbreviations
        all_abbreviations = {**ncaaf_abbreviations, **ncaab_abbreviations}
        
        return all_abbreviations.get(team_name, team_name[:3].upper())

# Example usage
if __name__ == "__main__":
    scraper = ESPNScraper()
    
    # Test team stats scraping
    nfl_teams = scraper.get_team_stats("nfl", "2023")
    print(f"Scraped {len(nfl_teams)} NFL teams")
    
    # Test game results scraping
    if nfl_teams:
        sample_team = nfl_teams[0]['team']
        games = scraper.get_game_results("nfl", sample_team, "2023")
        print(f"Scraped {len(games)} games for {sample_team}")
