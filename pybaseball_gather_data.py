import pybaseball

def get_pitcher_game_logs(season):
    # Retrieve statcast data for the specified season
    statcast_data = pybaseball.statcast(start_dt=f'{season}-01-01', end_dt=f'{season}-12-31')

    # Filter the data for pitchers only
    pitching_data = statcast_data[statcast_data['inning_topbot'] == 'top']

    # Group the data by pitcher, date, and team to get game-by-game stats
    pitcher_game_logs = pitching_data.groupby(['pitcher_name', 'game_date', 'team'])

    # Calculate the desired stats for each game
    pitcher_game_logs = pitcher_game_logs.agg({
        'inning': 'max',
        'events': 'count',
        'strikes': 'sum',
        'balls': 'sum',
        'p_throws': 'first',
        'hit_location': 'count',
        'outs_when_up': 'sum',
        'earned_runs': 'sum'
    })

    # Rename columns to match the desired output
    pitcher_game_logs = pitcher_game_logs.rename(columns={
        'inning': 'IP',
        'events': 'TBF',
        'strikes': 'S',
        'balls': 'B',
        'p_throws': 'Throws',
        'hit_location': 'H',
        'outs_when_up': 'Outs',
        'earned_runs': 'ER'
    })

    # Reset the index to flatten the DataFrame
    pitcher_game_logs = pitcher_game_logs.reset_index()

    # Sort the game logs by date in ascending order
    pitcher_game_logs = pitcher_game_logs.sort_values('game_date')

    return pitcher_game_logs

# Prompt the user to enter the desired season
season = int(input("Enter the season year: "))

# Retrieve the pitcher game logs for the specified season
game_logs = get_pitcher_game_logs(season)

# Display the pitcher game logs
print("Pitcher Game Logs for Season", season)
print(game_logs)