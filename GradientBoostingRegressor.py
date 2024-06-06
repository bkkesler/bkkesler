import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_squared_error, r2_score
from scipy.stats import spearmanr

year = 2023
start_date = f"{year}-04-01"
end_date = f"{year}-10-01"
final_dataframe = pd.read_pickle(f'player_game_stats_{start_date}_to_{end_date}.pkl')

# Remove rows with NaN values
final_dataframe = final_dataframe.dropna()

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

# Create and train the Gradient Boosting Regressor
gb_regressor = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, max_depth=3, random_state=42)
gb_regressor.fit(X_train, y_train)

# Perform grid search to find the best hyperparameters
param_grid = {
    'n_estimators': [50, 100, 200],
    'learning_rate': [0.01, 0.1, 0.2],
    'max_depth': [3, 5, 7]
}
grid_search = GridSearchCV(estimator=gb_regressor, param_grid=param_grid, cv=5, scoring='neg_mean_squared_error')
grid_search.fit(X_train, y_train)

# Get the best model and its parameters
best_gb_regressor = grid_search.best_estimator_
print(f"Best parameters: {grid_search.best_params_}")

# Make predictions on the test set using the best model
y_pred = best_gb_regressor.predict(X_test)

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