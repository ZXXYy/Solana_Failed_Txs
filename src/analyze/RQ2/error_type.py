import json
import ast
import pandas as pd

def get_failed_count_for_type(df_types, error_type):
    error_logs = list(df_types[error_type])
    total_count = 0
    with open(f"src/analyze/RQ2/output_fig/failed_txs.log", "r") as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if line.strip() not in error_logs:
                continue
            # print(line.strip())
            programs = ast.literal_eval(lines[i+1])
            for program_id, cnt in programs.items():
                total_count += cnt
    return total_count
# Load the data
df_types = pd.read_csv("src/analyze/RQ2/output_fig/error_categorization.csv")
total = 0
total_perct = 0
for col in df_types.columns:
    cnt = get_failed_count_for_type(df_types, col)
    print(f"{col}: {cnt}, {cnt/801017921}")
    print("=====================================")
    total += cnt
    total_perct += cnt/801017921
total = total-84484-46075
print(f"Total: {total-84484-46075}")
print(f"Uncategorized: {801017921-total}, {(801017921-total)/801017921}, {1-total_perct}")