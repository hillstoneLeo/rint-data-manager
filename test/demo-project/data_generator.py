#!/usr/bin/env python3
"""
Data generation script for creating large CSV files with random data.
Pure Python implementation using only standard library.
"""

import random
import csv
import argparse
import os
from datetime import datetime, timedelta

# Sample data for generating realistic-looking data
FIRST_NAMES = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda', 'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica', 'Thomas', 'Sarah', 'Charles', 'Karen']
LAST_NAMES = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin']
CITIES = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 'San Antonio', 'San Diego', 'Dallas', 'San Jose', 'Austin', 'Jacksonville', 'Fort Worth', 'Columbus', 'Charlotte', 'San Francisco', 'Indianapolis', 'Seattle', 'Denver', 'Washington']
STATES = ['California', 'Texas', 'New York', 'Florida', 'Illinois', 'Pennsylvania', 'Ohio', 'Georgia', 'North Carolina', 'Michigan', 'New Jersey', 'Virginia', 'Washington', 'Arizona', 'Massachusetts', 'Tennessee', 'Indiana', 'Missouri', 'Maryland', 'Wisconsin']
CATEGORIES = ['Electronics', 'Clothing', 'Food', 'Books', 'Sports', 'Home', 'Toys', 'Health', 'Automotive', 'Garden']
PRODUCTS = ['Laptop', 'Phone', 'Tablet', 'Headphones', 'Mouse', 'Keyboard', 'Monitor', 'Camera', 'Speaker', 'Watch', 'Shoes', 'Shirt', 'Pants', 'Jacket', 'Book', 'Ball', 'Bike', 'Chair', 'Table', 'Lamp']
PAYMENT_METHODS = ['Credit Card', 'Debit Card', 'Cash', 'PayPal', 'Bank Transfer', 'Apple Pay', 'Google Pay']

def generate_random_name():
    """Generate a random full name."""
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

def generate_random_email(first_name, last_name):
    """Generate a random email address."""
    domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'example.com', 'test.com']
    username_patterns = [
        f"{first_name.lower()}.{last_name.lower()}",
        f"{first_name[0].lower()}{last_name.lower()}",
        f"{first_name.lower()}{random.randint(1, 99)}",
        f"{last_name.lower()}{random.randint(1, 99)}"
    ]
    return f"{random.choice(username_patterns)}@{random.choice(domains)}"

def generate_random_phone():
    """Generate a random US phone number."""
    area_codes = ['212', '646', '917', '718', '347', '929', '516', '631', '914', '845']
    return f"({random.choice(area_codes)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"

def generate_random_address():
    """Generate a random address."""
    street_numbers = [str(random.randint(1, 9999))]
    street_names = ['Main St', 'Oak Ave', 'Elm St', 'Park Ave', 'Pine St', 'Maple Ave', 'Cedar St', 'Washington St', 'Lincoln Ave', 'Broadway']
    return f"{random.choice(street_numbers)} {random.choice(street_names)}"

def generate_customer_data(num_records=5000):
    """Generate customer data."""
    print(f"Generating {num_records} customer records...")
    
    data = []
    start_date = datetime.now() - timedelta(days=365*2)
    
    for i in range(num_records):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        
        record = {
            'customer_id': f'CUST_{i+1:06d}',
            'first_name': first_name,
            'last_name': last_name,
            'email': generate_random_email(first_name, last_name),
            'phone': generate_random_phone(),
            'address': generate_random_address(),
            'city': random.choice(CITIES),
            'state': random.choice(STATES),
            'zip_code': f"{random.randint(10000, 99999)}",
            'country': 'USA',
            'age': random.randint(18, 80),
            'gender': random.choice(['Male', 'Female', 'Other']),
            'income': round(random.uniform(25000, 200000), 2),
            'credit_score': random.randint(300, 850),
            'registration_date': (start_date + timedelta(days=random.randint(0, 730))).strftime('%Y-%m-%d'),
            'last_purchase_date': (start_date + timedelta(days=random.randint(0, 730))).strftime('%Y-%m-%d'),
            'total_purchases': random.randint(0, 1000),
            'avg_purchase_amount': round(random.uniform(10, 500), 2),
            'preferred_category': random.choice(CATEGORIES),
            'loyalty_member': random.choice([True, False]),
            'newsletter_subscribed': random.choice([True, False]),
        }
        data.append(record)
        
        if (i + 1) % 1000 == 0:
            print(f"Generated {i + 1} records...")
    
    return data

