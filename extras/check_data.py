import pandas as pd

# Check what the raw tendencies file actually has
tendencies = pd.read_csv("data/team_tendencies.csv")
print("All columns:", tendencies.columns.tolist())

# Also check the lineups for missing rating columns
lineups = pd.read_csv("data/lineups.csv")
print("\nLineup columns:", lineups.columns.tolist())