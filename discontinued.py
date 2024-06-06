from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

def fetch_plate_appearances(player_id, year, driver_path):
    """
    Fetch plate appearance data for a specific player and year from Baseball-Reference.

    Args:
        player_id (str): The player's Baseball-Reference ID.
        year (int): The season year.
        driver_path (str): The path to the ChromeDriver executable.

    Returns:
        DataFrame: A DataFrame containing the player's plate appearances.
    """
    # Verify if the driver path is correct
    if not os.path.isfile(driver_path):
        raise ValueError(f"The path is not a valid file: {driver_path}")

    # Construct the URL for the player's game logs
    url = f"https://www.baseball-reference.com/players/gl.fcgi?id={player_id}&t=b&year={year}"

    # Setup ChromeDriver options
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run Chrome in headless mode
    options.add_argument('--disable-gpu')  # Disable GPU acceleration
    options.add_argument('--no-sandbox')  # Bypass OS security model

    # Create a ChromeDriver service
    service = Service(driver_path)

    # Initialize the WebDriver
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # Open the URL
        driver.get(url)

        # Wait until the game logs table is loaded
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.ID, 'batting_gamelogs')))

        # Find all td elements with the data-endpoint attribute in the PA column
        pa_elements = driver.find_elements(By.XPATH, "//td[@data-stat='PA' and @data-endpoint]")

        # Print the data-endpoint attributes for debugging
        print("Found elements with data-endpoint attributes:")
        for pa_element in pa_elements:
            print(pa_element.get_attribute("data-endpoint"))

        # Create a list to store all plate appearance data
        all_plate_appearances = []

        for pa_element in pa_elements:
            # Click the element to load individual plate appearances
            driver.execute_script("arguments[0].click();", pa_element)

            # Wait for the plate appearances data to load
            wait.until(EC.presence_of_element_located((By.ID, 'batting_events')))

            # Get the new page source and parse it with BeautifulSoup
            time.sleep(2)  # Give some time for the content to fully load
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # Find the span with the data-label attribute to get the name and date
            span = soup.find('span', {'id': 'batting_events_link'})
            if span and span.has_attr('data-label'):
                data_label = span['data-label']
                print(f"Data label: {data_label}")  # Debugging line to check data label text

                # Split the data label text to extract name and date
                if ', ' in data_label:
                    name, date_str = data_label.split(', ', 1)
                    date = pd.to_datetime(date_str)
                else:
                    print(f"Unexpected data label format: {data_label}")
                    continue

            # Find the plate appearances table by its ID
            pa_table = soup.find('table', {'id': 'batting_events'})

            # Check if the table is found
            if pa_table is not None:
                # Convert the HTML table to a DataFrame
                df = pd.read_html(StringIO(str(pa_table)))[0]

                # Add name and date columns
                df['Name'] = name
                df['Date'] = date

                # Clean up the DataFrame
                df = df[df[df.columns[0]] != df.columns[0]]  # Remove rows that repeat the column fields
                df.reset_index(drop=True, inplace=True)  # Reset the index

                # Add the DataFrame to the list
                all_plate_appearances.append(df)

        # Concatenate all DataFrames into one
        if all_plate_appearances:
            final_df = pd.concat(all_plate_appearances, ignore_index=True)
        else:
            final_df = pd.DataFrame()

        return final_df

    finally:
        # Quit the WebDriver
        driver.quit()

# Example usage
# player_id = 'troutmi01'
# year = 2021
# driver_path = 'D:\\Downloads\\chromedriver-win32\\chromedriver-win32\\chromedriver.exe'  # Ensure this path is correct
# plate_appearances = fetch_plate_appearances(player_id, year, driver_path)
# print(plate_appearances.head(10))
# # Construct the filename
# filename = f'plate_appearances_{player_id}_{year}.csv'
#
# # Save the DataFrame to a CSV file with the constructed filename
# plate_appearances.to_csv(filename, index=False)


