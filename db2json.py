import sqlite3
import json

# Connect to the SQLite database
conn = sqlite3.connect('votes.db')
cursor = conn.cursor()

# Get all table names in the database
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

# Dictionary to store all table data
database_dict = {}

# Iterate through all tables
for table in tables:
    table_name = table[0]
    cursor.execute(f"SELECT * FROM {table_name}")
    
    # Get column names
    columns = [description[0] for description in cursor.description]
    
    # Fetch all rows
    rows = cursor.fetchall()
    
    # Convert rows to list of dictionaries
    table_data = []
    for row in rows:
        table_data.append(dict(zip(columns, row)))
    
    # Add table data to the main dictionary
    database_dict[table_name] = table_data

# Close the connection
conn.close()

# Write to JSON file
with open('votes_db_content.json', 'w') as json_file:
    json.dump(database_dict, json_file, indent=2)

print("Database contents have been exported to votes_db_content.json")
