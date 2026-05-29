from flask import Flask, g, render_template
import sqlite3

DATABASE = 'Database/actuals.db'

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('home.html')

if __name__ == "__main__":
    app.run(debug=True)