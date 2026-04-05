"""
Spending Data Database Uploader
Uploads BLS CPI and Google Trends data to database
"""

import sys
from pathlib import Path

# Add project root to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import mysql.connector
from mysql.connector import Error, IntegrityError
import pandas as pd
from app.shared_utils import get_db_config, get_data_dir


class SpendingDatabaseUploader:
    def __init__(self, config=None):
        """Initialize database connection parameters from config dict or environment"""
        if config is None:
            config = get_db_config()

        self.host = config['host']
        self.user = config['user']
        self.password = config['password']
        self.database = config['database']
        self.port = config['port']
        self.connection = None

    def connect(self):
        """Establish connection to the database"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                charset='utf8mb4'
            )
            print("Successfully connected to database")
            return True
        except Error as e:
            print(f"Error connecting to database: {e}")
            return False

    def create_tables(self):
        """Create spending-related tables if they don't exist"""
        if not self.connection:
            print("No database connection. Call connect() first.")
            return False

        try:
            cursor = self.connection.cursor()

            # Table for BLS CPI data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS BLS_CPI_DATA (
                    CPI_ID INT AUTO_INCREMENT PRIMARY KEY,
                    CATEGORY VARCHAR(100) NOT NULL,
                    SERIES_ID VARCHAR(50) NOT NULL,
                    DATE DATE NOT NULL,
                    CPI_VALUE DECIMAL(10, 3),
                    MOM_PCT DECIMAL(10, 2),
                    YOY_PCT DECIMAL(10, 2),
                    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_category_date (CATEGORY, DATE)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            # Table for Google Trends data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS SPENDING_TRENDS (
                    TREND_ID INT AUTO_INCREMENT PRIMARY KEY,
                    CATEGORY VARCHAR(100) NOT NULL,
                    KEYWORD VARCHAR(255) NOT NULL,
                    AVG_INTEREST DECIMAL(10, 2),
                    RANK_IN_CATEGORY INT,
                    RECORDED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_category_keyword_date (CATEGORY, KEYWORD, RECORDED_AT)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            self.connection.commit()
            cursor.close()
            print("Tables created/verified successfully")
            return True

        except Error as e:
            print(f"Error creating tables: {e}")
            return False

    def upload_bls_data(self, df: pd.DataFrame) -> int:
        """
        Upload BLS CPI data from DataFrame to database.

        Args:
            df: DataFrame with columns: category, series_id, date, value, pct_1m, pct_12m

        Returns:
            Number of rows inserted
        """
        if not self.connection:
            print("No database connection. Call connect() first.")
            return 0

        try:
            cursor = self.connection.cursor()
            inserted = 0

            for _, row in df.iterrows():
                try:
                    # Convert NaN to None for proper NULL handling
                    cursor.execute("""
                        INSERT INTO BLS_CPI_DATA
                            (CATEGORY, SERIES_ID, DATE, CPI_VALUE, MOM_PCT, YOY_PCT)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            CPI_VALUE = VALUES(CPI_VALUE),
                            MOM_PCT = VALUES(MOM_PCT),
                            YOY_PCT = VALUES(YOY_PCT)
                    """, (
                        row['category'],
                        row['series_id'],
                        row['date'],
                        None if pd.isna(row['value']) else row['value'],
                        None if pd.isna(row['pct_1m']) else row['pct_1m'],
                        None if pd.isna(row['pct_12m']) else row['pct_12m']
                    ))
                    inserted += 1
                except IntegrityError:
                    continue

            self.connection.commit()
            cursor.close()
            print(f"Successfully uploaded {inserted} BLS CPI records")
            return inserted

        except Error as e:
            print(f"Error uploading BLS data: {e}")
            self.connection.rollback()
            return 0

    def upload_trends_data(self, df: pd.DataFrame) -> int:
        """
        Upload Google Trends data from DataFrame to database.

        Args:
            df: DataFrame with columns: Category, Keyword, Avg Interest, Rank in Cat

        Returns:
            Number of rows inserted
        """
        if not self.connection:
            print("No database connection. Call connect() first.")
            return 0

        try:
            cursor = self.connection.cursor()
            inserted = 0

            for _, row in df.iterrows():
                try:
                    # Convert NaN to None for proper NULL handling
                    cursor.execute("""
                        INSERT INTO SPENDING_TRENDS
                            (CATEGORY, KEYWORD, AVG_INTEREST, RANK_IN_CATEGORY)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        row['Category'],
                        row['Keyword'],
                        None if pd.isna(row['Avg Interest']) else row['Avg Interest'],
                        None if pd.isna(row['Rank in Cat']) else row['Rank in Cat']
                    ))
                    inserted += 1
                except IntegrityError:
                    continue

            self.connection.commit()
            cursor.close()
            print(f"Successfully uploaded {inserted} Google Trends records")
            return inserted

        except Error as e:
            print(f"Error uploading Trends data: {e}")
            self.connection.rollback()
            return 0

    def upload_from_csv(self, data_type: str):
        """
        Upload data from CSV files in the data directory.

        Args:
            data_type: 'bls' or 'trends'
        """
        data_path = get_data_dir('spending')

        if data_type == 'bls':
            csv_file = data_path / 'discretionary_bls_monthly.csv'
            if csv_file.exists():
                df = pd.read_csv(csv_file)
                # Convert column names to match expected format
                df = df.rename(columns={
                    'Category': 'category',
                    'Date': 'date'
                })
                # Need to get series_id, value, pct_1m, pct_12m from somewhere
                # For now, skip this - better to upload directly from the pipeline
                print(f"CSV upload for BLS not fully implemented - use direct DataFrame upload")
            else:
                print(f"File not found: {csv_file}")

        elif data_type == 'trends':
            csv_file = data_path / 'discretionary_trends_summary.csv'
            if csv_file.exists():
                df = pd.read_csv(csv_file)
                self.upload_trends_data(df)
            else:
                print(f"File not found: {csv_file}")

    def close(self):
        """Close the database connection"""
        if self.connection:
            self.connection.close()
            print("\nDatabase connection closed")


def main():
    """Main upload process"""
    uploader = SpendingDatabaseUploader()

    if uploader.connect():
        uploader.create_tables()

        # Upload trends data from CSV if it exists
        uploader.upload_from_csv('trends')

        uploader.close()


if __name__ == "__main__":
    main()
