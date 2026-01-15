#!/usr/bin/env python3
"""
Web Application for Fantasy Probability Calculator
Displays highest probability player/team props with efficient API usage
"""

import os
import sys
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
import logging
import json
from functools import wraps
import time

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fantasy_calculator import DatabaseManager
from odds_api import OddsManager, TheOddsAPI
from fantasy_probability_calculator import FantasyProbabilityCalculator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize components
db_manager = DatabaseManager()
odds_manager = OddsManager()
prob_calculator = FantasyProbabilityCalculator()

# Cache configuration
CACHE_DURATION = {
    'odds': 300,  # 5 minutes for odds
    'player_props': 300,  # 5 minutes for player props
    'stats': 3600,  # 1 hour for stats
    'analysis': 600  # 10 minutes for analysis
}

# In-memory cache
cache = {}

def get_cache_key(cache_type, sport=None, **kwargs):
    """Generate cache key"""
    key_parts = [cache_type]
    if sport:
        key_parts.append(sport)
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}:{v}")
    return "_".join(key_parts)

def get_cached_data(cache_key):
    """Get data from cache if still valid"""
    if cache_key in cache:
        data, timestamp = cache[cache_key]
        cache_type = cache_key.split('_')[0]
        duration = CACHE_DURATION.get(cache_type, 300)
        
        if datetime.now() - timestamp < timedelta(seconds=duration):
            logger.info(f"Cache hit: {cache_key}")
            return data
        else:
            logger.info(f"Cache expired: {cache_key}")
            del cache[cache_key]
    return None

def set_cached_data(cache_key, data):
    """Store data in cache"""
    cache[cache_key] = (data, datetime.now())
    logger.info(f"Cached: {cache_key}")

def rate_limit(max_calls=10, period=60):
    """Rate limiting decorator"""
    calls = []
    
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            now = time.time()
            # Remove calls outside the period
            calls[:] = [call_time for call_time in calls if now - call_time < period]
            
            if len(calls) >= max_calls:
                return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
            
            calls.append(now)
            return f(*args, **kwargs)
        return wrapper
    return decorator

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/opportunities')
@rate_limit(max_calls=20, period=60)
def get_opportunities():
    """Get top opportunities for all sports"""
    try:
        cache_key = get_cache_key('analysis', 'all')
        cached = get_cached_data(cache_key)
        if cached:
            return jsonify(cached)
        
        opportunities = []
        sports = ['nfl', 'nba', 'mlb', 'nhl', 'ncaaf', 'ncaab']
        
        for sport in sports:
            try:
                sport_opps = get_sport_opportunities(sport)
                opportunities.extend(sport_opps)
            except Exception as e:
                logger.error(f"Error getting opportunities for {sport}: {e}")
                continue
        
        # Sort by expected value
        opportunities.sort(key=lambda x: x.get('expected_value', 0), reverse=True)
        
        # Take top 50
        top_opportunities = opportunities[:50]
        
        result = {
            'opportunities': top_opportunities,
            'count': len(top_opportunities),
            'timestamp': datetime.now().isoformat()
        }
        
        set_cached_data(cache_key, result)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error getting opportunities: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/opportunities/<sport>')
@rate_limit(max_calls=20, period=60)
def get_sport_opportunities_endpoint(sport):
    """Get opportunities for a specific sport"""
    try:
        cache_key = get_cache_key('analysis', sport)
        cached = get_cached_data(cache_key)
        if cached:
            return jsonify(cached)
        
        opportunities = get_sport_opportunities(sport)
        
        result = {
            'sport': sport,
            'opportunities': opportunities,
            'count': len(opportunities),
            'timestamp': datetime.now().isoformat()
        }
        
        set_cached_data(cache_key, result)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error getting opportunities for {sport}: {e}")
        return jsonify({'error': str(e)}), 500

