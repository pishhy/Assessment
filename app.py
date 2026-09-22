from flask import Flask, g, render_template, request, redirect, url_for, flash, session  # request reads form data, redirect/url_for send the browser to another route, flash queues a one-time message, session stores the logged-in user's id
import sqlite3  # lets Python talk to the SQLite database file
from werkzeug.security import generate_password_hash, check_password_hash  # turns a plain password into a scrambled hash, and checks a plain password against a stored hash


DATABASE = 'Database/REAL_ASSESSMENT.db'


app = Flask(__name__)
app.secret_key = 'hiiiiiiiiii'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/menu')
def menu():
    sql = "SELECT burgers, price, ingredients, condiments, photo FROM products WHERE burgers IS NOT NULL AND burgers != ''"
    results = query_db(sql)
    return render_template("menus.html", results=results)


@app.route('/sides')
def sides():
    drinks = query_db("SELECT sides, price, photo FROM sides WHERE description='drink'")
    sauces = query_db("SELECT sides, price, photo FROM sides WHERE description='sauce'")
    food_sides = query_db("SELECT sides, price, photo FROM sides WHERE description='side'")
    return render_template("sides.html", drinks=drinks, sauces=sauces, food_sides=food_sides)




@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('logout'))

    if request.method == 'POST': 
        username = request.form['username'] 
        password = request.form['password'] 
        user_row = query_db("SELECT * FROM user WHERE name = ?", [username], one=True)  # looks up a row in the "user" table whose "name" matches what was typed
        if user_row is None:  # no account exists with that username
            flash("We couldn't find that account, please sign up first.")  # queues a message explaining why they're being redirected
            return redirect(url_for('signup'))  # sends them to the signup page to create an account
        user = dict(user_row)  # converts the sqlite3.Row into a plain dict so the key lookups below type-check cleanly
        if not check_password_hash(user['password'], password):  # compares the typed password against the hashed password stored in the database
            flash("Incorrect password, please try again.")  # queues an error message
            return redirect(url_for('login'))  # reloads the login page so they can retry
        session['user_id'] = user['id']  # remembers which user is logged in for future requests
        session['username'] = user['name']  # stores the username too, so it can be shown elsewhere without another query
        flash(f"Welcome back, {user['name']}!")  # queues a friendly success message
        return redirect(url_for('home'))  # sends the now-logged-in user to the homepage
    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        session.clear()  # Clears session ONLY when the button is clicked
        flash("You have been logged out.")
        return redirect(url_for('home'))
    # GET request: shows a confirmation page with the button
    return render_template('logout.html')

@app.route('/cart')
def cart():
    return render_template('cart.html')


@app.route('/signup', methods=['GET', 'POST']) 
def signup():
    if request.method == 'POST':
        username = request.form['username']  
        password = request.form['password'] 
        address = request.form['address']

        existing_user = query_db("SELECT id FROM user WHERE name = ?", [username], one=True)  # checks whether that username is already taken
        if existing_user is not None:  # someone already signed up with this username
            flash("That username is already registered, please log in instead.")  # explains why they're being redirected
            return redirect(url_for('login'))  # sends them to the login page instead of creating a duplicate
        
        hashed_password = generate_password_hash(password)  # scrambles the password so the raw text is never stored in the database
        max_id_row = query_db("SELECT MAX(id) AS max_id FROM user", one=True)  # finds the current highest id (the "user" table's id column doesn't auto-increment on its own); this always returns a row, even on an empty table
        next_id_row = dict(max_id_row) if max_id_row is not None else {}  # converts the row to a dict for clean key lookups, falling back to an empty dict just in case
        next_id = (next_id_row.get('max_id') or 0) + 1  # picks the next id, starting at 1 if the table is empty
        db = get_db()  # grabs the current database connection
        db.execute(
            "INSERT INTO user (id, name, address, password) VALUES (?, ?, ?, ?)",  # adds a new row to the "user" table, including the id we just generated
            [next_id, username, address, hashed_password]
        )
        db.commit()  # saves the new row permanently to the database file
        flash("Account created! You can now log in.")  # queues a success message
        return redirect(url_for('login'))  # sends the new user to the login page to sign in with their new details

    return render_template('signup.html')  # GET request: just show the signup form


@app.errorhandler(404)
def page_not_found(error):
    ''' # Custom error handling for page not found errors'''
    return render_template('error.html', error=str(error)), 404




@app.errorhandler(500)
def internal_server_error(error):
    ''' # Custom error handling for internal server errors'''
    return render_template('error.html', error=str(error)), 500




@app.errorhandler(Exception)
def unexpected_error(error):
    ''' # Custom error handling for other unexpected errors'''
    return render_template('error.html', error=str(error)), 500


if __name__ == "__main__":
    app.run(debug=True)