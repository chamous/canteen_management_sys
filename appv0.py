from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import datetime

app = Flask(__name__)
app.secret_key = "your-secret-key"
with app.test_client() as client:
    with client.session_transaction() as session:
        session['key'] = 'your-secret-key'

HOST_NAME = 'localhost'
HOST_PORT = 5000
HOST = 'localhost'
PORT = 3306
USER ='root'
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
    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meals (
            meal_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description VARCHAR(255) NOT NULL,
            price FLOAT NOT NULL,
            image VARCHAR(255) NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            hr_id VARCHAR(255) NOT NULL,
            meal_id INT NOT NULL,
            order_time DATETIME NOT NULL,
            FOREIGN KEY (meal_id) REFERENCES meals(meal_id)
        )
    """)
    conn.commit()
    conn.close()

def add_meal(ame, description, price, image):
    meal_id = get_next_id("meals")
    filename = f"static/images/{meal_id}.jpg"
    image.save(filename)
    # insert meal data into the database
    add_meal_query = "INSERT INTO meals (name, description, price, image) VALUES (%s, %s, %s, %s, %s)"
    meal_data = (meal_id, name, description, price, filename)
    cursor.execute(add_meal_query, meal_data)
    cnx.commit()
    return meal_id


def get_meals():
    cursor = cnx.cursor(dictionary=True)
    # retrieve all meals from the database
    query = "SELECT * FROM meals"
    cursor.execute(query)
    meals = cursor.fetchall()
    return meals

def add_order(name, hr_id, meal_id):
    if check_order_limit(name):
        return False
    cursor = cnx.cursor()
    order_id = get_next_id(cursor, "orders")
    # insert order data into the database
    add_order_query = "INSERT INTO orders (id, name, hr_id, meal_id) VALUES (%s, %s, %s, %s)"
    order_data = (id, name, hr_id, meal_id)
    cursor.execute(add_order_query, order_data)
    cnx.commit()
    return

def get_orders():
    cursor = cnx.cursor(dictionary=True)
    # retrieve all orders from the database
    query = "SELECT * FROM orders"
    cursor.execute(query)
    orders = cursor.fetchall()
    return orders

def check_order_limit(name):
    current_time = datetime.datetime.now()
    shift_start = current_time.replace(hour=8, minute=0, second=0, microsecond=0)
    shift_end = current_time.replace(hour=16, minute=0, second=0, microsecond=0)
    cursor = cnx.cursor()
    # check if the user has already placed an order within the current shift
    query = "SELECT * FROM orders WHERE name = %s AND order_time >= %s AND order_time < %s"
    time_data = (name, shift_start, shift_end)
    cursor.execute(query, time_data)
    result = cursor.fetchone()
    if result is not None:
        return True
    return False

def get_next_id(cursor, table_name):
    # retrieve the last id used in the specified table
    query = f"SELECT MAX(id) FROM {table_name}"
    cursor.execute(query)
    last_id = cursor.fetchone()[0]
    if last_id is None:
        return 1
    return last_id + 1

def authenticate(username, password):
    # replace with your authentication logic
    return username == "admin" and password == "password"
    return
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if authenticate(username, password):
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid username or password"
    return render_template("login.html", error=error)

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        meal_id = get_next_id("meals")
        name = request.form["name"]
        description = request.form["description"]
        price = request.form["price"]
        image = request.files["image"]
        if add_meal(meal_id, name, description, price, image):
            return redirect(url_for("dashboard"))
        else:
            error = "Failed to add meal"
    else:
        error = None

    meals = get_meals()
    orders = get_orders()
    return render_template("dashboard.html", meals=meals, orders=orders, error=error)

@app.route("/order", methods=["GET", "POST"])
def order():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form["name"]
        hr_id = request.form["hr_id"]
        meal_id = request.form["meal"]
        if add_order(name, hr_id, meal_id):
            return redirect(url_for("order"))
        else:
            error = "Failed to place order"
    else:
        error = None

    meals = get_meals()
    return render_template("order.html", meals=meals, error=error)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')