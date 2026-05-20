import pandas as pd
import os

# Step 1: Load the full dataset
full_data_path = "data/raw_data/accepted_2007_to_2018Q4.csv"
output_path = "data/raw_data/lending_club_clean_sample.csv"

# Step 2: Load CSV
print("Loading full dataset...")
df = pd.read_csv(full_data_path, low_memory=False)

# Step 3: Filter only 'Fully Paid' and 'Charged Off'
df = df[df['loan_status'].isin(['Fully Paid', 'Charged Off'])]

# Step 4: Select relevant columns
columns_to_keep = [
    'loan_amnt', 'term', 'int_rate', 'grade', 'emp_length', 'home_ownership',
    'annual_inc', 'purpose', 'dti', 'delinq_2yrs', 'revol_util',
    'total_acc', 'loan_status'
]
df = df[columns_to_keep]

# Step 5: Drop missing values
df.dropna(inplace=True)

# Step 6: Sample 5,000 rows
df_sample = df.sample(n=5000, random_state=42)

# Step 7: Save the sample
os.makedirs("data/raw_data", exist_ok=True)
df_sample.to_csv(output_path, index=False)

print(f"Sample saved to {output_path}")