def get_sport_opportunities(sport):
    """Get opportunities for a sport (with caching)"""
    opportunities = []
    
    try:
        # Get player props with caching
        cache_key = get_cache_key('player_props', sport)
        cached_props = get_cached_data(cache_key)
        
        if not cached_props:
            api_key = os.getenv("THE_ODDS_API_KEY")
            if api_key:
                odds_api = TheOddsAPI(api_key)
                player_props = odds_api.get_player_props(sport)
                set_cached_data(cache_key, player_props)
                cached_props = player_props
            else:
                cached_props = []
        
        # Process player props
        for game in cached_props:
            home_team = game.get('home_team', 'Unknown')
            away_team = game.get('away_team', 'Unknown')
            
            for bookmaker in game.get('bookmakers', []):
                bookmaker_name = bookmaker.get('title', 'Unknown')
                
                for market in bookmaker.get('markets', []):
                    market_key = market.get('key', '')
                    
                    for outcome in market.get('outcomes', []):
                        player_name = outcome.get('name', 'Unknown')
                        line = outcome.get('point', 0)
                        odds = outcome.get('price', 0)
                        
                        # Calculate probability from odds
                        if odds != 0:
                            if odds > 0:
                                implied_prob = 100 / (odds + 100)
                            else:
                                implied_prob = abs(odds) / (abs(odds) + 100)
                            
                            # Calculate expected value (simplified)
                            # In real implementation, you'd use the probability calculator
                            expected_value = implied_prob * 0.5  # Simplified calculation
                            
                            opportunities.append({
                                'type': 'player_prop',
                                'sport': sport,
                                'player': player_name,
                                'prop': market_key.replace('player_', '').replace('_', ' ').title(),
                                'line': line,
                                'odds': odds,
                                'implied_probability': round(implied_prob * 100, 2),
                                'expected_value': round(expected_value, 3),
                                'game': f"{away_team} @ {home_team}",
                                'bookmaker': bookmaker_name,
                                'timestamp': datetime.now().isoformat()
                            })
        
        # Get team props (spreads, totals, etc.)
        cache_key = get_cache_key('odds', sport)
        cached_odds = get_cached_data(cache_key)
        
        if not cached_odds:
            all_odds = odds_manager.get_odds_for_sport(sport, markets=["h2h", "spreads", "totals"])
            set_cached_data(cache_key, all_odds)
            cached_odds = all_odds
        
        # Process team props
        for api_name, odds_list in cached_odds.items():
            for game in odds_list:
                home_team = game.get('home_team', 'Unknown')
                away_team = game.get('away_team', 'Unknown')
                
                for bookmaker in game.get('bookmakers', []):
                    bookmaker_name = bookmaker.get('title', 'Unknown')
                    
                    for market in bookmaker.get('markets', []):
                        market_key = market.get('key', '')
                        
                        for outcome in market.get('outcomes', []):
                            selection = outcome.get('name', 'Unknown')
                            point = outcome.get('point', 0)
                            odds = outcome.get('price', 0)
                            
                            if odds != 0:
                                if odds > 0:
                                    implied_prob = 100 / (odds + 100)
                                else:
                                    implied_prob = abs(odds) / (abs(odds) + 100)
                                
                                expected_value = implied_prob * 0.5  # Simplified
                                
                                opportunities.append({
                                    'type': 'team_prop',
                                    'sport': sport,
                                    'selection': selection,
                                    'prop': market_key.upper(),
                                    'line': point,
                                    'odds': odds,
                                    'implied_probability': round(implied_prob * 100, 2),
                                    'expected_value': round(expected_value, 3),
                                    'game': f"{away_team} @ {home_team}",
                                    'bookmaker': bookmaker_name,
                                    'timestamp': datetime.now().isoformat()
                                })
    
    except Exception as e:
        logger.error(f"Error processing opportunities for {sport}: {e}")
    
    return opportunities

@app.route('/api/stats')
@rate_limit(max_calls=10, period=60)
def get_stats():
    """Get API usage statistics"""
    stats = {
        'cache_size': len(cache),
        'cache_keys': list(cache.keys()),
        'cache_durations': CACHE_DURATION,
        'api_key_configured': bool(os.getenv("THE_ODDS_API_KEY")),
        'timestamp': datetime.now().isoformat()
    }
    return jsonify(stats)

@app.route('/api/refresh/<sport>')
@rate_limit(max_calls=5, period=300)  # Limit refresh to 5 per 5 minutes
def refresh_sport(sport):
    """Manually refresh data for a sport"""
    try:
        # Clear cache for this sport
        keys_to_remove = [key for key in cache.keys() if sport in key]
        for key in keys_to_remove:
            del cache[key]
        
        # Force refresh
        opportunities = get_sport_opportunities(sport)
        
        return jsonify({
            'success': True,
            'sport': sport,
            'opportunities_count': len(opportunities),
            'message': f'Refreshed data for {sport}'
        })
    
    except Exception as e:
        logger.error(f"Error refreshing {sport}: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
