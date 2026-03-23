import pandas as pd

# Create DataFrame from our sales data
data = {
    "Date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05"],
    "Product": ["Thanakha", "Shampoo", "Soap", "Longyi", "Thanakha"],
    "Quantity": [10, 5, 20, 3, 8],
    "Price": [5000, 8000, 2000, 15000, 5000]
}

df = pd.DataFrame(data)

# Basic operations
print("Shape:", df.shape)
print("\nColumn types:\n", df.dtypes)
print("\nFirst 3 rows:\n", df.head(3))
print("\nBasic stats:\n", df.describe())
print("\nTotal revenue:", (df["Quantity"] * df["Price"]).sum())
print("\nBest product:", df.groupby("Product")["Quantity"].sum().idxmax())
print("\nMissing values:\n", df.isnull().sum())