import mysql.connector
from datetime import datetime, timedelta

class DatabaseClient:
    def __init__(self, host, user, password, database):
        """
        Initialize the database client with connection parameters.
        """
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = None

    def connect(self):
        """
        Establish a connection to the MySQL database.
        """
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
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
            cursor.execute("""
                SELECT c.date,
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
                SELECT Energy_min, Energy_max,
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
            
            # Format recommended nutrition data
            recommended_nutrition = {
                'calories': {'min': recommended['Energy_min'], 'max': recommended['Energy_max']},
                'carbohydrates': {'min': recommended['Carbohydrates_min'], 'max': recommended['Carbohydrates_max']},
                'protein': {'min': recommended['Protein_min'], 'max': recommended['Protein_max']},
                'fat': {'min': recommended['Fat_min'], 'max': recommended['Fat_max']},
                'fiber': {'min': recommended['Dietary_Fiber_min'], 'max': recommended['Dietary_Fiber_max']},
                'sodium': {'min': recommended['Sodium_min'], 'max': recommended['Sodium_max']}
            }
            
            return {
                'recent_nutrition': recent_nutrition,
                'recommended_nutrition': recommended_nutrition
            }
            
        except mysql.connector.Error as err:
            print("Database error:", str(err))
            return None

    def get_food_info_from_db(self, food_name):
        """
        Query the nutrition database for food information based on the food name.
        Also includes timestamp of when the food was consumed (created_at).
        """
        if not self.connection:
            print("No database connection.")
            return None

        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Query for food information and created_at as consumption time
            cursor.execute("""
                SELECT n.*, cd.created_at as consumption_time 
                FROM nutrition_info n 
                LEFT JOIN customer_diets cd ON n.food_name = cd.food_name 
                WHERE n.food_name = %s
                ORDER BY cd.created_at DESC LIMIT 1
            """, (food_name,))
            food_info = cursor.fetchone()
            
            cursor.close()
            return food_info
            
        except mysql.connector.Error as err:
            print("Database error:", str(err))
            return None
