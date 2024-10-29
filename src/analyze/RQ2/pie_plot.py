import matplotlib.pyplot as plt
import numpy as np

# Data
error_types = [
    "Price or Profit not met",
    "Invalid Status",
    "Out of Funds",
    "Invalid Input Parameters",
    "Network Delay",
    "Invalid Input Account",
    "Out of Resource",
    "Program Runtime Error",
    "Program Logic Constraint Violation",
    "Unknown",
    "Uncategorized"
]

counts = [
    351522390,
    341586093,
    31737032,
    27496008,
    21617568,
    6760053,
    4446004,
    352908,
    427387,
    13751672,
    1451365
]

percentages = [
    43.88,
    42.64,
    3.96,
    3.43,
    2.70,
    0.84,
    0.56,
    0.04,
    0.05,
    1.72,
    0.18
]

# Create figure and axis
plt.figure(figsize=(16, 8))

# Create pie chart
# Only show labels for sections larger than 2%
labels = [f'{pct:.2f}%' if pct >= 2 else '' 
          for type, count, pct in zip(error_types, counts, percentages)]
# Set global font sizes
plt.rcParams.update({
    'font.size': 20,
    'axes.titlesize': 16,
    'axes.labelsize': 14,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'legend.fontsize': 18,
    'legend.title_fontsize': 18
})
# Colors
colors = [(0.12, 0.47, 0.71, 0.7),  # Blue
          (1.0, 0.5, 0.05, 0.7),    # Orange
          (0.17, 0.63, 0.17, 0.7),  # Green
          (0.84, 0.15, 0.16, 0.7),  # Red
          (0.58, 0.40, 0.74, 0.7),  # Purple
          (0.55, 0.34, 0.29, 0.7),  # Brown
          (0.89, 0.47, 0.76, 0.7),  # Pink
          (0.5, 0.5, 0.5, 0.7),     # Gray
          (0.74, 0.74, 0.13, 0.7),  # Yellow
          (0.09, 0.75, 0.81, 0.7),  # Cyan
          (0.2, 0.2, 0.2, 0.7)]     # Dark Gray (for the 11th category)

# Create pie chart
wedges, texts, autotexts = plt.pie(percentages, 
                                  labels=labels,
                                  colors=colors,
                                  autopct='',
                                  startangle=90,
                                  textprops={'fontsize': 20},
                                  labeldistance=1.1)

# Create legend
legend_labels = [f"{error_type} ({pct:.2f}%)" 
                for error_type, pct in zip(error_types, percentages)]
plt.legend(wedges, legend_labels,
          title="Error Types",
          loc="upper center",
          bbox_to_anchor=(1, 0, 0.5, 1))

# plt.title('Distribution of Error Types for Failed Transactions', pad=20)

# Ensure the pie chart is circular
plt.axis('equal')

# Adjust layout to prevent legend cutoff
plt.tight_layout()

plt.savefig(f'src/analyze/RQ2/output_fig/pie_error.png', dpi=300) 