def generate_sales_data(num_records=5000):
    """Generate sales data."""
    print(f"Generating {num_records} sales records...")
    
    data = []
    start_date = datetime.now() - timedelta(days=365*2)
    
    for i in range(num_records):
        quantity = random.randint(1, 10)
        unit_price = round(random.uniform(10, 1000), 2)
        total_amount = quantity * unit_price
        discount_percent = round(random.uniform(0, 30), 2)
        discount_amount = total_amount * (discount_percent / 100)
        tax_amount = (total_amount - discount_amount) * 0.08
        final_amount = total_amount - discount_amount + tax_amount
        
        record = {
            'transaction_id': f'TXN_{i+1:08d}',
            'customer_id': f'CUST_{random.randint(1, 5000):06d}',
            'product_name': random.choice(PRODUCTS),
            'quantity': quantity,
            'unit_price': unit_price,
            'total_amount': round(total_amount, 2),
            'discount_percent': discount_percent,
            'discount_amount': round(discount_amount, 2),
            'tax_amount': round(tax_amount, 2),
            'final_amount': round(final_amount, 2),
            'payment_method': random.choice(PAYMENT_METHODS),
            'store_location': random.choice(CITIES),
            'sales_rep': generate_random_name(),
            'transaction_date': (start_date + timedelta(days=random.randint(0, 730), hours=random.randint(0, 23), minutes=random.randint(0, 59))).strftime('%Y-%m-%d %H:%M:%S'),
            'customer_rating': random.randint(1, 5),
            'return_flag': random.choice([True, False]),
        }
        data.append(record)
        
        if (i + 1) % 1000 == 0:
            print(f"Generated {i + 1} records...")
    
    return data

def save_dataset_to_csv(data, filename, output_dir='data'):
    """Save dataset to CSV file."""
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    
    print(f"Saving dataset to {filepath}...")
    
    if not data:
        print("Warning: No data to save!")
        return None
    
    fieldnames = data[0].keys()
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    file_size = os.path.getsize(filepath)
    print(f"Dataset saved successfully!")
    print(f"Shape: {len(data)} rows x {len(fieldnames)} columns")
    print(f"Size: {file_size / (1024*1024):.2f} MB")
    print(f"Columns: {list(fieldnames)}")
    
    return filepath

def main():
    """Main function to generate datasets."""
    parser = argparse.ArgumentParser(description='Generate demo datasets')
    parser.add_argument('--records', type=int, default=5000, help='Number of records to generate')
    parser.add_argument('--dataset', type=str, default='all', choices=['customers', 'sales', 'all'], help='Dataset to generate')
    parser.add_argument('--output-dir', type=str, default='data', help='Output directory')
    
    args = parser.parse_args()
    
    print("=== Data Generation Script (Pure Python) ===")
    print(f"Records: {args.records}")
    print(f"Dataset: {args.dataset}")
    print(f"Output Directory: {args.output_dir}")
    print()
    
    generated_files = []
    
    if args.dataset in ['customers', 'all']:
        print("Generating Customer Dataset...")
        customer_data = generate_customer_data(args.records)
        customer_file = save_dataset_to_csv(customer_data, 'customers.csv', args.output_dir)
        if customer_file:
            generated_files.append(customer_file)
        print()
    
    if args.dataset in ['sales', 'all']:
        print("Generating Sales Dataset...")
        sales_data = generate_sales_data(args.records)
        sales_file = save_dataset_to_csv(sales_data, 'sales.csv', args.output_dir)
        if sales_file:
            generated_files.append(sales_file)
        print()
    
    print("=== Generation Complete ===")
    print(f"Generated files: {generated_files}")

if __name__ == "__main__":
    main()