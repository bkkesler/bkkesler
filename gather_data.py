
from io import StringIO
from handle_edgecases import remove_non_numeric_rows, clean_and_format_date_statcast, determine_start_inning
import time
import requests
from bs4 import BeautifulSoup, Comment
import pandas as pd
import pybaseball as pyb
from handle_edgecases import clean_and_format_date, modify_innings_pitched
import re
import traceback
import random
from pybaseball import playerid_lookup, statcast_pitcher
import pickle

def get_top_90_players():
    """
    Scrape the top 90 players based on the percentage of games with a hit from teamrankings.com.

    Returns:
        list: A list of player names.
    """
    url = "https://www.teamrankings.com/mlb/player-stat/percent-of-games-with-a-hit"
    response = requests.get(url)
    response.raise_for_status()  # Raise an error for bad status codes

    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the table containing the player stats
    table = soup.find('table', {'class': 'tr-table datatable scrollable'})

    if table is None:
        return []  # Return an empty list if no table found

    # Extract player names from the table
    player_names = []
    for row in table.find_all('tr')[1:]:  # Skip the header row
        columns = row.find_all('td')
        if columns:
            player_name = columns[1].text.strip()
            player_names.append(player_name)

    return player_names


# Example usage:
# top_90_player_names = get_top_90_players()
# print(f"Found {len(top_90_player_names)} top players.")
# print(top_90_player_names[:10])  # Print the first 10 player names as a sample


def get_roster(year):
    """
    Scrape the roster page from Baseball-Reference for a given year.

    Args:
        year (int): The year for which to scrape the roster.

    Returns:
        dict: A dictionary mapping player names to their Baseball-Reference IDs.
    """
    url = f"https://www.baseball-reference.com/leagues/MLB/{year}-standard-batting.shtml"
    response = requests.get(url)
    response.raise_for_status()  # Raise an error for bad status codes

    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the commented section containing the table
    comment = soup.find(string=lambda text: isinstance(text, Comment) and 'id="players_standard_batting"' in text)
    if not comment:
        return {}  # Return an empty dictionary if no comment found

    # Parse the commented section as HTML
    comment_soup = BeautifulSoup(comment, 'html.parser')

    # Find the table within the commented section
    table = comment_soup.find('table', {'id': 'players_standard_batting'})

    if table is None:
        return {}  # Return an empty dictionary if no table found

    # Extract player names and IDs from the table
    name_to_id = {}
    for row in table.find_all('tr', class_='full_table'):
        columns = row.find_all('td')
        if columns:
            player_link = columns[0].find('a')
            if player_link:
                player_name = player_link.text.strip().replace('\xa0', ' ')
                href = player_link.get('href')
                player_id = href.split('/')[-1].split('.')[0]
                name_to_id[player_name] = player_id

    return name_to_id


# Example usage:
# year = 2024
# roster = get_roster(year)
# print(f"Found {len(roster)} players in the roster.")
# print(list(roster.items())[:10])  # Print the first 10 entries as a sample


def fetch_player_game_logs(player_id, year):
    """
    Fetch game logs for a specific player and year from Baseball-Reference.

    Args:
        player_id (str): The player's Baseball-Reference ID.
        year (int): The season year.

    Returns:
        DataFrame: A DataFrame containing the player's game logs.
    """
    # Construct the URL for the player's game logs
    url = f"https://www.baseball-reference.com/players/gl.fcgi?id={player_id}&t=b&year={year}"

    # Fetch the webpage content
    response = requests.get(url)
    response.raise_for_status()  # Raise an error for bad status codes

    # Parse the HTML content
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the table containing the game logs
    table = soup.find('table', {'id': 'batting_gamelogs'})
    if table is None:
        return pd.DataFrame()  # Return empty DataFrame if no table found

    # Wrap the HTML string in a StringIO object
    df = pd.read_html(StringIO(str(table)))[0]

    # Remove rows that repeat the column fields
    df = df[df[df.columns[0]] != df.columns[0]]

    # Reset the index
    df.reset_index(drop=True, inplace=True)

    return df


