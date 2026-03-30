# import pandas as pd
#
# # Create the Source Ledger (Exact values)
# source_data = {
#     'ITEM_ID': ['REF-001', 'REF-002', 'REF-003', 'REF-004', 'REF-005', 'REF-006'],
#     'AMOUNT': ['$43,889,654', '$43,889', '$50,000,000', '$1,200,000', '$750,200', 'PENDING'],
#     'REGION': ['NORTH', 'SOUTH', 'EAST', 'WEST', 'CENTRAL', 'OFFSHORE']
# }
#
# # Create the Target Ledger (Shorthand values for testing)
# target_data = {
#     'ITEM_ID': ['REF-001', 'REF-002', 'REF-003', 'REF-004', 'REF-005', 'REF-006'],
#     'AMOUNT': ['43.9M', '43.9K', '50M', '1.2K', '800K', 'PENDING'],
#     'REGION': ['NORTH', 'SOUTH', 'EAST', 'WEST', 'CENTRAL', 'OFFSHORE']
# }
#
# # Save to Excel with two sheets for comparison
# with pd.ExcelWriter('Audit_Test_Cases.xlsx') as writer:
#     pd.DataFrame(source_data).to_excel(writer, sheet_name='Source_Ledger', index=False)
#     pd.DataFrame(target_data).to_excel(writer, sheet_name='Target_Shorthand', index=False)
#
# print("✅ 'Audit_Test_Cases.xlsx' created successfully!")

import pandas as pd
import random

# Setting up 50 rows of data
rows = 50
item_ids = [f"REF-{str(i).zfill(3)}" for i in range(1, rows + 1)]
categories = ["CAPEX", "OPEX", "EQUITY", "PAYROLL", "MARKETING", "LEGAL", "TAX", "RENT"]
regions = ["North", "South", "East", "West", "Central", "Global"]

# Create Source Ledger (Exact values)
source_amounts = []
for i in range(rows):
    base = random.randint(1000, 100000000)
    source_amounts.append(f"${base:,}")

source_data = {
    'ITEM_ID': item_ids,
    'CATEGORY': [random.choice(categories) for _ in range(rows)],
    'REGION': [random.choice(regions) for _ in range(rows)],
    'AMOUNT': source_amounts,
    'STATUS': ['FINALIZED'] * rows
}

# Create Target Ledger (Shorthand & Mixed Results)
target_amounts = []
for i, val in enumerate(source_amounts):
    raw_num = float(val.replace('$', '').replace(',', ''))

    # Mix up the results for validation testing:
    if i % 5 == 0:  # Every 5th row is a Million shorthand (Yellow)
        target_amounts.append(f"{round(raw_num / 1_000_000, 1)}M")
    elif i % 7 == 0:  # Every 7th row is a Thousand shorthand (Yellow)
        target_amounts.append(f"{round(raw_num / 1_000, 1)}K")
    elif i % 10 == 0:  # Every 10th row is an Error (Red)
        target_amounts.append(f"${raw_num + 50000:,}")
    else:  # Rest are exact matches (White)
        target_amounts.append(val)

target_data = {
    'ITEM_ID': item_ids,
    'CATEGORY': source_data['CATEGORY'],
    'REGION': source_data['REGION'],
    'AMOUNT': target_amounts,
    'STATUS': source_data['STATUS']
}

with pd.ExcelWriter('Audit_Test_Cases_50Rows.xlsx') as writer:
    pd.DataFrame(source_data).to_excel(writer, sheet_name='Source_Ledger', index=False)
    pd.DataFrame(target_data).to_excel(writer, sheet_name='Target_Shorthand', index=False)

print("✅ 50-Row Test File Created: 'Audit_Test_Cases_50Rows.xlsx'")


import sys
print(sys.executable)