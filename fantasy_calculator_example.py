"""
Example usage of the Fantasy Sports Probability Calculator
Demonstrates Team and Player props for all supported sports
"""

from fantasy_probability_calculator import (
    FantasyProbabilityCalculator,
    TeamStats,
    GameContext
)
from fantasy_calculator_main import FantasyCalculatorApp


def example_nfl_team_props():
    """Example: NFL Team Props"""
    print("=" * 70)
    print("EXAMPLE 1: NFL Team Props - Dallas Cowboys vs Philadelphia Eagles")
    print("=" * 70)
    
    app = FantasyCalculatorApp()
    
    # Create team stats
    home_stats = {
        "team_id": "DAL",
        "wins": 10,
        "losses": 3,
        "win_percentage": 0.769,
        "home_record": [6, 1],
        "away_record": [4, 2],
        "recent_form": [True, True, False, True, True],
        "avg_points_for": 28.5,
        "avg_points_against": 20.2,
    }
    
    away_stats = {
        "team_id": "PHI",
        "wins": 9,
        "losses": 4,
        "win_percentage": 0.692,
        "home_record": [5, 2],
        "away_record": [4, 2],
        "recent_form": [True, False, True, True, False],
        "avg_points_for": 26.8,
        "avg_points_against": 22.1,
    }
    
    results = app.calculate_team_props(
        sport="nfl",
        home_team="Dallas Cowboys",
        away_team="Philadelphia Eagles",
        home_stats=home_stats,
        away_stats=away_stats,
        spread=-3.5,  # Cowboys favored by 3.5
        total=48.5
    )
    
    app.print_team_props(results)


def example_nfl_player_props():
    """Example: NFL Player Props"""
    print("=" * 70)
    print("EXAMPLE 2: NFL Player Props - Dak Prescott Passing Yards")
    print("=" * 70)
    
    app = FantasyCalculatorApp()
    
    results = app.calculate_player_props(
        sport="nfl",
        team="DAL",
        player_name="Dak Prescott",
        prop_types=["passing_yards", "passing_tds", "rushing_yards"],
        lines={
            "passing_yards": 275.5,
            "passing_tds": 2.5,
            "rushing_yards": 15.5
        }
    )
    
    app.print_player_props("Dak Prescott", results)


def example_nba_player_props():
    """Example: NBA Player Props"""
    print("=" * 70)
    print("EXAMPLE 3: NBA Player Props - Luka Doncic")
    print("=" * 70)
    
    app = FantasyCalculatorApp()
    
    results = app.calculate_player_props(
        sport="nba",
        team="DAL",
        player_name="Luka Doncic",
        prop_types=["points", "rebounds", "assists", "three_pointers"],
        lines={
            "points": 32.5,
            "rebounds": 9.5,
            "assists": 9.5,
            "three_pointers": 3.5
        }
    )
    
    app.print_player_props("Luka Doncic", results)


def example_nba_team_props():
    """Example: NBA Team Props"""
    print("=" * 70)
    print("EXAMPLE 4: NBA Team Props - Lakers vs Warriors")
    print("=" * 70)
    
    app = FantasyCalculatorApp()
    
    home_stats = {
        "team_id": "LAL",
        "wins": 25,
        "losses": 20,
        "win_percentage": 0.556,
        "home_record": [15, 8],
        "away_record": [10, 12],
        "recent_form": [True, False, True, True, False],
        "avg_points_for": 115.2,
        "avg_points_against": 112.8,
    }
    
    away_stats = {
        "team_id": "GSW",
        "wins": 22,
        "losses": 23,
        "win_percentage": 0.489,
        "home_record": [14, 10],
        "away_record": [8, 13],
        "recent_form": [False, True, False, True, True],
        "avg_points_for": 118.5,
        "avg_points_against": 116.2,
    }
    
    results = app.calculate_team_props(
        sport="nba",
        home_team="Los Angeles Lakers",
        away_team="Golden State Warriors",
        home_stats=home_stats,
        away_stats=away_stats,
        spread=-2.5,
        total=230.5
    )
    
    app.print_team_props(results)


def example_nhl_player_props():
    """Example: NHL Player Props"""
    print("=" * 70)
    print("EXAMPLE 5: NHL Player Props - Connor McDavid")
    print("=" * 70)
    
    app = FantasyCalculatorApp()
    
    results = app.calculate_player_props(
        sport="nhl",
        team="EDM",
        player_name="Connor McDavid",
        prop_types=["points", "goals", "assists", "shots"],
        lines={
            "points": 1.5,
            "goals": 0.5,
            "assists": 0.5,
            "shots": 4.5
        }
    )
    
    app.print_player_props("Connor McDavid", results)


