from keras.models import Sequential
from keras.layers import Dense
from keras.optimizers import Adam
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
import pandas as pd
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


# Create the neural network model
model = Sequential()
model.add(Dense(64, activation='relu', input_shape=(len(features),)))
model.add(Dense(32, activation='relu'))
model.add(Dense(1))

# Compile the model
model.compile(optimizer=Adam(learning_rate=0.01), loss='mean_squared_error')

# Train the model
model.fit(X_train, y_train, epochs=100, batch_size=32, verbose=1)

# Make predictions on the test set
y_pred = model.predict(X_test)

# Print the predictions and actual values side by side
print("Predictions\tActual")
for pred, actual in zip(y_pred, y_test):
    print(f"{pred[0]:.2f}\t\t{actual}")

# Evaluate the model
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)
spearman_corr, _ = spearmanr(y_pred, y_test)
print(f"\nMean Squared Error: {mse:.4f}")
print(f"R-squared: {r2:.4f}")
print(f"Spearman Correlation: {spearman_corr:.4f}")