def calculate_hits_per_plate_appearance(player_id, df, games_list=None, date=None, pitcher_hand=None, pitcher_id=None):
    """
    Calculate the hits per plate appearance for a given batter and add the results to a DataFrame.

    Parameters:
    player_id (int): The ID of the player (batter).
    df (DataFrame): The dataframe containing game logs.
    games_list (list, optional): The list of number of games to consider (e.g., [1, 7]). 'All' is also a valid input.
    date (str, optional): The date to consider games before. Format: 'YYYY-MM-DD'.
    pitcher_hand (str, optional): The handedness of the pitcher ('R' or 'L').
    pitcher_id (int, optional): The ID of the pitcher for specific matchups.

    Returns:
    dict: Hits per plate appearance for each game count in games_list.
    """
    results = {}

    # Filter by player ID
    player_data = df[df['Player'] == player_id]

    # Filter by date if provided
    if date:
        player_data = player_data[player_data['Date'] < date]

    for games in games_list:
        if games == 'All':
            filtered_data = player_data
        else:
            filtered_data = player_data.tail(games)

        # Filter by pitcher handedness if provided
        if pitcher_hand:
            filtered_data = filtered_data[filtered_data['pitcher_hand'] == pitcher_hand]

        # Filter by specific pitcher ID if provided
        if pitcher_id:
            filtered_data = filtered_data[filtered_data['pitcher_id'] == pitcher_id]

        # Calculate hits and plate appearances
        hits = filtered_data['H'].sum()
        plate_appearances = filtered_data['PA'].sum()

        # Calculate hits per plate appearance
        hits_per_pa = hits / plate_appearances if plate_appearances > 0 else None
        results[games] = hits_per_pa

    return results

def fetch_pitcher_game_logs(pitcher_id, year):
    """
    Fetch game logs for a specific pitcher and year from Baseball-Reference.

    Args:
        pitcher_id (str): The pitcher's Baseball-Reference ID.
        year (int): The season year.

    Returns:
        DataFrame: A DataFrame containing the pitcher's game logs.
    """
    url = f"https://www.baseball-reference.com/players/gl.fcgi?id={pitcher_id}&t=p&year={year}"
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table', {'id': 'pitching_gamelogs'})
    if table is None:
        print(f"No game logs table found for pitcher {pitcher_id} in year {year}")
        return pd.DataFrame()

    try:
        df = pd.read_html(StringIO(str(table)))[0]
        df = df[df[df.columns[0]] != df.columns[0]]
        df.reset_index(drop=True, inplace=True)
        return df
    except Exception as e:
        print(f"Error parsing game logs data for pitcher {pitcher_id} in year {year}: {e}")
        print("Table HTML:")
        print(table)
        return pd.DataFrame()

# Example usage:
# pitcher_id = 'degroja01'  # Example pitcher ID
# year = 2024
# pitcher_game_logs = fetch_pitcher_game_logs(pitcher_id, year)
# print(pitcher_game_logs.head())