def example_mlb_player_props():
    """Example: MLB Player Props"""
    print("=" * 70)
    print("EXAMPLE 6: MLB Player Props - Mike Trout")
    print("=" * 70)
    
    app = FantasyCalculatorApp()
    
    results = app.calculate_player_props(
        sport="mlb",
        team="LAA",
        player_name="Mike Trout",
        prop_types=["hits", "home_runs", "runs", "runs_batted_in"],
        lines={
            "hits": 1.5,
            "home_runs": 0.5,
            "runs": 1.5,
            "runs_batted_in": 1.5
        }
    )
    
    app.print_player_props("Mike Trout", results)


def example_ncaaf_team_props():
    """Example: NCAAF Team Props"""
    print("=" * 70)
    print("EXAMPLE 7: NCAAF Team Props - Alabama vs Georgia")
    print("=" * 70)
    
    app = FantasyCalculatorApp()
    
    home_stats = {
        "team_id": "ALA",
        "wins": 11,
        "losses": 1,
        "win_percentage": 0.917,
        "home_record": [6, 0],
        "away_record": [5, 1],
        "recent_form": [True, True, True, True, True],
        "avg_points_for": 35.2,
        "avg_points_against": 18.5,
    }
    
    away_stats = {
        "team_id": "UGA",
        "wins": 12,
        "losses": 0,
        "win_percentage": 1.000,
        "home_record": [7, 0],
        "away_record": [5, 0],
        "recent_form": [True, True, True, True, True],
        "avg_points_for": 38.1,
        "avg_points_against": 16.2,
    }
    
    results = app.calculate_team_props(
        sport="ncaaf",
        home_team="Alabama",
        away_team="Georgia",
        home_stats=home_stats,
        away_stats=away_stats,
        spread=3.5,  # Georgia favored
        total=52.5
    )
    
    app.print_team_props(results)


def example_ncaam_player_props():
    """Example: NCAAM Player Props"""
    print("=" * 70)
    print("EXAMPLE 8: NCAAM Player Props - Caitlin Clark")
    print("=" * 70)
    
    app = FantasyCalculatorApp()
    
    results = app.calculate_player_props(
        sport="ncaam",
        team="IOWA",
        player_name="Caitlin Clark",
        prop_types=["points", "rebounds", "assists", "three_pointers"],
        lines={
            "points": 28.5,
            "rebounds": 7.5,
            "assists": 8.5,
            "three_pointers": 4.5
        }
    )
    
    app.print_player_props("Caitlin Clark", results)


def example_value_analysis():
    """Example: Value Analysis"""
    print("=" * 70)
    print("EXAMPLE 9: Value Analysis - Comparing Calculated vs Implied Probability")
    print("=" * 70)
    
    app = FantasyCalculatorApp()
    
    # Example: Player prop with odds
    calculated_prob = 0.65  # 65% chance of going over
    odds = -110  # American odds
    
    analysis = app.analyze_prop_value(calculated_prob, odds)
    
    print(f"\nCalculated Probability: {analysis['calculated_probability']:.1%}")
    print(f"Implied Probability: {analysis['implied_probability']:.1%}")
    print(f"Expected Value: {analysis['expected_value']:.3f}")
    print(f"Value Percentage: {analysis['value_percentage']:.1f}%")
    print(f"Recommendation: {analysis['recommendation']}")
    print("\n" + "=" * 70 + "\n")


def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("FANTASY SPORTS PROBABILITY CALCULATOR - EXAMPLES")
    print("=" * 70 + "\n")
    
    examples = [
        ("NFL Team Props", example_nfl_team_props),
        ("NFL Player Props", example_nfl_player_props),
        ("NBA Team Props", example_nba_team_props),
        ("NBA Player Props", example_nba_player_props),
        ("NHL Player Props", example_nhl_player_props),
        ("MLB Player Props", example_mlb_player_props),
        ("NCAAF Team Props", example_ncaaf_team_props),
        ("NCAAM Player Props", example_ncaam_player_props),
        ("Value Analysis", example_value_analysis),
    ]
    
    for name, example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\nError running {name}: {e}\n")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
