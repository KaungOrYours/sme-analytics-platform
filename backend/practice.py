# ================================
# SME Analytics - Python Practice
# ================================

print("=" * 40)
print("SME Analytics Python Practice")
print("=" * 40)

# 1. Sales record as dictionary
print("\n1. Single Sales Record:")
sales_record = {
    "date": "2026-01-01",
    "product": "Thanakha",
    "quantity": 10,
    "price": 5000,
    "total": 10 * 5000
}
print(sales_record)

# 2. List of sales records
print("\n2. Multiple Sales Records:")
sales_data = [
    {"date": "2026-01-01", "product": "Thanakha", "quantity": 10, "price": 5000},
    {"date": "2026-01-02", "product": "Shampoo", "quantity": 5, "price": 8000},
    {"date": "2026-01-03", "product": "Soap", "quantity": 20, "price": 2000},
    {"date": "2026-01-04", "product": "Longyi", "quantity": 3, "price": 15000},
    {"date": "2026-01-05", "product": "Thanakha", "quantity": 8, "price": 5000},
]
print(f"Total records: {len(sales_data)}")

# 3. Calculate total revenue
print("\n3. Total Revenue:")
def calculate_total_revenue(data):
    total = 0
    for record in data:
        revenue = record["quantity"] * record["price"]
        total += revenue
    return total

total = calculate_total_revenue(sales_data)
print(f"Total Revenue: {total:,} MMK")

# 4. Find best selling product
print("\n4. Best Selling Product:")
def find_best_product(data):
    product_totals = {}
    for record in data:
        product = record["product"]
        revenue = record["quantity"] * record["price"]
        if product in product_totals:
            product_totals[product] += revenue
        else:
            product_totals[product] = revenue
    best = max(product_totals, key=product_totals.get)
    return best, product_totals[best], product_totals

best, revenue, all_products = find_best_product(sales_data)
print(f"Best Product: {best}")
print(f"Revenue: {revenue:,} MMK")
print(f"All products: {all_products}")

# 5. Filter records
print("\n5. Filter - Thanakha only:")
thanakha_sales = [r for r in sales_data if r["product"] == "Thanakha"]
print(f"Thanakha records: {len(thanakha_sales)}")
for r in thanakha_sales:
    print(f"  {r['date']}: {r['quantity']} units")

# 6. Sort by price
print("\n6. Products sorted by price:")
sorted_data = sorted(sales_data, key=lambda x: x["price"], reverse=True)
for r in sorted_data:
    print(f"  {r['product']}: {r['price']:,} MMK")

print("\n" + "=" * 40)
print("Practice Complete! ✅")
print("=" * 40)