def get_player_season_pa(player_name, year):
    # Normalize player name by removing special characters and accents
    # player_name = re.sub(r'[^a-zA-Z\s]', '', player_name)

    parts = player_name.split()
    first_name = parts[0]
    last_name = ' '.join(parts[1:])

    # Split player name into first and last name
    # first_name, last_name = player_name.split()

    # Add spaces after periods in the first name
    first_name = re.sub(r'\.(?!$)', '. ', first_name)

    # Get player ID from player name
    player = pyb.playerid_lookup(last_name, first_name)

    if player.empty:
        print(f"No player found with name: {player_name} trying fuzzy")
        player = pyb.playerid_lookup(last_name, first_name, fuzzy = True)
        print(player)

    if player.empty:
        print(f"No player found with name: {player_name}")
        return None, None

    player_id = player['key_mlbam'].values[0]

    # Define start and end dates for the season
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    # Get statcast data
    data = pyb.statcast_batter(start_date, end_date, player_id)

    # Filter relevant columns
    pa_data = data[['game_date', 'batter', 'pitcher', 'events', 'stand', 'p_throws']]

    # Filter out rows with empty or NaN 'events'
    pa_data = pa_data.dropna(subset=['events'])

    # Fix the SettingWithCopyWarning by using .loc
    pa_data.loc[:, 'hit'] = pa_data['events'].apply(
        lambda x: 1 if x in ['single', 'double', 'triple', 'home_run'] else 0)

    # Save the filtered DataFrame to a CSV file
    filename = f'{player_id}_{year}_plate_appearances.csv'
    #pa_data.to_csv(filename, index=False)

    return pa_data, player

# Example usage
# player_name = "J.T. Realmuto"
# year = 2023
# pa_data, filename = get_player_season_pa(player_name, year)


def fetch_all_player_game_logs(player_ids, year):
    """
    Fetch game logs for all active players for a given year.

    Args:
        player_ids (list): List of player IDs.
        year (int): The season year.

    Returns:
        DataFrame: A DataFrame containing the game logs for all players.
    """
    all_player_data = []
    for player_id in player_ids:
        try:
            data = fetch_player_game_logs(player_id, year)
            data['Player'] = player_id
            data['Year'] = year
            data = remove_non_numeric_rows(data, 'H')
            data = remove_non_numeric_rows(data, 'Rk')
            all_player_data.append(data)
            time.sleep(5)  # Add a delay to avoid overloading the server
        except Exception as e:
            print(f"Error fetching data for player {player_id}: {e}")

    # Combine all player data into a single DataFrame
    if all_player_data:
        player_data_df = pd.concat(all_player_data, ignore_index=True)
    else:
        player_data_df = pd.DataFrame()

    player_data_df = clean_and_format_date(player_data_df)

    return player_data_df

# Example usage:
# year = 2024
# player_data_df = fetch_all_player_game_logs(player_ids, year)
# print(player_data_df.head())


