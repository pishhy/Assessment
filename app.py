"""Evan burgers flask application for burgers"""
import sqlite3
from functools import wraps
from flask import Flask, g, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash



DATABASE = 'Database/REAL_ASSESSMENT.db'


app = Flask(__name__)
app.secret_key = 'hiiiiiiiiii'


def get_db():
    ''' Opens database connection'''
    # checks if a connection was already opened on this request
    db = getattr(g, '_database', None)
    # no connection yet this request
    if db is None:
        #store it on "g" so the rest of this request can reuse it
        db = g._database = sqlite3.connect(DATABASE)
        #lets query results be read like dictionaries (row['column']) instead of plain tuples
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(_):
    '''closes the database connection that was opened'''
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()  # closes the connection so it doesn't stay open after the request finishes


def query_db(query, args=(), one=False):
    '''handles all the queries that happens on the website'''
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def next_id(table):  # these tables don't auto-increment
    '''finds highest existing id in a database table and returns the next available number.'''
    row = query_db(f"SELECT MAX(id) AS max_id FROM {table}", one=True)
    row = dict(row) if row is not None else {}
    return (row.get('max_id') or 0) + 1


def login_required(view):  #put @login_required above route that needs session['user_id'] to exist
    '''this makes it easier for a page needed to be in session to navigate'''
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if 'user_id' not in session:  # nobody logged in this session
            flash("Please log in first.")
            return redirect(url_for('login'))  # send them to login
        return view(*args, **kwargs)
    return wrapped_view


@app.route('/')
def home():
    '''The function for the home page'''
    return render_template('home.html')  # just shows the homepage, no data needed

#route to show the menu page, which includes all the burgers
@app.route('/menu')
def menu():
    '''burgers option for menu option'''
    sql = """SELECT id, burgers, price, ingredients, condiments, photo
        FROM products WHERE burgers IS NOT NULL AND burgers != ''"""
    results = query_db(sql)
    return render_template("menus.html", results=results)

#route to show the sides page, which includes drinks, sauces, and food sides
@app.route('/sides')
def sides():
    """sides/drink/sauces option for the sides menu"""
    drinks = query_db("SELECT id, sides, price, photo FROM sides WHERE description='drink'")
    sauces = query_db("SELECT id, sides, price, photo FROM sides WHERE description='sauce'")
    food_sides = query_db("SELECT id, sides, price, photo FROM sides WHERE description='side'")
    return render_template("sides.html", drinks=drinks, sauces=sauces, food_sides=food_sides)



@app.route('/login', methods=['GET', 'POST'])
def login():
    '''Login function that handles what happens on the log in page'''
    if 'user_id' in session:
        return redirect(url_for('logout'))

    if request.method == 'POST':
        username = request.form['username']  # value typed into the "username" input
        password = request.form['password']  # value typed into the "password" input
        user_row = query_db("SELECT * FROM user WHERE name = ?", [username], one=True)
        if user_row is None:  # no account exists with that username
            flash("We couldn't find that account, please sign up first.")
            return redirect(url_for('signup'))
        user = dict(user_row)
        if not check_password_hash(user['password'], password):
            flash("Incorrect password, please try again.")  # queues an error message
            return redirect(url_for('login'))  # reloads the login page so they can retry
        session['user_id'] = user['id']  # remembers which user is logged in for future requests
        session['username'] = user['name']
        flash(f"Welcome back, {user['name']}!")  # queues a friendly success message
        return redirect(url_for('home'))
    return render_template('login.html')

#route to log out the current user, clearing the session
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    '''logout function that clear the user in session'''
    if request.method == 'POST':
        session.clear()  # Clears session ONLY when the button is clicked
        flash("You have been logged out.")
        return redirect(url_for('home'))
    # GET request: shows a confirmation page with the button
    return render_template('logout.html')


# route to add a burger to the cart
@app.route('/add_to_cart/burger/<int:product_id>', methods=['POST'])
@login_required
def add_burger_to_cart(product_id):
    '''function that allows the add now button on the burger menu page to be interacted'''
    quantity = int(request.form.get('quantity', 1))

    db = get_db()

    burger_ordered_id = next_id('burger_ordered')
    db.execute(
        "INSERT INTO burger_ordered (id, products_id, burger_quantity) VALUES (?, ?, ?)",
        [burger_ordered_id, product_id, quantity]
    )

    order_id = next_id('Customer_order')
    db.execute(
        """INSERT INTO Customer_order (id, burger_ordered_id, sides_ordered_id, user_id)
        VALUES (?, ?, ?, ?)""",
        [order_id, burger_ordered_id, None, session['user_id']]
    )
    db.commit()

    flash("Added to your cart!")
    # go back to whichever page the "Add Now" button was pressed on, instead of jumping to /cart
    return redirect(request.referrer or url_for('menu'))

