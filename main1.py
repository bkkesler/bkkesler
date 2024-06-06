import pandas as pd
from gather_data import fetch_player_game_logs, compile_team_data, get_team_stats, \
    get_active_players, fetch_all_player_game_logs, get_top_90_players, get_roster, get_pitcher_roster, \
    fetch_all_pitcher_game_logs_pybaseball, get_player_season_pa
from handle_edgecases import remove_non_numeric_rows, clean_and_format_date_statcast, modify_innings_pitched, determine_start_inning
from calculate_stats import calculate_hits_per_out, calculate_hits_per_pa, calculate_hits_per_out_statcast
import os
import pickle

pathName = os.getcwd()
playersUsed = 15

# Get top batters for this year
top_90_player_names = get_top_90_players()
print(f"Found {len(top_90_player_names)} top players.")
print(top_90_player_names[:playersUsed])  # Print the first 10 player names as a sample

# Main script
year = 2023

# Batting roster (for IDs)
roster = get_roster(year)
roster_dict = {v: k for k, v in roster.items()}  # Create a bidirectional dictionary
print(f"Found {len(roster)} players in the roster.")
print(list(roster.items())[:playersUsed])  # Print the first 10 entries as a sample

# Remove players from top_90_player_names if they are not in the roster
top_90_player_names = [name for name in top_90_player_names if name in roster]
print(f"Found {len(top_90_player_names)} top players in the roster.")
print(top_90_player_names[:playersUsed])  # Print the first 10 player names as a sample


# Get top batters' game logs and save
filename = 'top_player_game_logs' + str(year) + '.pkl'
top_90_player_ids = [roster[name] for name in top_90_player_names if
                     name in roster]  # Get ids from each of top players
print(top_90_player_ids[:playersUsed])
if not os.path.exists(pathName + "\\" + filename):
    top_90_player_ids = [roster[name] for name in top_90_player_names if
                         name in roster]  # Get ids from each of top players
    print(top_90_player_ids[:playersUsed])
    top_player_game_logs = fetch_all_player_game_logs(top_90_player_ids[:playersUsed], year)
    top_player_game_logs.to_pickle('top_player_game_logs' + str(year) + '.pkl')
    top_player_game_logs.to_csv('top_player_game_logs' + str(year) + '.csv')
else:
    top_player_game_logs = pd.read_pickle(filename)

pitcher_roster = get_pitcher_roster(year)
print(f"Found {len(pitcher_roster)} pitchers in the roster.")
print(list(pitcher_roster.items())[:10])  # Print the first 10 entries as a sample

start_date = f"{year}-04-01"
end_date = f"{year}-10-01"
#Get top batter PA information and save
filename = f'top_batters_pas_{start_date}_to_{end_date}.pkl'

if not os.path.exists(pathName + "\\" + filename):
    # Initialize an empty list to store the dataframes for each player and game
    dataFrames = []
    for player_id in top_90_player_ids:
        player_name = roster_dict[player_id]  # Retrieve the player's name using the bidirectional dictionary
        pa_data, statcast_id = get_player_season_pa(player_name, year)
        pa_data['bbref_id'] = player_id
        dataFrames.append(pd.DataFrame(pa_data))
    top_player_pas = pd.concat(dataFrames, ignore_index=True)
    top_player_pas.to_pickle(filename)
    top_player_pas.to_csv(f'top_batters_pas_{start_date}_to_{end_date}.csv')
else:
    top_player_pas = pd.read_pickle(filename)

# Get pitcher data
filename = f'all_pitchers_game_logs_{start_date}_to_{end_date}.pkl'
if not os.path.exists(pathName + "\\" + filename):
    print('Pitching file does not exist. Creating')
    # Get pitching roster and game logs
    pitcher_roster = get_pitcher_roster(year)
    print(f"Found {len(pitcher_roster)} pitchers in the roster.")
    print(list(pitcher_roster.items())[:10])  # Print the first 10 entries as a sample
    pitcher_data_game_logs = fetch_all_pitcher_game_logs_pybaseball(list(pitcher_roster.values()), year)
    print(pitcher_data_game_logs.head())
    # Save to pickle
    with open(f'all_pitchers_game_logs_{start_date}_to_{end_date}.pkl', 'wb') as f:
        pickle.dump(pitcher_data_game_logs, f)

    # Save to CSV
    pitcher_data_game_logs.to_csv(f'all_pitchers_game_logs_{start_date}_to_{end_date}.csv', index=False)
else:
    print('Loading pitcher game logs')
    pitcher_data_game_logs = pd.read_pickle(filename)


