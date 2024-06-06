import re
import pandas as pd


def clean_and_format_date(dataframe):
    # Remove extra information from the 'Date' column
    dataframe['Date'] = dataframe['Date'].apply(lambda x: re.sub(r'\(.*?\)', '', x))
    dataframe['Date'] = dataframe['Date'].apply(lambda x: x.split('susp')[0].strip())

    # Remove specific instances of (1) and (2) from the 'Date' column
    dataframe['Date'] = dataframe['Date'].apply(lambda x: x.replace('(1)', '').replace('(2)', ''))
    dataframe['Date'] = dataframe['Date'].apply(lambda x: x.split('susp')[0].strip())

    # Create a new 'DateTime' column by combining 'Date' and 'Year'
    dataframe['DateTime'] = dataframe['Date'] + ', ' + dataframe['Year'].astype(str)

    # Define a custom function to parse the date strings
    def parse_date(date_str):
        try:
            return pd.to_datetime(date_str, format='%B-%d-%Y')
        except ValueError:
            try:
                return pd.to_datetime(date_str, format='%b %d, %Y')
            except ValueError:
                return pd.NaT

    # Apply the custom function to the 'DateTime' column
    dataframe['DateTime'] = dataframe['DateTime'].apply(parse_date)

    return dataframe


def clean_and_format_date_statcast(dataframe):
    def parse_date(date_str):
        try:
            return pd.to_datetime(date_str, format='%Y-%m-%d')
        except ValueError:
            try:
                return pd.to_datetime(date_str)
            except ValueError:
                try:
                    return pd.to_datetime(date_str, format='%b %d, %Y')
                except ValueError:
                    return pd.NaT

    dataframe['DateTime'] = dataframe['game_date']
    # Apply the custom function to the 'DateTime' column
    dataframe['DateTime'] = dataframe['DateTime'].apply(parse_date)

    return dataframe


# pitcher_data_game_logs = pd.read_pickle('all_pitchers_game_logs_2023-04-01_to_2023-10-01.pkl')
# pitcher_data_game_logs = pitcher_data_game_logs[:10]
# print(pitcher_data_game_logs['game_date'])
# pitcher_data_game_logs = clean_and_format_date_statcast(pitcher_data_game_logs)
# print(pitcher_data_game_logs['DateTime'])

def remove_non_numeric_rows(df, column):
    """
    Remove rows where a specified column is not numeric.

    Args:
        df (DataFrame): The input DataFrame.
        column (str): The column to check for numeric values.

    Returns:
        DataFrame: The cleaned DataFrame with non-numeric rows removed.
    """
    # Convert column to numeric, forcing non-numeric values to NaN
    df[column] = pd.to_numeric(df[column], errors='coerce')

    # Drop rows with NaN values in the specified column
    df = df.dropna(subset=[column])

    # Convert the column to integer type using .loc
    df.loc[:, column] = df[column].astype(int)

    return df


def modify_innings_pitched(dataframe):
    def convert_ip(ip):
        if pd.isnull(ip):
            return ip
        elif isinstance(ip, str) and '.' in ip:
            whole, fraction = ip.split('.')
            whole = int(whole)
            if fraction == '1':
                return whole + 0.3333
            elif fraction == '2':
                return whole + 0.6667
            else:
                return float(ip)
        else:
            return float(ip)

    dataframe['IP'] = dataframe['IP'].apply(convert_ip)

    return dataframe


def determine_start_inning(dataframe):
    """
     Determine the starting inning for each pitcher on each game date.

     This function adds a new column 'inning_start' to the DataFrame, indicating the
     first inning each pitcher starts for each game date.

     Args:
         dataframe (DataFrame): The input DataFrame containing columns 'Pitcher', 'DateTime', and 'inning'.

     Returns:
         DataFrame: The updated DataFrame with the 'inning_start' column added.
     """
    # Group by 'Pitcher' and 'DateTime', then find the minimum 'inning' for each group
    min_innings = dataframe.groupby(['Pitcher', 'DateTime'])['inning'].min().reset_index()

    # Rename the 'inning' column to 'inning_start' to indicate it is the starting inning
    min_innings.rename(columns={'inning': 'inning_start'}, inplace=True)

    # Merge the min_innings DataFrame back to the original DataFrame to add the 'inning_start' column
    dataframe = dataframe.merge(min_innings, on=['Pitcher', 'DateTime'], how='left')

    return dataframe
