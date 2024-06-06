import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_squared_error, r2_score
from scipy.stats import spearmanr

year = 2023
start_date = f"{year}-04-01"
end_date = f"{year}-10-01"
final_dataframe = pd.read_pickle(f'player_game_stats_{start_date}_to_{end_date}.pkl')

# Assuming your DataFrame is named 'final_dataframe'
# Select the relevant features and target variable
features = [
    'Hits_Per_Game_1_games', 'Hits_Per_Game_3_games', 'Hits_Per_Game_7_games', 'Hits_Per_Game_All_games',
    'Hits_Per_PA_1_games', 'Hits_Per_PA_3_games', 'Hits_Per_PA_7_games', 'Hits_Per_PA_All_games',
    '1_Starter', '1_MiddleReliever', '1_EndingPitcher',
    '3_Starter', '3_MiddleReliever', '3_EndingPitcher',
    '7_Starter', '7_MiddleReliever', '7_EndingPitcher',
    'All_Starter', 'All_MiddleReliever', 'All_EndingPitcher'
]
target = 'Hits'

X = final_dataframe[features]
y = final_dataframe[target]

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Create and train the Random Forest Regressor with the best parameters
rf_regressor = RandomForestRegressor(max_depth=10, min_samples_leaf=4, min_samples_split=2, n_estimators=200, random_state=42)
rf_regressor.fit(X_train, y_train)

# Make predictions on the test set
y_pred = rf_regressor.predict(X_test)

# Print the predictions and actual values side by side
print("Predictions\tActual")
for pred, actual in zip(y_pred, y_test):
    print(f"{pred:.2f}\t\t{actual}")

# Evaluate the model
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)
spearman_corr, _ = spearmanr(y_pred, y_test)
print(f"\nMean Squared Error: {mse:.4f}")
print(f"R-squared: {r2:.4f}")
print(f"Spearman Correlation: {spearman_corr:.4f}")

# Make predictions on new data
new_data = pd.DataFrame({
    'Hits_Per_Game_1_games': [1.5],
    'Hits_Per_Game_3_games': [1.2],
    'Hits_Per_Game_7_games': [1.0],
    'Hits_Per_Game_All_games': [1.1],
    'Hits_Per_PA_1_games': [0.3],
    'Hits_Per_PA_3_games': [0.25],
    'Hits_Per_PA_7_games': [0.2],
    'Hits_Per_PA_All_games': [0.22],
    '1_Starter': [0.8],
    '1_MiddleReliever': [0.6],
    '1_EndingPitcher': [0.5],
    '3_Starter': [0.75],
    '3_MiddleReliever': [0.55],
    '3_EndingPitcher': [0.45],
    '7_Starter': [0.7],
    '7_MiddleReliever': [0.5],
    '7_EndingPitcher': [0.4],
    'All_Starter': [0.72],
    'All_MiddleReliever': [0.52],
    'All_EndingPitcher': [0.42]
}, index=[0])  # Add index to create a DataFrame with one row

predicted_hits = rf_regressor.predict(new_data)
print(f"\nPredicted Hits: {predicted_hits[0]:.2f}")
