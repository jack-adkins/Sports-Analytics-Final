import pandas as pd

matchup = pd.read_csv("data/matchup_data.csv")
print("Columns:", matchup.columns.tolist())
print("Rows:", len(matchup))
print("\nSample:")
print(matchup.head(10).to_string())