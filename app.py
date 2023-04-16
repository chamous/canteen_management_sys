from flask import Flask, render_template, request, flash, jsonify
from flask import redirect, url_for, session, make_response, abort
from database import cnx, create_tables, add_meal, get_meals, check_order_limit
from database import add_order, get_orders, get_next_id, add_user, delete_meal_by_id
import secrets
import csv
import serial
import io
HOST_NAME = 'localhost'
HOST_PORT = 5000
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
with app.test_client() as client:
    with client.session_transaction() as _:
        _['key'] = app.secret_key
# render HOME pageclear


@app.route("/")
def home():
    return render_template("home.html")


def authenticate(username, password):
    cursor = cnx.cursor()
    cursor.execute("SELECT * FROM users "
                    "WHERE username = %s "
                    "AND password = %s", (username, password))
    user = cursor.fetchone()
    cursor.close()
    if user:
        return True
    else:
        return False
# render login page


@app.route("/login", methods=["GET", "POST"])
def login():
    cursor = cnx.cursor()
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
    return render_template("add_meal.html", error=error)


@app.route("/delete_meal/<int:id>", methods=["DELETE"])
def delete_meal(id):
    if delete_meal_by_id(id):
        flash("Meal deleted successfully", "success")
    else:
        flash("Failed to delete meal", "danger")
    return jsonify({"success": True})


# render GET_MEAL page


@app.route("/meals", methods=["GET", "POST"])
def get_mealPage():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    meals = get_meals()
    return render_template("meals.html", meals=meals)

# render GET_ORDER page


@app.route("/orders", methods=["GET", "POST"])
def OrderPage():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    meals = get_meals()
    orders = get_orders()
    return render_template("orders.html", meals=meals, orders=orders)


# render DASGBOARD page


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
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
        meals_id = request.form["meals_id"]

        # Check if the user has already placed an order
        if check_order_limit(name):
            error = "You have already placed an order in this shift"
        else:
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
    rows = [(
        order["orders_id"], order["name"], order["hr_id"],
        order["meals_id"], order["order_time"])
        for order in orders]
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
    rows = [(
        order["orders_id"], order["name"], order["hr_id"],
        order["meals_id"], order["order_time"])
        for order in orders]
    csv_data = io.StringIO()
    writer = csv.writer(csv_data)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    response = make_response(csv_data.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=orders.csv"
    response.headers["Content-type"] = "text/csv"
    return response


@app.route("/add_user", methods=["GET", "POST"])
def add_user_page():
    if session.get("username") != "superadmin":
        abort(401)

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        add_user(username, password)
        return redirect(url_for("user_list"))
    else:
        return render_template("add_user.html")


@app.route('/user_list')
def user_list():
    if session.get("username") != "superadmin":
        abort(401)

    cursor = cnx.cursor()
    cursor.execute('SELECT * FROM users')
    rows = cursor.fetchall()
    cursor.close()

    users = []
    for row in rows:
        user = {
            'id': row[0],
            'name': row[1],
            'password': row[2]
        }
        users.append(user)

    message = ''
    if not users:
        message = 'There are no users to display'

    return render_template('user_manager.html', users=users, message=message)


@app.route('/update_user/<int:user_id>', methods=['POST'])
def update_user(user_id):
    if session.get("username") != "superadmin":
        abort(401)

    cursor = cnx.cursor()

    if 'password' in request.form:
        # Update password
        new_password = request.form.get('password')
        update_password_query = "UPDATE users SET password=%s WHERE id=%s"
        cursor.execute(update_password_query, (new_password, user_id))

    if 'new_username' in request.form:
        # Update username
        new_username = request.form.get('new_username')
        update_username_query = "UPDATE users SET username=%s WHERE id=%s"
        cursor.execute(update_username_query, (new_username, user_id))

    cnx.commit()
    cursor.close()

    return redirect(url_for('user_list'))


@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if session.get("username") != "superadmin":
        abort(401)

    cursor = cnx.cursor()
    cursor.execute('DELETE FROM users WHERE id=%s', (user_id,))
    cnx.commit()
    cursor.close()

    return redirect(url_for('user_list'))


def print_order(order):
    order = ("name", "hr_id", "meals_id")
    # Connect to the printer using serial communication
    ser = serial.Serial('COM1', baudrate=9600, timeout=1)
    ser.write(b'\x1b\x40')  # Initialize the printer

    # Set the label format and position
    ser.write(b'\x1b\x69\x01\x01')  # Set label format to 1x1 inch
    ser.write(b'\x1b\x6c\x08')  # Set label position to 8 mm from the top

    # Print the order details on the label
    # Set font size to double-height and double-width
    ser.write(b'\x1b\x21\x10')
    # Print the order details on separate lines
    ser.write(b'\n'.join([f.encode() for f in order]))

    # Finish and disconnect the printer
    ser.write(b'\x1b\x45')  # Turn on the cutter
    ser.write(b'\x1b\x66\x00')  # Cut the label
    ser.close()


if __name__ == "__main__":
    create_tables()
    app.run(host=HOST_NAME, port=HOST_PORT, debug=True)