print('Selecting eventful pitches')
# Drop rows with NaN values in events
pitcher_data_game_logs = pitcher_data_game_logs.dropna(subset=['events'])
print('Cleaning pitcher date')
pitcher_data_game_logs = clean_and_format_date_statcast(pitcher_data_game_logs)

# Find the handedness of the starting pitcher for each game
print('Finding starting pitcher handedness')
team_abbr_map = {
    'TB': 'TBR',
    'SD': 'SDP',
    'KC': 'KCR',
    'WSH': 'WSN',
    'AZ': 'ARI',
    'CWS': 'CHW',
    'SF': 'SFG'
}
# Find the handedness of the starting pitcher for each game
starting_pitcher_handedness = pitcher_data_game_logs.groupby(['DateTime', 'Tm'])['p_throws'].first().reset_index()

# Convert team abbreviations in starting_pitcher_handedness
starting_pitcher_handedness['Tm'] = starting_pitcher_handedness['Tm'].map(lambda x: team_abbr_map.get(x, x))


# Merge the starting pitcher handedness with the top_player_game_logs dataframe
top_player_game_logs = pd.merge(top_player_game_logs, starting_pitcher_handedness, left_on=['DateTime', 'Opp'], right_on=['DateTime', 'Tm'], how='left')
top_player_game_logs.info()
print(top_player_game_logs.loc[1:20])

print('Determining inning starts')
pitcher_data_game_logs = determine_start_inning(pitcher_data_game_logs)


# print('\n Printing pitcher data')
# pitcher_data_game_logs.info()

# Put together the matrix for machine learning
# Calculate this for last game, 3 games, last 7 games, and for the season. For starting pitchers, "games" are when they started
# 1. The player's hits per game
# 2. The player's hit per plate appearance against the handedness of the opposing starting pitcher (LHP or RHP)
# 3. The opposing starting pitcher's hits given per out
# 4. The opposing team's bullpen hits given per out

# Initialize an empty list to store the dataframes for each player and game
dataframes = []

for player_id in top_90_player_ids:
    player_game_logs = top_player_game_logs[top_player_game_logs['Player'] == player_id]
    player_name = roster_dict[player_id]  # Retrieve the player's name using the bidirectional dictionary

    for _, game in player_game_logs.iterrows():
        game_date = game['DateTime']
        #print(game_date)
        opposing_team = game['Opp']

        # 1. The player's hits per game
        games_list = [1, 3, 7, 'All']
        hits_per_game_stats = {}
        for games in games_list:
            hit_data = player_game_logs[player_game_logs['DateTime'] < game_date]
            if games == 'All':
                hits_per_game = hit_data['H'].mean()
            else:
                hits_per_game = hit_data.sort_values('DateTime', ascending=False).head(games)['H'].mean()
            hits_per_game_stats[f"{games}_games"] = hits_per_game

        # 2. The player's hit per plate appearance against the handedness of the opposing starting pitcher (LHP or RHP)
        pa_data = top_player_pas[top_player_pas['bbref_id'] == player_id]
        if pa_data is None:
            hits_per_pa_stats = {f"{games}_games_{hand}": None for games in games_list for hand in ['L', 'R']}
        else:
            hits_per_pa_stats = calculate_hits_per_pa(pa_data, game_date, games_list)
            #print(hits_per_pa_stats)
        # 3 &4. The opposing pitching hits given per out
        hits_per_out_stats = calculate_hits_per_out_statcast(pitcher_data_game_logs, opposing_team, game_date, games_list)
        #print(hits_per_game_stats.items())

        # Combine all the stats into a single dataframe for the player and game
        game_stats = {
            'Player': player_id,
            'Date': game_date,
            'Opposing_Team': opposing_team,
            **{f"Hits_Per_Game_{k}": v for k, v in hits_per_game_stats.items()},
            **{f"Hits_Per_PA_{games}_games": hits_per_pa_stats.get(f"{games}_games_{game['p_throws']}", None) for games in games_list},
            # **{f"Hits_Per_PA_{k}": v for k, v in hits_per_pa_stats.items()},
            **hits_per_out_stats,
            'Hits': game['H']
        }
        dataframes.append(pd.DataFrame(game_stats, index=[0]))

# Concatenate all the dataframes into a single dataframe
final_dataframe = pd.concat(dataframes, ignore_index=True)

# Save the final dataframe to a file
final_dataframe.to_csv(f'player_game_stats_{start_date}_to_{end_date}.csv', index=False)
print("Final dataframe saved to 'player_game_stats.csv'")

with open(f'player_game_stats_{start_date}_to_{end_date}.pkl', 'wb') as f:
    pickle.dump(final_dataframe, f)
