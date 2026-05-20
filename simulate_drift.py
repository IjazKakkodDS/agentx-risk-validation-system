import pandas as pd
import numpy as np
import os

# Load original clean sample
df = pd.read_csv("data/raw_data/lending_club_clean_sample.csv")

# Simulate drift
df_drifted = df.copy()
if "annual_inc" in df_drifted.columns:
    df_drifted["annual_inc"] *= np.random.uniform(1.3, 1.6)

if "loan_amnt" in df_drifted.columns:
    df_drifted["loan_amnt"] += np.random.normal(5000, 2000, len(df_drifted))

if "int_rate" in df_drifted.columns:
    df_drifted.drop("int_rate", axis=1, inplace=True)

# Save simulated data
os.makedirs("data/drift_test", exist_ok=True)
df_drifted.to_csv("data/drift_test/incoming_drifted_data.csv", index=False)
print("✅ Drifted data saved to: data/drift_test/incoming_drifted_data.csv")
