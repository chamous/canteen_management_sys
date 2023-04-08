from flask import Flask, render_template, request, redirect, url_for, session, make_response, send_file,abort
import mysql.connector
import datetime
import io
import secrets
from io import StringIO
import csv
import serial

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
with app.test_client() as client:
    with client.session_transaction() as session:
        session['key'] = app.secret_key

HOST_NAME = 'localhost'
HOST_PORT = 5000
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
    cnx.commit()



def add_meal(meals_id, name, description, price, image):
    cursor = cnx.cursor()
    meals_id = get_next_id(cursor, "meals")
    filename = f"static/images/{meals_id}.jpg"
    image.save(filename)
    # insert meal data into the database
    add_meal_query = "INSERT INTO meals (meals_id, name, description, price, image) VALUES (%s, %s, %s, %s, %s)"
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

def add_order(name, hr_id, meals_id):
    if check_order_limit(name):
        return False
    cursor = cnx.cursor()
    orders_id = get_next_id(cursor, "orders")
    # insert order data into the database
    add_order_query = "INSERT INTO orders (orders_id, name, hr_id, meals_id, order_time) VALUES (%s, %s, %s, %s, NOW())"
    order_data = (orders_id, name, hr_id, meals_id)
    cursor.execute(add_order_query, order_data)
    cnx.commit()
    return True

def get_orders():
    cursor = cnx.cursor(dictionary=True)
    # retrieve all orders from the database
    query = "SELECT * FROM orders"
    cursor.execute(query)
    orders = cursor.fetchall()
    return orders

# Here we check the order time then we check its shift
def check_order_limit(name):
    current_time = datetime.datetime.now()
    shift_starts = [
        current_time.replace(hour=23, minute=0, second=0, microsecond=0),
        current_time.replace(hour=7, minute=0, second=0, microsecond=0),
        current_time.replace(hour=15, minute=0, second=0, microsecond=0)
    ]
    shift_ends = [
        current_time.replace(hour=7, minute=0, second=0, microsecond=0),
        current_time.replace(hour=15, minute=0, second=0, microsecond=0),
        current_time.replace(hour=23, minute=0, second=0, microsecond=0)
    ]
    cursor = cnx.cursor()
    order_limit = 1  # maximum number of orders allowed per shift
    for i in range(3):
        shift_start = shift_starts[i]
        shift_end = shift_ends[i]
        # count the number of orders placed by the user within the current shift
        query = "SELECT COUNT(*) FROM orders WHERE name = %s AND order_time >= %s AND order_time < %s"
        time_data = (name, shift_start, shift_end)
        cursor.execute(query, time_data)
        result = cursor.fetchone()
        if result[0] >= order_limit:
            return True
    return False



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



def authenticate(username, password):
    cursor = cnx.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
    user = cursor.fetchone()
    cursor.close()
    if user:
        return True
    else:
        return False



#render HOME page
@app.route("/")
def home():
    return render_template("home.html")


# render LOGIN page


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Connect to the MySQL database
        cursor = cnx.cursor()

        # Retrieve the user's data from the MySQL table
        query = "SELECT * FROM users WHERE username = %s"
        cursor.execute(query, (username,))
        user_data = cursor.fetchone()

        if user_data is not None and password == user_data[2]:
            session["logged_in"] = True
            session["username"] = username

            # Check if the user is superadmin and redirect to dashboard
            if username == "superadmin":
                return redirect(url_for("dashboard"))

            return redirect(url_for("add_mealPage"))
        else:
            error = "Invalid username or password"

        # Close the database connection
        cursor.close()
        cnx.close()

    return render_template("login.html", error=error)



@app.route("/log_out", methods=["GET"])
def log_out():
    session.pop("logged_in", None)
    session.pop("username", None)
    return redirect(url_for("login"))

# render add_meal page
@app.route("/add_meal", methods=["GET", "POST"])
def add_mealPage():
    cursor = cnx.cursor()
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    if request.method == "POST":
        meals_id = get_next_id(cnx.cursor(), "meals")
        name = request.form["name"]
        description = request.form["description"]
        price = request.form["price"]
        image = request.files["image"]
        if add_meal(meals_id, name, description, price, image):
            return redirect(url_for("dashboard"))
        else:
            error = "Failed to add meal"
    else:
        error = None
    return render_template("add_meal.html")

 # render GET_MEAL page
@app.route("/meals", methods=['GET', 'POST'])
def get_mealPage():
    cursor = cnx.cursor()
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    meals = get_meals()
    return render_template("meals.html", meals=meals)

# render GET_ORDER page
@app.route("/orders", methods=["GET", "POST"])
def OrderPage():
    cursor = cnx.cursor()
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    meals = get_meals()
    orders = get_orders()
    return render_template("orders.html", meals=meals, orders=orders)

# render DASGBOARD page
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    cursor = cnx.cursor()
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    # Check if the logged in user is 'superadmin'
    username = session.get("username")
    if username != 'superadmin':
        return abort(403)

    meals = get_meals()
    orders = get_orders()
    return render_template("dashboard.html", meals=meals, orders=orders)


@app.route("/order", methods=["GET", "POST"])
def order():
    if request.method == "POST":
        name = request.form["name"]
        hr_id = request.form["hr_id"]
        meals_id = get_next_id(cnx.cursor(), "meals")
        if add_order(name, hr_id, meals_id):

            return redirect(url_for("order"))
        else:
            error = "Failed to place order"
    else:
        error = None

    meals = get_meals()
    return render_template("order.html", meals=meals, error=error)

@app.route("/download-orders")
def download_orders():
    orders = get_orders()
    headers = ["Order ID", "Name", "HR ID", "Meal ID", "Order Time"]
    rows = [(order["orders_id"], order["name"], order["hr_id"], order["meals_id"], order["order_time"]) for order in orders]
    csv_data = io.StringIO()
    writer = csv.writer(csv_data)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    response = make_response(csv_data.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=orders.csv"
    response.headers["Content-type"] = "text/csv"
    return response

@app.route('/download_csv')
def download_csv():
    orders = get_orders()
    headers = ["Order ID", "Name", "HR ID", "Meal ID", "Order Time"]
    rows = [(order["orders_id"], order["name"], order["hr_id"], order["meals_id"], order["order_time"]) for order in orders]
    csv_data = io.StringIO()
    writer = csv.writer(csv_data)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    response = make_response(csv_data.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=orders.csv"
    response.headers["Content-type"] = "text/csv"
    return response



def print_order(order):
    # Connect to the printer using serial communication
    ser = serial.Serial('COM1', baudrate=9600, timeout=1)
    ser.write(b'\x1b\x40') # Initialize the printer

    # Set the label format and position
    ser.write(b'\x1b\x69\x01\x01') # Set label format to 1x1 inch
    ser.write(b'\x1b\x6c\x08') # Set label position to 8 mm from the top

    # Print the order details on the label
    ser.write(b'\x1b\x21\x10') # Set font size to double-height and double-width
    ser.write(b'\n'.join([f.encode() for f in order])) # Print the order details on separate lines

    # Finish and disconnect the printer
    ser.write(b'\x1b\x45') # Turn on the cutter
    ser.write(b'\x1b\x66\x00') # Cut the label
    ser.close()


if __name__ == "__main__":
    create_tables()
    app.run(host=HOST_NAME, port=HOST_PORT, debug=True)