# route to add a side (drink, sauce, or food side) to the cart
@app.route('/add_to_cart/side/<int:side_id>', methods=['POST'])
@login_required
def add_side_to_cart(side_id):
    '''function that allows the add now button on the side page to be called'''
    quantity = int(request.form.get('quantity', 1))

    db = get_db()

    sides_ordered_id = next_id('sides_ordered')  # this row represents "this side, this quantity"
    db.execute(
        "INSERT INTO sides_ordered (id, sides_id, burger_quantity) VALUES (?, ?, ?)",
        [sides_ordered_id, side_id, quantity]
    )

    order_id = next_id('Customer_order')
    db.execute(
        """INSERT INTO Customer_order (id, burger_ordered_id, sides_ordered_id, user_id) 
        VALUES (?, ?, ?, ?)""",
        [order_id, None, sides_ordered_id, session['user_id']]
    )
    db.commit()

    flash("Added to your cart!")
    # go back to whichever page the "Add Now" button was pressed on, instead of jumping to /cart
    return redirect(request.referrer or url_for('sides'))

#cart route: shows the logged-in user's current cart contents, with a running total of the order
@app.route('/cart')
@login_required
def cart():
    '''a function that will allow the added products to be put on the cart page'''
    sql = """
        SELECT
            Customer_order.id AS order_id,
            products.burgers AS burger_name,
            products.price AS burger_price,
            products.photo AS burger_photo,
            burger_ordered.burger_quantity AS burger_quantity,
            sides.sides AS side_name,
            sides.price AS side_price,
            sides.photo AS side_photo,
            sides_ordered.burger_quantity AS side_quantity
        FROM Customer_order
        LEFT JOIN burger_ordered ON Customer_order.burger_ordered_id = burger_ordered.id
        LEFT JOIN products ON burger_ordered.products_id = products.id
        LEFT JOIN sides_ordered ON Customer_order.sides_ordered_id = sides_ordered.id
        LEFT JOIN sides ON sides_ordered.sides_id = sides.id
        WHERE Customer_order.user_id = ?
        ORDER BY Customer_order.id
    """
    order_items = query_db(sql, [session['user_id']]) or []

    total = 0  # running total of the whole order, in dollars
    for row in order_items:
        if row['burger_price'] is not None:  # this row is a burger line
            # burger prices are stored as text like "$6.99" in this database
            burger_price = float(str(row['burger_price']).replace('$', ''))
            total += burger_price * row['burger_quantity']
        if row['side_price'] is not None:  # this row is a side line
            total += row['side_price'] * row['side_quantity']

    return render_template('cart.html', order_items=order_items, total=total)



# route to remove a single item from the cart
@app.route('/remove_from_cart/<int:order_id>', methods=['POST'])
@login_required
def remove_from_cart(order_id):
    '''a function that allows user to remove their products'''
    db = get_db()
    # the "AND user_id = ?" check matters here: without it, anyone could remove items from
    # someone else's cart just by guessing/changing the order_id in the request
    db.execute(
        "DELETE FROM Customer_order WHERE id = ? AND user_id = ?",
        [order_id, session['user_id']]
    )
    db.commit()

    flash("Item removed from your cart.")
    return redirect(url_for('cart'))

#a route to submit the order and clear the cart
@app.route('/submit_order', methods=['POST'])
@login_required
def submit_order():
    '''function that allows user to submit their order and clear the whole cart'''
    db = get_db()
    # removes every Customer_order row for this user — since the cart page is built entirely
    # from Customer_order, this is what actually empties the cart
    db.execute("DELETE FROM Customer_order WHERE user_id = ?", [session['user_id']])
    db.commit()

    flash("Order submitted!")
    return redirect(url_for('cart'))  # sends them back to the now-empty cart


#signup route: creates a new user account in the database
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    '''function that gives user a for to sign up'''
    if request.method == 'POST':
        username = request.form['username']  # value typed into the "username" input
        password = request.form['password']  # value typed into the "password" input
        address = request.form['address']  # value typed into the "address" input

        existing_user = query_db("SELECT id FROM user WHERE name = ?", [username], one=True)
        if existing_user is not None:  # someone already signed up with this username
            flash("That username is already registered, please log in instead.")
            return redirect(url_for('login'))
        hashed_password = generate_password_hash(password)  # scrambles the password
        new_user_id = next_id('user')
        db = get_db()  # grabs the current database connection
        db.execute(
            "INSERT INTO user (id, name, address, password) VALUES (?, ?, ?, ?)", 
            [new_user_id, username, address, hashed_password]
        )
        db.commit()  # saves the new row permanently to the database file
        flash("Account created! You can now log in.")  # queues a success message
        return redirect(url_for('login'))  # sends the new user to the login page

    return render_template('signup.html')  # GET request: just show the signup form

#handles 404 page not found errors
@app.errorhandler(404)
def page_not_found(error):
    ''' # Custom error handling for page not found errors'''
    return render_template('error.html', error=str(error)), 404



#handles 500 internal server errors
@app.errorhandler(500)
def internal_server_error(error):
    ''' # Custom error handling for internal server errors'''
    return render_template('error.html', error=str(error)), 500



#handles other unexpected errors
@app.errorhandler(Exception)
def unexpected_error(error):
    ''' # Custom error handling for other unexpected errors'''
    return render_template('error.html', error=str(error)), 500


if __name__ == "__main__":
    app.run(debug=True)
