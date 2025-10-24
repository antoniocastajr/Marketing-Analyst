# PROJECT: Data Analyst Agent
# AUTHOR: Antonio Castañares Rodríguez

# DESCRIPTION: This file connects to the database, processes customer data, applies KMeans clustering to segment customers, 
# and stores the updated segments back in the database.

import pandas as pd
import sqlite3
import logging 
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# --------------------------------------LOGGING--------------------------------------------
# Logging configuration (print time, name, level and message using the terminal)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Suppress the httpx library logs to avoid cluttering the output
logging.getLogger("httpx").setLevel(logging.WARNING)

LOGGER = logging.getLogger(__name__)

# --------------------------------------FUNCTIONS------------------------------------------

def get_db_connection(db_path: str = 'data/leads_scored.db'):
    """Establish a connection to the SQLite database."""
    try:   
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        LOGGER.error(f"Failed to connect to database '{db_path}': {e}")
        raise

def load_data(conn):
    """Load data from the database."""
    try: 
        transactions = pd.read_sql('SELECT * FROM transactions', conn)
        leads_scored = pd.read_sql('SELECT * FROM leads_scored', conn)
        return transactions, leads_scored
    except Exception as e:
        LOGGER.error(f"Failed to load data from database: {e}")
        raise

def preprocess_data(transactions, leads_scored):
    """Calculate new metrics, merge features and fill missing values."""

    # Calculate purchase_frequency (group by user_email and count transactions)
    purchase_frequency = transactions.groupby('user_email').size().reset_index(name='purchase_frequency')

    # Take relevant columns and merge them with purchase_frequency, keeping all customers from leads_scored (left join)
    customer_data = leads_scored[['user_email','p1', 'member_rating']].merge(purchase_frequency, on='user_email', how='left')

    # Fill missing values
    customer_data['purchase_frequency'] = customer_data['purchase_frequency'].fillna(0)                                         # No purchases → 0 frequency
    customer_data['p1'] = customer_data['p1'].fillna(customer_data['p1'].mean())                                                # Missing lead score → mean
    customer_data['member_rating'] = customer_data['member_rating'].fillna(customer_data['member_rating'].mean())               # Missing rating → mean

    # Standardize features (all features should be on similar scale, mean=0, std=1)
    scaler = StandardScaler()
    X = customer_data[['purchase_frequency', 'p1', 'member_rating']]                                                            # Select features to scale
    X_scaled = scaler.fit_transform(X)

    return customer_data, X_scaled

def segment_customers(customer_data, X_scaled, n_clusters=5):
    """Segment customers using KMeans Clustering."""
    # Initialize KMeans, with specified number of clusters and random state for reproducibility
    kmeans = KMeans(n_clusters=n_clusters,random_state=42)
    customer_data['customer_segment'] = kmeans.fit_predict(X_scaled)

    return customer_data

def update_database(conn, customer_data):
    """Update the lead_scored table in the database with customer segments."""
    # Update the leads_scored table with new customer segments
    try:
        customer_data.to_sql('leads_scored', conn, if_exists='replace', index=False)
    except Exception as e:
        LOGGER.error(f"Failed to update database: {e}")
        raise

# --------------------------------------MAIN-----------------------------------------------

if __name__ == "__main__":
    LOGGER.info("Starting customer segmentation process.")
    try:
        conn = get_db_connection()
        LOGGER.info("Database connection established.")
        transactions, leads_scored = load_data(conn)
        LOGGER.info("Data loaded successfully.")
    except Exception as e:
        exit(1)

    customer_data, X_scaled = preprocess_data(transactions, leads_scored)
    LOGGER.info("Data preprocessed successfully.")
    customer_data = segment_customers(customer_data, X_scaled)
    LOGGER.info("Customers segmented successfully.")

    try:
        update_database(conn, customer_data)
        LOGGER.info("Database updated successfully.")
    except Exception as e:
        exit(1)
    finally:
        LOGGER.info("Closing database connection.")
        conn.close()

