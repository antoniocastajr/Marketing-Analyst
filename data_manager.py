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
    """Data Manager for handling database operations."""
    
    # Internal class variables
    _instance = None
    _leads_scored: pd.DataFrame = None
    _transactions: pd.DataFrame = None
    _products: pd.DataFrame = None
    _is_loaded: bool = False
    
    def __new__(cls):
        """Ensure only one instance of DataManager exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_data(self, db_path: str = 'data/leads_scored.db', force_reload: bool = False):
        """Load data from the SQLite database (only once unless force_reload=True)."""
        if not self._is_loaded or force_reload:
            try:
                engine = create_engine(f'sqlite:///{db_path}')
                conn = engine.connect()
                self._leads_scored = pd.read_sql('SELECT * FROM leads_scored', conn)
                self._transactions = pd.read_sql('SELECT * FROM transactions', conn)
                self._products = pd.read_sql('SELECT * FROM products', conn)
                conn.close()
                self._is_loaded = True
                LOGGER.info(f"Data loaded successfully from database: {len(self._leads_scored)} leads, {len(self._transactions)} transactions")
            except Exception as e:
                LOGGER.error(f"Error loading data from database: {e}")
                raise
        else:
            LOGGER.info("Data already loaded, using cached version.")
        return self._leads_scored.copy(), self._transactions.copy(), self._products.copy()

    def refresh_data(self, db_path: str = 'data/leads_scored.db'):
        """Force reload data from database."""
        LOGGER.info("Forcing data refresh...")
        self.load_data(db_path, force_reload=True)
        
    @property
    def leads(self):
        """Get leads_scored DataFrame (loads if not already loaded)."""
        if not self._is_loaded:
            LOGGER.warning("Data not loaded yet, loading now...")
            self.load_data()
        return self._leads_scored.copy()

    @property
    def transactions(self):
        """Get transactions DataFrame (loads if not already loaded)."""
        if not self._is_loaded:
            LOGGER.warning("Data not loaded yet, loading now...")
            self.load_data()
        return self._transactions.copy()
    
    @property
    def products(self):
        """Get products DataFrame (loads if not already loaded)."""
        if not self._is_loaded:
            LOGGER.warning("Data not loaded yet, loading now...")
            self.load_data()
        return self._products.copy()
    