def get_pitcher_roster(year):
    """
    Scrape the pitcher roster page from Baseball-Reference for a given year.

    Args:
        year (int): The year for which to scrape the pitcher roster.

    Returns:
        dict: A dictionary mapping pitcher names to their Baseball-Reference IDs and handedness.
    """
    url = f"https://www.baseball-reference.com/leagues/majors/{year}-standard-pitching.shtml"

    while True:
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an error for bad status codes
            break
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                print("Rate limited. Sleeping for 60 seconds.")
                time.sleep(60)
            else:
                raise e

    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the commented section containing the table
    comment = soup.find(string=lambda text: isinstance(text, Comment) and 'id="players_standard_pitching"' in text)
    if not comment:
        return {}  # Return an empty dictionary if no comment found

    # Parse the commented section as HTML
    comment_soup = BeautifulSoup(comment, 'html.parser')

    # Find the table within the commented section
    table = comment_soup.find('table', {'id': 'players_standard_pitching'})

    if table is None:
        return {}  # Return an empty dictionary if no table found

    # Extract pitcher names, IDs, and handedness from the table
    name_to_info = {}
    for row in table.find_all('tr'):
        if 'class' in row.attrs and ('full_table' in row['class'] or 'partial_table' in row['class']):
            columns = row.find_all('td')
            if columns:
                player_cell = columns[0]
                pitcher_link = player_cell.find('a')
                if pitcher_link:
                    pitcher_name = pitcher_link.text.strip().replace('\xa0', ' ')
                    href = pitcher_link.get('href')
                    pitcher_id = href.split('/')[-1].split('.')[0]
                    handedness = 'L' if player_cell.text.strip().endswith('*') else 'R'

                    if pitcher_name not in name_to_info:
                        name_to_info[pitcher_name] = {'id': pitcher_id, 'hand': handedness}

    return name_to_info



def fetch_pitcher_game_logs_pybaseball(pitcher_mlbam_id, start_date, end_date):
    """
    Fetch game logs for a specific pitcher and date range using pybaseball.

    Args:
        pitcher_mlbam_id (str): The pitcher's MLBAM ID.
        start_date (str): The start date in the format YYYY-MM-DD.
        end_date (str): The end date in the format YYYY-MM-DD.

    Returns:
        DataFrame: A DataFrame containing the pitcher's game logs.
    """
    game_logs = statcast_pitcher(start_date, end_date, pitcher_mlbam_id)
    if game_logs.empty:
        print(f"No game logs found for pitcher {pitcher_mlbam_id} from {start_date} to {end_date}")
        return pd.DataFrame()
    return game_logs


def correct_name_format(pitcher_name):
    """
    Correct the format of the pitcher name for specific cases.

    Args:
        pitcher_name (str): The name of the pitcher.

    Returns:
        tuple: Corrected first name and last name.
    """
    # pitcher_name = "Chase De Jong"
    parts = pitcher_name.split()
    first_name = parts[0]
    last_name = ' '.join(parts[1:])

    # Add spaces after periods in the first name
    first_name = re.sub(r'\.(?!$)', ' ', first_name)

    return first_name, last_name


def fetch_all_pitcher_game_logs_pybaseball(pitcher_roster, start_date, end_date):
    """
    Fetch game logs for all pitchers for a given date range using pybaseball.

    Args:
        pitcher_roster (list): List of pitcher names.
        start_date (str): The start date in the format YYYY-MM-DD.
        end_date (str): The end date in the format YYYY-MM-DD.

    Returns:
        DataFrame: A DataFrame containing the game logs for all pitchers.
    """
    all_pitcher_data = []
    for pitcher_name in pitcher_roster:
        try:
            first_name, last_name = correct_name_format(pitcher_name)
            player_info = playerid_lookup(last=last_name, first=first_name)
            if player_info.empty:
                print(f"No player found with name {pitcher_name}")
                continue
            pitcher_mlbam_id = player_info['key_mlbam'].values[0]
            data = fetch_pitcher_game_logs_pybaseball(pitcher_mlbam_id, start_date, end_date)
            if not data.empty:
                data['Pitcher'] = pitcher_name
                all_pitcher_data.append(data)
            time.sleep(random.uniform(3, 7))
        except Exception as e:
            print(f"Error fetching data for pitcher {pitcher_name}: {e}")
            traceback.print_exc()
            time.sleep(random.uniform(3, 7))

    if all_pitcher_data:
        pitcher_data_df = pd.concat(all_pitcher_data, ignore_index=True)
        # Add team data
        pitcher_data_df['Tm'] = pitcher_data_df.apply(lambda row: row['home_team'] if row['inning_topbot'] == 'Top' else row['away_team'], axis=1)

    else:
        pitcher_data_df = pd.DataFrame()

    return pitcher_data_df