def fetch_pitcher_game_logs(pitcher_id, year):
    """
    Fetch game logs for a specific pitcher and year from Baseball-Reference.

    Args:
        pitcher_id (str): The pitcher's Baseball-Reference ID.
        year (int): The season year.

    Returns:
        DataFrame: A DataFrame containing the pitcher's game logs.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    url = f"https://www.baseball-reference.com/players/gl.fcgi?id={pitcher_id}&t=p&year={year}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'html.parser')

    table = soup.find('table', {'id': 'pitching_gamelogs'})
    if table is None:
        print(f"No game logs table found for pitcher {pitcher_id} in year {year}")
        return pd.DataFrame()

    # Find all the rows in the table body
    rows = table.find('tbody').find_all('tr')

    # Extract the column names from the table header
    header_row = table.find('thead').find('tr')
    column_names = [col.get_text(strip=True) for col in header_row.find_all('th')]

    # Extract the data from each row
    data = []
    for row in rows:
        if row.get('class') and 'thead' in row.get('class'):
            continue  # skip header rows within the body
        row_data = [col.get_text(strip=True) for col in row.find_all('td')]
        if row_data:
            data.append(row_data)

    # Create a DataFrame from the extracted data
    df = pd.DataFrame(data, columns=column_names)

    return df

def fetch_all_pitcher_game_logs(pitcher_ids, year):
    """
    Fetch game logs for all pitchers for a given year.

    Args:
        pitcher_ids (list): List of pitcher IDs.
        year (int): The season year.

    Returns:
        DataFrame: A DataFrame containing the game logs for all pitchers.
    """
    all_pitcher_data = []
    for pitcher_id in pitcher_ids:
        try:
            data = fetch_pitcher_game_logs(pitcher_id, year)
            if not data.empty:
                data['Pitcher'] = pitcher_id
                data['Year'] = year
                all_pitcher_data.append(data)
            # Introduce a random delay between 3 to 7 seconds
            time.sleep(random.uniform(3, 7))
        except Exception as e:
            print(f"Error fetching data for pitcher {pitcher_id}: {e}")
            traceback.print_exc()  # Print the full traceback for more detailed information
            # Introduce a random delay between 3 to 7 seconds even on error
            time.sleep(random.uniform(3, 7))

    if all_pitcher_data:
        pitcher_data_df = pd.concat(all_pitcher_data, ignore_index=True)
    else:
        pitcher_data_df = pd.DataFrame()

    return pitcher_data_df

# Example usage:
year = 2023
print("getting pitcher roster")
# Assuming get_pitcher_roster is a function that returns a dictionary with pitcher IDs
pitcher_roster = get_pitcher_roster(year)
print("Getting pitcher game logs")
pitcher_roster = {k: pitcher_roster[k] for k in list(pitcher_roster.keys())[:10]}
pitcher_data_df = fetch_all_pitcher_game_logs(list(pitcher_roster.values()), year)
print(pitcher_data_df.head())

def fetch_pitcher_game_logs(pitcher_id, year):
    """
    Fetch game logs for a specific pitcher and year from Baseball-Reference.

    Args:
        pitcher_id (str): The pitcher's Baseball-Reference ID.
        year (int): The season year.

    Returns:
        DataFrame: A DataFrame containing the pitcher's game logs.
    """
    url = f"https://www.baseball-reference.com/players/gl.fcgi?id={pitcher_id}&t=p&year={year}"
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table', {'id': 'pitching_gamelogs'})
    if table is None:
        print(f"No game logs table found for pitcher {pitcher_id} in year {year}")
        return pd.DataFrame()

    try:
        df = pd.read_html(StringIO(str(table)))[0]
        df = df[df[df.columns[0]] != df.columns[0]]
        df.reset_index(drop=True, inplace=True)
        return df
    except Exception as e:
        print(f"Error parsing game logs data for pitcher {pitcher_id} in year {year}: {e}")
        print("Table HTML:")
        print(table)
        return pd.DataFrame()

# Example usage:
# pitcher_id = 'degroja01'  # Example pitcher ID
# year = 2024
# pitcher_game_logs = fetch_pitcher_game_logs(pitcher_id, year)
# print(pitcher_game_logs.head())

def fetch_all_pitcher_game_logs(pitcher_ids, year):
    """
    Fetch game logs for all pitchers for a given year.

    Args:
        pitcher_ids (list): List of pitcher IDs.
        year (int): The season year.

    Returns:
        DataFrame: A DataFrame containing the game logs for all pitchers.
    """
    all_pitcher_data = []
    for pitcher_id in pitcher_ids:
        try:
            data = fetch_pitcher_game_logs(pitcher_id, year)
            if not data.empty:
                data['Pitcher'] = pitcher_id
                data['Year'] = year
                all_pitcher_data.append(data)
            # Introduce a random delay between 3 to 7 seconds
            time.sleep(random.uniform(3, 7))
        except Exception as e:
            print(f"Error fetching data for pitcher {pitcher_id}: {e}")
            traceback.print_exc()  # Print the full traceback for more detailed information
            # Introduce a random delay between 3 to 7 seconds even on error
            time.sleep(random.uniform(3, 7))

    if all_pitcher_data:
        pitcher_data_df = pd.concat(all_pitcher_data, ignore_index=True)
    else:
        pitcher_data_df = pd.DataFrame()

    return pitcher_data_df

# Example usage:
year = 2023
print("getting pitcher roster")
# Assuming get_pitcher_roster is a function that returns a dictionary with pitcher IDs
pitcher_roster = get_pitcher_roster(year)
print("Getting pitcher game logs")
pitcher_roster = {k: pitcher_roster[k] for k in list(pitcher_roster.keys())[:10]}
pitcher_data_df = fetch_all_pitcher_game_logs(list(pitcher_roster.values()), year)
print(pitcher_data_df.head())
pitcher_data_df.to_csv(f'all_pitchers_game_logs_{year}.csv', index=False)

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
