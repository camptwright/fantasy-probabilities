#!/usr/bin/env python3
"""
Real Data Integration Example
Demonstrates how to fetch real sportsbook odds, player props, and ESPN statistics
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from odds_api import OddsManager, TheOddsAPI
from espn_scraper import ESPNScraper
from fantasy_calculator import DatabaseManager
from fantasy_probability_calculator import FantasyProbabilityCalculator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_api_keys():
    """Check if required API keys are configured"""
    required_key = "THE_ODDS_API_KEY"
    api_key = os.getenv(required_key)
    
    if not api_key or api_key == "your_the_odds_api_key_here":
        print(f"ERROR: {required_key} not configured!")
        print("Please:")
        print("1. Sign up at https://the-odds-api.com/")
        print("2. Get your API key")
        print("3. Add it to your .env file: THE_ODDS_API_KEY=your_key_here")
        return False
    
    print(f"{required_key} configured")
    return True


def example_fetch_game_odds():
    """Example: Fetch real game odds from sportsbooks"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Fetching Real Game Odds")
    print("="*60)
    
    if not check_api_keys():
        return
    
    odds_manager = OddsManager()
    
    # Get odds for NFL
    print("\nFetching NFL odds...")
    nfl_odds = odds_manager.get_odds_for_sport("nfl", markets=["h2h", "spreads", "totals"])
    
    if not nfl_odds:
        print("WARNING: No odds data received. Check your API key and credits.")
        return
    
    # Display results
    for api_name, odds_list in nfl_odds.items():
        print(f"\n{api_name.upper()}: {len(odds_list)} games found")
        
        # Show first 3 games
        for game in odds_list[:3]:
            home_team = game.get('home_team', 'Unknown')
            away_team = game.get('away_team', 'Unknown')
            commence_time = game.get('commence_time', 'Unknown')
            
            print(f"\n  {away_team} @ {home_team}")
            print(f"     Start: {commence_time}")
            
            # Show odds from first 2 bookmakers
            bookmakers = game.get('bookmakers', [])[:2]
            for bookmaker in bookmakers:
                bookmaker_name = bookmaker.get('title', 'Unknown')
                print(f"\n     {bookmaker_name}:")
                
                markets = bookmaker.get('markets', [])
                for market in markets:
                    market_key = market.get('key', 'unknown')
                    outcomes = market.get('outcomes', [])
                    
                    if market_key == 'h2h':
                        print(f"       Moneyline:")
                        for outcome in outcomes:
                            team = outcome.get('name', 'Unknown')
                            odds = outcome.get('price', 0)
                            print(f"         {team}: {odds:+d}")
                    
                    elif market_key == 'spreads':
                        print(f"       Spread:")
                        for outcome in outcomes:
                            team = outcome.get('name', 'Unknown')
                            point = outcome.get('point', 0)
                            odds = outcome.get('price', 0)
                            print(f"         {team} {point:+.1f}: {odds:+d}")
                    
                    elif market_key == 'totals':
                        print(f"       Total:")
                        for outcome in outcomes:
                            name = outcome.get('name', 'Unknown')
                            point = outcome.get('point', 0)
                            odds = outcome.get('price', 0)
                            print(f"         {name} {point:.1f}: {odds:+d}")


