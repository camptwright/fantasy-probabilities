# Fantasy Probability Calculator

A comprehensive fantasy sports analysis tool that analyzes odds from multiple sportsbooks and calculates fantasy performance probabilities using historical data and statistical models.

## Features

- **Multi-Source Odds Integration**: Fetches odds from multiple sportsbook APIs
- **Fantasy Performance Prediction**: Calculates probabilities for game outcomes, point differentials, and total points
- **Player Performance Analysis**: Analyzes individual player performance probabilities
- **Historical Data Collection**: Scrapes team and player statistics from ESPN
- **Machine Learning Models**: Uses trained models for improved accuracy
- **Web Dashboard**: Interactive web interface for viewing opportunities
- **NCAA Sports Focus**: Specialized support for NCAA Football and Basketball

## Project Structure

```
fantasy-probabilities/
├── app.py                          # Flask web application (main entry point for web interface)
├── fantasy_main.py                 # CLI application (main entry point for command-line)
├── main.py                         # Alternative CLI entry point
│
├── Core Modules
│   ├── fantasy_calculator.py       # Database management and data models
│   ├── fantasy_probability_calculator.py  # Probability calculation engine
│   ├── probability_calculator.py   # Additional probability calculations
│   ├── odds_api.py                 # Sportsbook odds API integration
│   ├── espn_scraper.py             # ESPN data scraping
│   ├── espn_player_last_game.py    # Player-specific ESPN data
│   └── models.py                   # Shared data models (dataclasses)
│
├── Examples and Utilities
│   ├── example.py                  # Basic usage examples
│   ├── real_data_integration_example.py  # Real API integration examples
│   ├── player_props_example.py     # Player prop examples
│   ├── ncaa_example.py             # NCAA-specific examples
│   ├── fantasy_calculator_main.py  # Alternative calculator interface
│   └── test.py                     # Unit tests
│
├── Setup and Configuration
│   ├── fantasy_setup.py            # Setup script (recommended)
│   ├── setup.py                     # Alternative setup script
│   ├── config.env.example          # Environment configuration template
│   └── requirements.txt            # Python dependencies
│
├── Web Application
│   └── templates/
│       └── dashboard.html           # Web dashboard template
│
└── Data Files
    ├── fantasy_data.db              # SQLite database (created on first run)
    └── fantasy_calculator.log      # Application logs
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd fantasy-probabilities
   ```

