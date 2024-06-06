import pandas as pd


def calculate_hits_per_out_statcast(dataframe, team, game_date, games_list):
    """
    Calculate hits per out for specified periods and pitcher categories using Statcast data.

    Parameters:
    dataframe (DataFrame): The dataframe containing Statcast data.
    team (str): The team to filter by.
    game_date (str): The date of the game to consider logs before. Format: 'YYYY-MM-DD'.
    games_list (list): The list of number of games to consider (e.g., [1, 7]). 'All' is also a valid input.

    Returns:
    dict: Hits per out for each period and pitcher category.
    """
    if team == 'TBR':
        team = 'TB'
    if team == 'SDP':
        team = 'SD'
    if team == 'KCR':
        team = 'KC'
    if team == 'WSN':
        team = 'WSH'
    if team == 'ARI':
        team = 'AZ'
    if team == 'CHW':
        team = 'CWS'
    if team == 'SFG':
        team = 'SF'

    # Convert game_date to datetime for comparison
    game_date = pd.to_datetime(game_date)

    # Filter the DataFrame for the specified team and dates before the given game_date
    team_df = dataframe[(dataframe['Tm'] == team)]
    team_df = team_df[team_df['DateTime'] < game_date]

    # Initialize dictionary to store stats
    stats = {}

    # Define pitcher categories
    categories = ['Starter', 'MiddleReliever', 'EndingPitcher']

    for games in games_list:
        if games == 'All':
            team_period_df = team_df
        else:
            unique_dates = team_df['DateTime'].unique()
            sorted_dates = sorted(unique_dates, reverse=True)
            selected_dates = sorted_dates[:games]
            team_period_df = team_df[team_df['DateTime'].isin(selected_dates)]

        for category in categories:
            if category == 'Starter':
                category_df = team_period_df[team_period_df['inning_start'] <= 3]
            elif category == 'MiddleReliever':
                category_df = team_period_df[(team_period_df['inning_start'] > 3) & (team_period_df['inning_start'] <= 6)]
            else:  # category == 'EndingPitcher'
                category_df = team_period_df[team_period_df['inning_start'] > 6]

            events_counts = category_df['events'].value_counts()
            hits = sum(events_counts.get(hit_type, 0) for hit_type in ['single', 'double', 'triple', 'home_run'])

            # Total events
            total_instances = category_df['Pitcher'].notna().sum()

            outs = total_instances - hits

            if outs > 0:
                hits_per_out = hits / outs
                stats[f"{games}_{category}"] = hits_per_out
            else:
                stats[f"{games}_{category}"] = None

    return stats


def calculate_hits_per_out(dataframe, team, game_date, games_list):
    """
    Calculate hits per out for specified periods and pitcher categories.

    Parameters:
    dataframe (DataFrame): The dataframe containing game logs.
    team (str): The team to filter by.
    game_date (str): The date of the game to consider logs before. Format: 'YYYY-MM-DD'.
    games_list (list): The list of number of games to consider (e.g., [1, 7]). 'All' is also a valid input.

    Returns:
    dict: Hits per out for each period and pitcher category.
    """
    # Convert game_date to datetime for comparison
    game_date = pd.to_datetime(game_date)

    # Filter the DataFrame for the specified team and year
    team_df = dataframe[(dataframe['Tm'] == team) & (dataframe['DateTime'] < game_date) & (dataframe['Year'] == game_date.year)]

    # Initialize dictionary to store stats
    stats = {}

    # Define pitcher categories
    categories = ['Starter', 'MiddleReliever', 'EndingPitcher']

    for games in games_list:
        if games == 'All':
            team_period_df = team_df
        else:
            team_period_df = team_df.sort_values('DateTime', ascending=False).head(games)

        # Get the starting pitcher for the given game date
        starting_pitcher_id = team_period_df[team_period_df['Entered'].astype(int) == 1]['Pitcher'].values[0]

        # Filter the DataFrame for the starting pitcher
        pitcher_period_df = dataframe[(dataframe['Pitcher'] == starting_pitcher_id) & (dataframe['DateTime'] < game_date) & (dataframe['Year'] == game_date.year)]

        if games == 'All':
            pitcher_period_df = pitcher_period_df
        else:
            pitcher_period_df = pitcher_period_df.sort_values('DateTime', ascending=False).head(games)

        for category in categories:
            if category == 'Starter':
                category_df = pitcher_period_df
            elif category == 'MiddleReliever':
                category_df = team_period_df[team_period_df['Entered'].str.extract(r'(\d+)', expand=False).astype(int).between(2, 7)]
            else:  # category == 'EndingPitcher'
                category_df = team_period_df[team_period_df['Entered'].str.extract(r'(\d+)', expand=False).astype(int) >= 8]

            innings_pitched = category_df['IP'].sum()
            hits_allowed = category_df['H'].sum()

            if innings_pitched > 0:
                hits_per_out = (hits_allowed / innings_pitched) * 1/3
                stats[f"{games}_{category}"] = hits_per_out
            else:
                stats[f"{games}_{category}"] = None

    return stats


def calculate_hits_per_pa(pa_data, game_date, games_list):
    """
    Calculate hits per plate appearance for specified periods and pitcher handedness.

    Parameters:
    pa_data (DataFrame): The DataFrame containing plate appearance data.
    game_date (str): The date of the game to consider logs before. Format: 'YYYY-MM-DD'.
    games_list (list): The list of number of games to consider (e.g., [1, 7]). 'All' is also a valid input.

    Returns:
    dict: Hits per plate appearance for each period and pitcher handedness.
    """
    # Convert game_date to datetime for comparison
    pa_data.loc[:, 'game_date'] = pd.to_datetime(pa_data['game_date'])
    game_date = pd.to_datetime(game_date)

    # Filter data up to the specified game_date
    pa_data = pa_data[pa_data['game_date'] < game_date]

    stats = {}
    handedness = ['L', 'R']

    for games in games_list:
        if games == 'All':
            relevant_data = pa_data
        else:
            games = int(games)
            # Get unique game dates and take the last 'games' dates
            unique_games = pa_data['game_date'].unique()
            # print(f'Unique games: {unique_games}')
            if len(unique_games) < games:
                for hand in handedness:
                    stats[f"{games}_games_{hand}"] = None
                    continue
                # games = len(unique_games)
            last_games = unique_games[:games]
            relevant_data = pa_data[pa_data['game_date'].isin(last_games)]
            # print(f'Relevant Data for {str(games)}')
            # print(relevant_data)

        for hand in handedness:
            hand_data = relevant_data[relevant_data['p_throws'] == hand]
            if not hand_data.empty:
                hits_per_pa = hand_data['hit'].mean()
                stats[f"{games}_games_{hand}"] = hits_per_pa
            else:
                stats[f"{games}_games_{hand}"] = None

    return stats


# Example usage
# from gather_data import get_player_season_pa
#
# player_name = "Mike Trout"
# year = 2023
# pa_data, filename = get_player_season_pa(player_name, year)
#
# game_date = "2021-08-01"
# games_list = [1,7,10, 'All']  # Calculate for the last 10 games and all games before the date
#
# hits_per_pa_stats = calculate_hits_per_pa(pa_data, game_date, games_list)
#
# print(hits_per_pa_stats)