def example_fetch_player_props():
    """Example: Fetch real player props from sportsbooks"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Fetching Real Player Props")
    print("="*60)
    
    if not check_api_keys():
        return
    
    api_key = os.getenv("THE_ODDS_API_KEY")
    odds_api = TheOddsAPI(api_key)
    
    # Player prop markets for NFL
    player_markets = [
        "player_pass_yds",
        "player_pass_tds",
        "player_rush_yds",
        "player_receptions",
        "player_receiving_yds"
    ]
    
    print("\nFetching NFL player props...")
    print(f"   Markets: {', '.join(player_markets)}")
    
    try:
        player_props = odds_api.get_odds(
            sport="americanfootball_nfl",
            markets=player_markets,
            regions=["us"]
        )
        
        if not player_props:
            print("WARNING: No player props data received.")
            print("   This might be because:")
            print("   - No games scheduled right now")
            print("   - Player props not available for current games")
            print("   - API credits exhausted")
            return
        
        print(f"\nFound {len(player_props)} games with player props")
        
        # Show props for first game
        if player_props:
            game = player_props[0]
            home_team = game.get('home_team', 'Unknown')
            away_team = game.get('away_team', 'Unknown')
            
            print(f"\n  {away_team} @ {home_team}")
            
            # Collect all props by player
            player_props_dict = {}
            
            for bookmaker in game.get('bookmakers', []):
                bookmaker_name = bookmaker.get('title', 'Unknown')
                
                for market in bookmaker.get('markets', []):
                    market_key = market.get('key', 'unknown')
                    
                    for outcome in market.get('outcomes', []):
                        player_name = outcome.get('name', 'Unknown')
                        point = outcome.get('point', 0)
                        odds = outcome.get('price', 0)
                        
                        if player_name not in player_props_dict:
                            player_props_dict[player_name] = []
                        
                        player_props_dict[player_name].append({
                            'market': market_key,
                            'line': point,
                            'odds': odds,
                            'bookmaker': bookmaker_name
                        })
            
            # Display props by player
            for player_name, props in list(player_props_dict.items())[:5]:  # First 5 players
                print(f"\n  {player_name}:")
                for prop in props[:3]:  # First 3 props per player
                    market = prop['market'].replace('player_', '').replace('_', ' ').title()
                    line = prop['line']
                    odds = prop['odds']
                    bookmaker = prop['bookmaker']
                    print(f"     {market}: {line} @ {odds:+d} ({bookmaker})")
    
    except Exception as e:
        logger.error(f"Error fetching player props: {e}")
        print(f"ERROR: {e}")


def example_fetch_espn_stats():
    """Example: Fetch player and team statistics from ESPN"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Fetching ESPN Statistics")
    print("="*60)
    
    scraper = ESPNScraper(headless=True)
    
    # Get team stats
    print("\nFetching NFL team statistics...")
    try:
        nfl_teams = scraper.get_team_stats("nfl", "2024")
        
        if nfl_teams:
            print(f"\nFound {len(nfl_teams)} NFL teams")
            print("\n  Top 5 teams by win percentage:")
            
            sorted_teams = sorted(
                nfl_teams, 
                key=lambda x: x.get('win_percentage', 0), 
                reverse=True
            )
            
            for i, team in enumerate(sorted_teams[:5], 1):
                name = team.get('team', 'Unknown')
                wins = team.get('wins', 0)
                losses = team.get('losses', 0)
                win_pct = team.get('win_percentage', 0)
                print(f"     {i}. {name}: {wins}-{losses} ({win_pct:.3f})")
        else:
            print("WARNING: No team data retrieved")
    
    except Exception as e:
        logger.error(f"Error fetching team stats: {e}")
        print(f"ERROR: {e}")
    
    # Note: For individual player stats, use espn_player_last_game module
    print("\nTip: Use espn_player_last_game module for individual player stats")
    print("   Example:")
    print("   from espn_player_last_game import find_latest_team_game_event, fetch_game_summary, find_player_stats_in_summary")


def example_complete_workflow():
    """Example: Complete workflow combining odds, props, and stats"""
    print("\n" + "="*60)
    print("EXAMPLE 4: Complete Workflow")
    print("="*60)
    
    if not check_api_keys():
        return
    
    print("\nThis example shows the complete workflow:")
    print("   1. Fetch player props from sportsbooks")
    print("   2. Get player statistics from ESPN")
    print("   3. Calculate probabilities")
    print("   4. Identify value bets")
    
    # Initialize components
    db_manager = DatabaseManager()
    odds_manager = OddsManager()
    calculator = FantasyProbabilityCalculator(db_manager)
    
    # Step 1: Get player props
    print("\nStep 1: Fetching player props...")
    api_key = os.getenv("THE_ODDS_API_KEY")
    odds_api = TheOddsAPI(api_key)
    
    try:
        player_props = odds_api.get_odds(
            sport="americanfootball_nfl",
            markets=["player_pass_yds"],
            regions=["us"]
        )
        
        if player_props:
            print(f"   Found {len(player_props)} games with player props")
            
            # Step 2: For each prop, we would:
            # - Get player stats from ESPN
            # - Calculate probability
            # - Compare to implied probability from odds
            # - Identify value
            
            print("\nStep 2-4: Analysis would happen here")
            print("   - Fetch player stats from ESPN")
            print("   - Calculate expected value")
            print("   - Compare to sportsbook odds")
            print("   - Flag value opportunities")
            
            print("\nSee fantasy_calculator_main.py for complete implementation")
        else:
            print("   WARNING: No player props available right now")
    
    except Exception as e:
        logger.error(f"Error in workflow: {e}")


def main():
    """Run all examples"""
    print("="*60)
    print("REAL DATA INTEGRATION EXAMPLES")
    print("="*60)
    print("\nThis script demonstrates how to:")
    print("  • Fetch real sportsbook odds")
    print("  • Get player props from sportsbooks")
    print("  • Retrieve statistics from ESPN")
    print("  • Combine all data for analysis")
    
    # Run examples
    try:
        example_fetch_game_odds()
        example_fetch_player_props()
        example_fetch_espn_stats()
        example_complete_workflow()
        
        print("\n" + "="*60)
        print("Examples completed!")
        print("="*60)
        print("\nNext steps:")
        print("  1. Set up your API keys in .env file")
        print("  2. Run: python fantasy_main.py update-odds --sport nfl")
        print("  3. Run: python fantasy_main.py update-player-props --sport nfl")
        print("  4. Run: python fantasy_main.py analyze --sport nfl")
        print("\n📖 See INTEGRATION_GUIDE.md for detailed documentation")
    
    except KeyboardInterrupt:
        print("\n\nWARNING: Interrupted by user")
    except Exception as e:
        logger.error(f"Error running examples: {e}")
        print(f"\nERROR: {e}")


if __name__ == "__main__":
    main()
