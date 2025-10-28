# Demo Project

This is a demo project showcasing data generation and analysis capabilities.

## Project Structure

```
demo-project/
├── data_generator.py       # Data generation script
├── data/                   # Data directory
├── tests/                  # Test directory
└── README.md              # This file
```

## Data Generation

The project includes a lightweight data generation script that creates large CSV files with realistic random data using only Python standard library.

### Usage

```bash
# Generate default 5K records for both datasets
python data_generator.py

# Generate custom number of records
python data_generator.py --records 10000

# Generate specific dataset
python data_generator.py --dataset customers

# Custom output directory
python data_generator.py --output-dir /path/to/data
```

### Available Datasets

1. **Customer Data** (`customers.csv`)
   - Customer demographics and information
   - Fields: customer_id, name, email, address, age, income, etc.

2. **Sales Data** (`sales.csv`)
   - Sales transaction information
   - Fields: transaction_id, customer_id, product, amount, etc.

### Features

- **Lightweight**: Uses only Python standard library (no heavy dependencies)
- **Fast Build**: Container builds quickly without pandas, numpy, faker
- **Realistic Data**: Pre-defined sample data for realistic-looking results
- **Large Scale**: Can generate 5K+ records efficiently
- **Multiple Datasets**: Customer and sales data with relationships
- **Progress Tracking**: Shows progress during generation
- **File Size Info**: Reports file sizes and dataset statistics
- **Flexible**: Command-line interface for customization

## Integration with DVC

This project is integrated with DVC for data version control and tracking.