2. **Install dependencies**:
   ```bash
   python fantasy_setup.py
   ```
   
   Or manually:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API keys**:
   - Copy `config.env.example` to `.env`
   - Add your API keys:
     - **REQUIRED**: The Odds API (https://the-odds-api.com/) - Free tier: 500 requests/month
     - **OPTIONAL**: OddsAPI.com (https://oddsapi.com/) - Alternative odds source

## Usage

### Command Line Interface

The main CLI entry point is `fantasy_main.py`:

```bash
# Check status and configuration
python fantasy_main.py status

# Update odds for a specific sport
python fantasy_main.py update-odds --sport nfl

# Collect historical data
python fantasy_main.py collect-data --sport nfl --seasons 2022,2023

# Analyze fantasy opportunities
python fantasy_main.py analyze --sport nfl

# Update player performance odds
python fantasy_main.py update-player-props --sport nfl

# Analyze player performance opportunities
python fantasy_main.py analyze-player-props --sport nfl

# Start continuous monitoring
python fantasy_main.py monitor --interval 30
```

### Web Application

Start the web dashboard:

```bash
python app.py
```

Then open your browser to `http://localhost:5000` to view the interactive dashboard showing top opportunities sorted by expected value.

The web app features:
- Real-time dashboard with filtering by sport and prop type
- Efficient API usage with intelligent caching (5-minute cache for odds, 1-hour for stats)
- Rate limiting to prevent API abuse
- Auto-refresh option for continuous monitoring

### Python API

```python
from fantasy_main import FantasyProbabilityApp
from fantasy_probability_calculator import FantasyProbabilityCalculator, TeamStats, GameContext

# Initialize the app
app = FantasyProbabilityApp()

# Update odds
app.update_odds('nfl')

# Analyze opportunities
opportunities = app.analyze_fantasy_opportunities('nfl')

# Calculate probabilities
prob_calculator = FantasyProbabilityCalculator()
probabilities = prob_calculator.calculate_game_outcome_probability(game_context)
```

## Supported Sports

- **NCAA Football** (ncaaf)
- **NCAA Basketball** (ncaab)
- **NFL** (nfl)
- **NBA** (nba)
- **MLB** (mlb)
- **NHL** (nhl)

## Core Modules

### fantasy_calculator.py
Database management using SQLite. Handles storage and retrieval of:
- Teams, players, games
- Odds and player props
- Historical statistics
- Fantasy recommendations

### fantasy_probability_calculator.py
Main probability calculation engine. Provides:
- Game outcome probabilities
- Point differential probabilities (spreads)
- Total points probabilities (over/under)
- Player performance probabilities

### odds_api.py
Integrates with sportsbook APIs:
- The Odds API (primary)
- OddsAPI.com (optional)
- Handles odds conversion (American, decimal, probability)
- Fetches player props and game odds

### espn_scraper.py & espn_player_last_game.py
ESPN data collection:
- Team statistics and standings
- Player statistics and game logs
- Historical game results
- Real-time game data

### models.py
Shared data models using Python dataclasses:
- Team, Player, Game
- Odds, PlayerProp, PlayerStats
- FantasyRecommendation

## Database Schema

The tool uses SQLite (`fantasy_data.db`) with the following main tables:

- `teams`: Team information and statistics
- `players`: Player information and positions
- `games`: Game schedules and results
- `fantasy_odds`: Fantasy odds from sportsbooks
- `player_performance_props`: Player performance prop bets
- `player_stats`: Historical player statistics
- `historical_data`: Historical game results

## Configuration

Key configuration options in `.env`:

```env
# REQUIRED API Key
THE_ODDS_API_KEY=your_api_key_here

# OPTIONAL API Key
# ODDS_API_KEY=your_api_key_here

# Database
DATABASE_PATH=fantasy_data.db

# Calculator Settings
UPDATE_INTERVAL_MINUTES=30
MAX_FANTASY_VALUE=100
MIN_PROFIT_MARGIN=0.05

# Sports Configuration
SPORTS=['ncaaf', 'ncaab']
```

## Probability Calculations

The calculator provides several types of probability calculations:

1. **Game Outcome Probabilities**: Win/loss probabilities for teams based on historical performance, recent form, and matchup factors
2. **Point Differential Probabilities**: Likelihood of covering point spreads using statistical models
3. **Total Points Probabilities**: Over/under probabilities for game totals based on team offensive/defensive averages
4. **Player Performance Probabilities**: Individual player stat predictions using historical averages, recent form, and matchup context

## API Efficiency

The application implements intelligent caching to minimize API calls:

- **Odds**: Cached for 5 minutes
- **Player Props**: Cached for 5 minutes
- **Statistics**: Cached for 1 hour
- **Analysis Results**: Cached for 10 minutes

This reduces API usage by approximately 90% compared to uncached requests, keeping usage well within free tier limits (500 requests/month for The Odds API).

## Examples

### Basic Usage
```bash
python example.py
```

### Real Data Integration
```bash
python real_data_integration_example.py
```

### Player Props
```bash
python player_props_example.py
```

### NCAA Sports
```bash
python ncaa_example.py
```

## Logging

The tool logs all activities to `fantasy_calculator.log` with detailed information about:
- API calls and responses
- Data collection progress
- Probability calculations
- Error handling

Logs are also output to the console for real-time monitoring.

## File Paths

- **Database**: `fantasy_data.db` (in project root)
- **Logs**: `fantasy_calculator.log` (in project root)
- **Environment Config**: `.env` (in project root, created from `config.env.example`)
- **Web Templates**: `templates/dashboard.html`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational and research purposes only. Always gamble responsibly and within your means. The authors are not responsible for any financial losses incurred through the use of this software.
