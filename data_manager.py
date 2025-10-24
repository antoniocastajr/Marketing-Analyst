# PROJECT: Data Analyst Agent
# AUTHOR: Antonio Castañares Rodríguez
# -----------------------

# DESCRIPTION: This file manages data loading from the SQLite database just once, avoiding redundant reads 
# and improving performance.

import logging
import pandas as pd
from sqlalchemy import create_engine

# --------------------------------------LOGGING--------------------------------------------
# Logging configuration (print time, name, level and message using the terminal)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Suppress the httpx library logs to avoid cluttering the output
logging.getLogger("httpx").setLevel(logging.WARNING)
LOGGER = logging.getLogger(__name__)

# --------------------------------------DATA MANAGER CLASS---------------------------------

class DataManager:
    """
    Description: Data Manager for handling database operations. This class loads data from
    the SQLite database only once and caches it for future use.
    """
    
    # Internal class variables
    _instance = None
    _leads: pd.DataFrame = None
    _leads_scored: pd.DataFrame = None
    _transactions: pd.DataFrame = None
    _products: pd.DataFrame = None
    _is_loaded: bool = False
    
    def __new__(cls):
        """
        Description: Ensure only one instance of DataManager exists.
        """

        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_data(self, db_path: str = 'data/leads_scored.db', force_reload: bool = False):
        """
        Description: Load data from the SQLite database (only once unless force_reload=True).
        Args:
            db_path (str): Path to the SQLite database file.
            force_reload (bool): If True, forces reloading data from the database.
        Returns:
            Tuple of DataFrames: (leads, leads_scored, transactions, products)
        """

        if not self._is_loaded or force_reload:                                                 # Load data only if not already loaded or if forced                                                                                                      
            try:
                engine = create_engine(f'sqlite:///{db_path}')                                  # Connect to the SQLite database
                conn = engine.connect()
                # Get data from each table
                self._leads = pd.read_sql('SELECT * FROM leads', conn)
                self._leads_scored = pd.read_sql('SELECT * FROM leads_scored', conn)
                self._transactions = pd.read_sql('SELECT * FROM transactions', conn)
                self._products = pd.read_sql('SELECT * FROM products', conn)
                conn.close()                                                                    # Close the connection
                
                # Verify all DataFrames were loaded successfully
                if self._leads is None or self._leads_scored is None or \
                   self._transactions is None or self._products is None:
                    raise ValueError("One or more tables failed to load from database")
                if self._leads.empty or self._leads_scored.empty or \
                   self._transactions.empty or self._products.empty:
                    LOGGER.warning("One or more tables are empty in the database")
                
                self._is_loaded = True                                                          # Mark data as loaded if successful                                          
                LOGGER.info(f"Data loaded successfully from database {db_path}")
            except Exception as e:
                LOGGER.error(f"Error loading data from database: {e}")
                self._is_loaded = False                                                         # Critical: ensure flag is False on error
                
                # Reset all DataFrames to None on error
                self._leads = None
                self._leads_scored = None
                self._transactions = None
                self._products = None
                raise
        else:
            LOGGER.info("Data already loaded, using cached version.")
        return self._leads.copy(), self._leads_scored.copy(), self._transactions.copy(), self._products.copy()

    def refresh_data(self, db_path: str = 'data/leads_scored.db'):
        """
        Description: Force reload data from database.
        Args:
            db_path (str): Path to the SQLite database file.
        Returns:
            None
        """

        LOGGER.info("Forcing data refresh...")
        self.load_data(db_path, force_reload=True)
        
    @property
    def leads(self):
        """
        Description: Get leads DataFrame (loads if not already loaded).
        Args:
            None
        Returns:
            pd.DataFrame: leads DataFrame
        """
        if not self._is_loaded:                                                                 # Load data if not already loaded
            LOGGER.warning("Data not loaded yet, loading now...")
            self.load_data()
        if self._leads is None:
            raise ValueError("Leads data is not available. Database may not have loaded correctly.")
        return self._leads.copy()
    
    @property
    def leads_scored(self):
        """
        Description: Get leads_scored DataFrame (loads if not already loaded).
        Args:
            None
        Returns:
            pd.DataFrame: leads_scored DataFrame
        """
        if not self._is_loaded:                                                                 # Load data if not already loaded
            LOGGER.warning("Data not loaded yet, loading now...")
            self.load_data()
        if self._leads_scored is None:
            raise ValueError("Leads scored data is not available. Database may not have loaded correctly.")
        return self._leads_scored.copy()

    @property
    def transactions(self):
        """
        Description: Get transactions DataFrame (loads if not already loaded).
        Args:
            None
        Returns:
            pd.DataFrame: transactions DataFrame
        """
        if not self._is_loaded:                                                                 # Load data if not already loaded
            LOGGER.warning("Data not loaded yet, loading now...")
            self.load_data()
        if self._transactions is None:
            raise ValueError("Transactions data is not available. Database may not have loaded correctly.")
        return self._transactions.copy()
    
    @property
    def products(self):
        """
        Description: Get products DataFrame (loads if not already loaded).
        Args:
            None
        Returns:
            pd.DataFrame: products DataFrame
        """
        if not self._is_loaded:                                                                 # Load data if not already loaded
            LOGGER.warning("Data not loaded yet, loading now...")
            self.load_data()
        if self._products is None:
            raise ValueError("Products data is not available. Database may not have loaded correctly.")
        return self._products.copy()
    