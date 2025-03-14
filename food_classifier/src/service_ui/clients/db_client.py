import os
import mysql.connector
from datetime import datetime, timedelta
from pathlib import Path
import pytz

class DatabaseClient:
    def __init__(self):
        """
        Initialize the database client with connection parameters.
        If no parameters are provided, use environment variables from .env file.
        """
        env_path = Path('/etc/food-classifier/.env')
        
        # Load environment variables from .env file
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip('"').strip("'")
        
        # Use environment variables
        self.host = os.getenv('AZURE_MYSQL_HOST')
        self.user = os.getenv('AZURE_MYSQL_USER')
        self.password = os.getenv('AZURE_MYSQL_PASSWORD')
        self.database = os.getenv('AZURE_MYSQL_DATABASE')
        self.ssl_ca = os.getenv('AZURE_MYSQL_SSL_CA')
        self.connection = None

    def connect(self):
        """
        Establish a connection to the Azure MySQL database.
        """
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                ssl_ca=self.ssl_ca
            )
        except mysql.connector.Error as err:
            print("Error connecting to database:", str(err))
            self.connection = None

    def close(self):
        """
        Close the database connection.
        """
        if self.connection:
            self.connection.close()

    def get_customer_basic_info(self, combined_code):
        """
        Query the database for customer basic information.
        """
        if not self.connection:
            print("No database connection.")
            return None

        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Query for customer basic information
            cursor.execute("""
                SELECT customer_id, code, name, gender, age, height, weight, photo_url, notes 
                FROM customer 
                WHERE code = %s
            """, (combined_code,))
            customer_info = cursor.fetchone()
            
            cursor.close()
            return customer_info
            
        except mysql.connector.Error as err:
            print("Database error:", str(err))
            return None

    def get_customer_nutrition_info(self, customer_id):
        """
        Query the database for customer's recent 5 days nutritional intake
        and recommended nutrition ranges.
        """
        if not self.connection:
            print("No database connection.")
            return None

        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Query for recent 5 days nutritional intake
            five_days_ago = datetime.now() - timedelta(days=5)
            
            # 쿼리 수정: date로 그룹화하여 일별 총량 계산
            cursor.execute("""
                SELECT 
                    c.date,
                    SUM(n.Energy) as total_calories,
                    SUM(n.Carbohydrates) as total_carbohydrates,
                    SUM(n.Protein) as total_protein,
                    SUM(n.Fat) as total_fat,
                    SUM(n.Dietary_Fiber) as total_fiber,
                    SUM(n.Sodium) as total_sodium
                FROM consumption c
                JOIN nutrition_info n ON c.food_id = n.food_id
                WHERE c.customer_id = %s AND c.date >= %s
                GROUP BY c.date
                ORDER BY c.date DESC
            """, (customer_id, five_days_ago))
            recent_nutrition = cursor.fetchall()
            
            # Query for recommended nutrition ranges
            cursor.execute("""
                SELECT 
                    Energy_min, Energy_max,
                    Carbohydrates_min, Carbohydrates_max,
                    Protein_min, Protein_max,
                    Fat_min, Fat_max,
                    Dietary_Fiber_min, Dietary_Fiber_max,
                    Sodium_min, Sodium_max
                FROM recommended_nutrition
                WHERE customer_id = %s
            """, (customer_id,))
            recommended = cursor.fetchone()
            
            cursor.close()
            
            return {
                'recent_nutrition': recent_nutrition,
                'recommended_nutrition': {
                    'calories': {'min': recommended['Energy_min'], 'max': recommended['Energy_max']},
                    'carbohydrates': {'min': recommended['Carbohydrates_min'], 'max': recommended['Carbohydrates_max']},
                    'protein': {'min': recommended['Protein_min'], 'max': recommended['Protein_max']},
                    'fat': {'min': recommended['Fat_min'], 'max': recommended['Fat_max']},
                    'fiber': {'min': recommended['Dietary_Fiber_min'], 'max': recommended['Dietary_Fiber_max']},
                    'sodium': {'min': recommended['Sodium_min'], 'max': recommended['Sodium_max']}
                }
            }
            
        except mysql.connector.Error as err:
            print("Database error:", str(err))
            return None

    def get_food_info_from_db(self, food_name):
        """
        Query the nutrition database for food information based on the food name.
        Returns nutritional information from nutrition_info table.
        """
        if not self.connection:
            print("No database connection.")
            return None

        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Query for food information from nutrition_info table
            cursor.execute("""
                SELECT food_id, food_name, Energy, Carbohydrates, Protein, Fat, Dietary_Fiber, Sodium
                FROM nutrition_info 
                WHERE food_name = %s
            """, (food_name,))
            food_info = cursor.fetchone()
            
            cursor.close()
            return food_info
            
        except mysql.connector.Error as err:
            print("Database error:", str(err))
            return None

    def get_recommended_nutrition(self, customer_id):
        """
        Get recommended nutrition ranges for a customer.
        """
        if not self.connection:
            print("No database connection.")
            return None

        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Query for recommended nutrition ranges
            cursor.execute("""
                SELECT 
                    Energy_min, Energy_max,
                    Carbohydrates_min, Carbohydrates_max,
                    Protein_min, Protein_max,
                    Fat_min, Fat_max,
                    Dietary_Fiber_min, Dietary_Fiber_max,
                    Sodium_min, Sodium_max
                FROM recommended_nutrition
                WHERE customer_id = %s
            """, (customer_id,))
            recommended = cursor.fetchone()
            
            cursor.close()
            return recommended
            
        except mysql.connector.Error as err:
            print("Database error:", str(err))
            return None

    def record_food_consumption(self, customer_id, food_id):
        """
        Record food consumption in the database with KST (Korea Standard Time)
        """
        if not self.connection:
            print("No database connection.")
            return False

        try:
            cursor = self.connection.cursor()
            
            # Get current time in KST
            kst = pytz.timezone('Asia/Seoul')
            now = datetime.now(kst)
            
            # Insert consumption record with KST
            cursor.execute("""
                INSERT INTO consumption (customer_id, food_id, time, date)
                VALUES (%s, %s, %s, %s)
            """, (customer_id, food_id, now, now.date()))
            
            self.connection.commit()
            cursor.close()
            return True
            
        except mysql.connector.Error as err:
            print(f"Error recording food consumption: {str(err)}")
            return False
         
    def get_today_consumption_by_patient(self, customer_code):
        """
        Retrieve the customer_id by customer code and return today's consumption records.
        For a customer code retrieve its customer_id and today's consumption records.
        """
        if not self.connection:
            print("No database connection.")
            return False

        try:
            cursor = self.connection.cursor(dictionary=True)

            # Retrieve the customer_id from the customer table that matches the customer code
            query_customer = """
                SELECT customer_id
                FROM customer
                WHERE SUBSTRING_INDEX(code, '-', 1) = %s
            """
            cursor.execute(query_customer, (customer_code,))
            customer = cursor.fetchone()

            if not customer:
                return None, "해당 환자코드를 가진 고객을 찾을 수 없습니다.", None

            customer_id = customer['customer_id']
            
            # In the consumption table retrieve records from the time column where the customer_id matches and the date is today
            query_consumption = """
                SELECT time
                FROM consumption
                WHERE customer_id = %s AND DATE(time) = CURDATE()
            """

            cursor.execute(query_consumption, (customer_id,))
            consumption_records = cursor.fetchall()

            cursor.close()
            return consumption_records

        except mysql.connector.Error as err:
            print(f"MySQL 에러: {str(err)}")
            return False