# Practice: Python fundamentals
# for SME Analytics Platform

# 1. Sales record as dictionary
sales_record = {
    "date": "2026-01-01",
    "product": "Thanakha",
    "quantity": 10,
    "price": 5000,
    "total": 10 * 5000
}

print("Single record:", sales_record)

# 2. List of sales records
sales_data = [
    {"date": "2026-01-01", "product": "Thanakha", "quantity": 10, "price": 5000},
    {"date": "2026-01-02", "product": "Shampoo", "quantity": 5, "price": 8000},
    {"date": "2026-01-03", "product": "Soap", "quantity": 20, "price": 2000},
    {"date": "2026-01-04", "product": "Longyi", "quantity": 3, "price": 15000},
    {"date": "2026-01-05", "product": "Thanakha", "quantity": 8, "price": 5000},
]

# 3. Function to calculate total revenue
def calculate_total_revenue(data):
    total = 0
    for record in data:
        total += record["quantity"] * record["price"]
    return total

print("Total revenue:", calculate_total_revenue(sales_data))

# 4. Function to find best selling product
def find_best_product(data):
    product_sales = {}
    for record in data:
        product = record["product"]
        revenue = record["quantity"] * record["price"]
        if product in product_sales:
            product_sales[product] += revenue
        else:
            product_sales[product] = revenue
    best = max(product_sales, key=product_sales.get)
    return best, product_sales[best]

best_product, best_revenue = find_best_product(sales_data)
print(f"Best product: {best_product} with {best_revenue} MMK")

# 5. Function to calculate average sale
def calculate_average(data):
    total = calculate_total_revenue(data)
    return total / len(data)

print("Average sale:", calculate_average(sales_data))