import pandas as pd

print("=" * 40)
print("pandas Practice")
print("=" * 40)

# Create DataFrame
data = {
    "Date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05", "2026-01-03"],
    "Product": ["Thanakha", "Shampoo", "Soap", "Longyi", "Thanakha", "Soap"],
    "Quantity": [10, 5, 20, 3, 8, 20],
    "Price": [5000, 8000, 2000, 15000, 5000, 2000],
    "Branch": ["Yangon", "Mandalay", "Yangon", "Mandalay", "Yangon", "Yangon"]
}

df = pd.DataFrame(data)

# Basic info
print("\n1. Shape (rows, columns):")
print(df.shape)

print("\n2. Column data types:")
print(df.dtypes)

print("\n3. First 3 rows:")
print(df.head(3))

print("\n4. Basic statistics:")
print(df.describe())

# Missing values
print("\n5. Missing values per column:")
print(df.isnull().sum())

# Duplicates
print("\n6. Duplicate rows:")
print(f"Number of duplicates: {df.duplicated().sum()}")

# Calculations
print("\n7. Add Revenue column:")
df["Revenue"] = df["Quantity"] * df["Price"]
print(df[["Product", "Quantity", "Price", "Revenue"]])

print("\n8. Total revenue:")
print(f"{df['Revenue'].sum():,} MMK")

print("\n9. Best selling product:")
best = df.groupby("Product")["Revenue"].sum()
print(best.sort_values(ascending=False))

print("\n10. Sales by branch:")
branch = df.groupby("Branch")["Revenue"].sum()
print(branch)

print("\n11. Remove duplicates:")
df_clean = df.drop_duplicates()
print(f"Before: {len(df)} rows")
print(f"After: {len(df_clean)} rows")

print("\n" + "=" * 40)
print("pandas Practice Complete! ✅")
print("=" * 40)