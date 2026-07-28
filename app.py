from flask import Flask, g, render_template
import sqlite3

DATABASE = 'Database/actuallls.db'

app = Flask(__name__)

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
    sql = """SELECT burgers, price, photo
    FROM products"""
    results = query_db(sql)
    return render_template('menus.html', results=results)


@app.route("/base/<int:id>")
def base(id):
    sql = """SELECT burgers, price, photo FROM products"""
    result = query_db(sql, (id,), True)
    return str(result)


@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/cart')
def cart():
    return render_template('cart.html')




if __name__ == "__main__":
    app.run(debug=True)