# Example usage:
# start_date = "2023-04-01"
# end_date = "2023-10-01"
# print("Getting pitcher roster")
# pitcher_roster = get_pitcher_roster(2023)  # Ensure this function returns a list of pitcher names
#
# # Test with the first 10 pitchers
# pitcher_roster = list(pitcher_roster.keys())[:2]
#
# print("Getting pitcher game logs using pybaseball")
# pitcher_data_df = fetch_all_pitcher_game_logs_pybaseball(pitcher_roster, start_date, end_date)
# pitcher_data_df = clean_and_format_date_statcast(pitcher_data_df)
# pitcher_data_df = determine_start_inning(pitcher_data_df)
# columns_to_keep = ['DateTime', 'Pitcher', 'events', 'Tm', 'inning', 'inning_start']
# pitcher_data_df = pitcher_data_df[columns_to_keep]
# print(pitcher_data_df.head())
#
# # Save to pickle
# with open(f'all_pitchers_game_logs_{start_date}_to_{end_date}_first2_shortened.pkl', 'wb') as f:
#     pickle.dump(pitcher_data_df, f)
#
# # Save to CSV
# pitcher_data_df.to_csv(f'all_pitchers_game_logs_{start_date}_to_{end_date}_first2_shortened.csv', index=False)




def get_team_stats(team_abbr, year):
    """
    Fetch team stats for a specific team and year from Baseball-Reference.

    Args:
        team_abbr (str): The team's abbreviation.
        year (int): The season year.

    Returns:
        DataFrame: A DataFrame containing the team's stats.
    """
    # Construct the URL for the team's stats
    url = f"https://www.baseball-reference.com/teams/{team_abbr}/{year}.shtml"
    response = requests.get(url)
    response.raise_for_status()  # Raise an error for bad status codes

    # Parse the HTML content
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the table containing the team stats
    table = soup.find('table', id='team_batting')
    if table is None:
        return pd.DataFrame()  # Return empty DataFrame if no table found

    # Wrap the HTML string in a StringIO object
    df = pd.read_html(StringIO(str(table)))[0]

    # Add team abbreviation and season to the DataFrame
    df['team_abbr'] = team_abbr
    df['season'] = year

    return df


def compile_team_data(team_abbrs, year):
    """
    Compile team stats for multiple teams and a specific year.

    Args:
        team_abbrs (list): List of team abbreviations.
        year (int): The season year.

    Returns:
        DataFrame: A DataFrame containing the compiled team stats.
    """
    all_team_data = []
    for team_abbr in team_abbrs:
        # Fetch stats for each team
        team_data = get_team_stats(team_abbr, year)
        all_team_data.append(team_data)

    # Concatenate all team DataFrames
    df = pd.concat(all_team_data, ignore_index=True)
    return df


def get_active_players(year):
    """
    Scrape the list of active players for a given year from Baseball-Reference.

    Args:
        year (int): The year for which to scrape the active players.

    Returns:
        list: A list of player IDs.
    """
    url = f"https://www.baseball-reference.com/leagues/MLB/{year}-roster.shtml"
    response = requests.get(url)
    response.raise_for_status()  # Raise an error for bad status codes

    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the table containing the player roster
    table = soup.find('table', {'id': 'players_standard_batting'})

    if table is None:
        print('No table found')
        return []  # Return an empty list if no table found

    # Extract player IDs from the table
    player_ids = []
    for row in table.find_all('tr'):
        player_link = row.find('a')
        if player_link:
            # Extract the player ID from the href attribute
            href = player_link.get('href')
            player_id = href.split('/')[-1].split('.')[0]
            player_ids.append(player_id)

    return player_ids
# Example usage:
# year = 2024
# player_ids = get_active_players(year)
# print(f"Found {len(player_ids)} active players for {year}.")
# print(player_ids[:10])  # Print the first 10 player IDs as a sample
