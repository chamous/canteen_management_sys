import mysql.connector
import datetime
import os

HOST = 'localhost'
PORT = 3306
USER = 'root'
PASSWORD = ''
DATABASE = 'canteen'

# Connect to the MySQL database
cnx = mysql.connector.connect(
    host=HOST,
    port=PORT,
    user=USER,
    password=PASSWORD,
    database=DATABASE
)


def create_tables():
    cursor = cnx.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meals (
            meals_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description VARCHAR(255) NOT NULL,
            price FLOAT NOT NULL,
            image VARCHAR(255) NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            orders_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            hr_id VARCHAR(255) NOT NULL,
            meals_id INT NOT NULL,
            order_time DATETIME NOT NULL,
            FOREIGN KEY (meals_id) REFERENCES meals(meals_id)
        )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL,
        password TEXT NOT NULL
        )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        role_id INTEGER AUTO_INCREMENT PRIMARY KEY NOT NULL,
        role_name TEXT NOT NULL
        )
    """)
    cnx.commit()


def add_meal(meals_id, name, description, price, image):
    cursor = cnx.cursor()
    meals_id = get_next_id(cursor, "meals")
    filename = f"static/images/{meals_id}.jpg"
    image.save(filename)
    # insert meal data into the database
    add_meal_query = (
        "INSERT INTO meals (meals_id, name, description, price, image) "
        "VALUES (%s, %s, %s, %s, %s)")
    meal_data = (meals_id, name, description, price, filename)
    cursor.execute(add_meal_query, meal_data)
    cnx.commit()
    return meals_id


def get_meals():
    cursor = cnx.cursor(dictionary=True)
    # retrieve all meals from the database
    query = "SELECT * FROM meals"
    cursor.execute(query)
    meals = cursor.fetchall()
    return meals


# Here we check the order time then we check its shift


def check_order_limit(name):
    current_time = datetime.datetime.now()
    shift_starts = [
        current_time.replace(hour=7, minute=0, second=0, microsecond=0),
        current_time.replace(hour=15, minute=0, second=0, microsecond=0),
        current_time.replace(hour=23, minute=0, second=0, microsecond=0)
    ]
    shift_ends = [
        current_time.replace(hour=14, minute=59, second=59, microsecond=999),
        current_time.replace(hour=22, minute=59, second=59, microsecond=999),
        current_time.replace(hour=6, minute=59, second=59, microsecond=999)
        + datetime.timedelta(days=1)
    ]
    cursor = cnx.cursor()
    order_limit = 1
    for i in range(3):
        shift_start = shift_starts[i]
        shift_end = shift_ends[i]
        if shift_start <= current_time <= shift_end:
            query = (
                "SELECT COUNT(*) FROM orders "
                "WHERE name = %s "
                "AND order_time >= %s "
                "AND order_time <= %s")
            time_data = (name, shift_start, shift_end)
            cursor.execute(query, time_data)
            result = cursor.fetchone()
            if result[0] >= order_limit:
                return True
    return False



def add_order(name, hr_id, meals_id):
    cursor = cnx.cursor()

    # Check if the user has already placed an order during the current shift
    if check_order_limit(name):
        return False

    # Add the order to the database
    query = "INSERT INTO orders (name, hr_id, meals_id, order_time) VALUES (%s, %s, %s, %s)"
    data = (name, hr_id, meals_id, datetime.datetime.now())
    cursor.execute(query, data)
    cnx.commit()

    cursor.close()
    return True




def delete_meal_by_id(meals_id):
    try:
        # Delete meal from meals table
        cursor = cnx.cursor()
        delete_meal_query = "DELETE FROM meals WHERE meals_id = %s"
        cursor.execute(delete_meal_query, (meals_id,))
        cnx.commit()

        # Delete meal image from server
        meal = get_meals(id)
        if meal is not None:
            os.remove(meal.image_path)

        # Close database connection
        cnx.close()

        return True
    except Exception as e:
        print("Failed to delete meal:", e)
        return False


def get_orders(name=None):
    cursor = cnx.cursor(dictionary=True)
    if name:
        query = "SELECT * FROM orders WHERE name = %s"
        cursor.execute(query, (name,))
    else:
        query = "SELECT * FROM orders ORDER BY order_time DESC LIMIT 10"
        cursor.execute(query)
    orders = cursor.fetchall()
    cursor.close()
    return orders


def get_next_id(cursor, table_name):
    # retrieve the last id used in the specified table
    if table_name == "meals":
        column_name = "meals_id"
    elif table_name == "orders":
        column_name = "orders_id"
    else:
        raise ValueError(f"Invalid table name: {table_name}")
    query = f"SELECT MAX({column_name}) FROM {table_name}"
    cursor.execute(query)
    last_id = cursor.fetchone()[0]
    if last_id is None:
        # if there are no entries in the table, start the id at 1
        next_id = 1
    else:
        # otherwise, increment the last id by 1 to get the next id
        next_id = last_id + 1
    return next_id


def add_user(username, password):
    cursor = cnx.cursor()
    add_user_query = "INSERT INTO users (username, password) VALUES (%s, %s)"
    user_data = (username, password)
    cursor.execute(add_user_query, user_data)
    cnx.commit()
    cursor.close()
