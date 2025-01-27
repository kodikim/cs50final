import os

from cs50 import SQL
import csv
import requests
from flask import Flask, flash, jsonify, redirect, render_template, request, session

from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required, lookup, small_lookup

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///final.db")


#sql commands to create database


'''
db.execute("CREATE TABLE shelved (user_id INTEGER NOT NULL, book_id INTEGER, shelf TEXT NOT NULL, rating INTEGER, cover_url TEXT)")
'''


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
@login_required
def index():
    # get the username of the user that is currently logged in
    user = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    return render_template("index.html", user = user[0]['username'])

@app.route("/shelves", methods=["GET", "POST"])
@login_required
def shelves():
    # get user's shelves (the edge case for no shelves is handled in the html)
    shelves = db.execute("SELECT DISTINCT shelf, book_id, cover_url FROM shelved WHERE user_id = :user_id", user_id = session['user_id'])

    # create dictionary for shelves and books
    bookshelves = {}
    for item in shelves:
        shelf = item['shelf']
        book = item['book_id']
        cover_url = item['cover_url']
        if book != None:
            if shelf not in bookshelves:
                bookshelves[shelf] =[]
            bookshelves[shelf].append({'book_id': book, 'cover_url': cover_url})
    return render_template("shelves.html", bookshelves=bookshelves)



@app.route("/search", methods=["GET", "POST"])
def search():

    #return search bar with no results yet
    if request.method == "GET":
        return render_template("search.html", results = None)

    # lookup user's query when form is submitted
    else:
        query = request.form.get("query")
        results = lookup(query)
        return render_template("search.html", results=results)


@app.route("/book/<string:book_id>", methods=["GET", "POST"])
def book_profile(book_id):
    # lookup information on which book is being looked at
    results = lookup(book_id)

    # lookup shelves (to be used for adding books to shelves)
    shelves = db.execute("SELECT DISTINCT shelf FROM shelved WHERE user_id = ?", session["user_id"])

    # get larger version of cover
    image = "https://covers.openlibrary.org/b/olid/{}-M.jpg".format(book_id)

    # render book profile
    if(request.method == "GET"):
        if book_id != 'None':
            return render_template("book_profile.html", error=False, book=results[0], image = image, shelves = shelves)
        elif book_id != 'None':
            return render_template("book_profile.html", error=False, book=results[0], image = image, shelves = shelves)
        else:
            return "Book not found"


@app.route("/new/<string:book_id>", methods=["POST"])
def new(book_id):
    # get name of new shelf from user input
    new_shelf = request.form.get("shelf-name")

    # check if shelf name was entered
    if not new_shelf:
        return render_template("book_profile.html", error=True, message= "Please enter shelf name", book = results[0], shelves = shelves, image = results[0]["cover_url_large"])
    else:
        shelves = db.execute("SELECT DISTINCT shelf FROM shelved WHERE user_id = ?", session["user_id"])
        results = lookup(book_id)
        # update database to include new shelf (no book value)
        db.execute("INSERT INTO shelved(user_id, shelf, book_id, cover_url) VALUES (?, ?, ?, ?)", session["user_id"], new_shelf, results[0]["book_id"], results[0]["cover_url"])
        return render_template("book_profile.html", error_soft=True, message = "New shelf created and book added.", book = results[0], shelves = shelves, image = results[0]["cover_url_large"])

@app.route("/add_to_shelf/<string:book_id>", methods=["POST"])
def add_shelf(book_id):
    results = lookup(book_id)
    shelf = request.form.get("shelve")

    # get only the shelf names (no repeats for multiple books on shelf)
    shelves = db.execute("SELECT DISTINCT shelf FROM shelved WHERE user_id = ?", session["user_id"])

    # check if no shelf was selected
    if shelf == "placeholder" or shelf is None:
        return render_template("book_profile.html", error=True, message = "Please select a shelf to add to", book=results[0], shelves=shelves, image = results[0]["cover_url_large"])
    else:

        # check if book has already been added to shelf
        repeats = db.execute("SELECT * FROM shelved WHERE user_id =? AND book_id =? AND shelf = ?", session['user_id'], book_id, shelf)
        if repeats:
            return render_template("book_profile.html", error=True, message = "Book has already been added to shelf", book=results[0], image = results[0]["cover_url_large"])

        # automatically add book to shelf
        db.execute("INSERT INTO shelved(user_id, book_id, shelf, cover_url) VALUES (?, ?, ?, ?)", session["user_id"], results[0]['book_id'], shelf, results[0]['cover_url'],)
        shelves = db.execute("SELECT DISTINCT shelf FROM shelved WHERE user_id = ?", session["user_id"])
        return render_template("book_profile.html", error_soft=True, message="Book succesfully added to shelf.", book=results[0], shelves=shelves, image = results[0]["cover_url_large"])


'''CREATE TABLE friends (user_id TEXT NOT NULL, friend_id TEXT NOT NULL)'''

@app.route("/friends", methods=["GET", "POST"])
def friends():
    if request.method == "GET":
        # get user's friends and those that have friended user from database
        friends = db.execute("SELECT friend_id FROM friends WHERE user_id = ?", session["user_id"])
        others = db.execute("SELECT user_id FROM friends WHERE friend_id = ?", session['user_id'])
        friend_list = []

        # create list of friends
        for friend in friends:
            username_dict = db.execute("SELECT username, id FROM users WHERE id = ?", friend['friend_id'])
            if username_dict:
                username = username_dict[0]
                friend_list.append(username)

        # create list of others who have friended
        other_list =[]
        for other in others:
            username_dict = db.execute("SELECT username, id FROM users WHERE id = ?", other['user_id'])
            if username_dict:
                username = username_dict[0]
                other_list.append(username)
        return render_template("friends.html", friends = friend_list, others = other_list)
    elif request.method == "POST":
        return render_template("friend_search.html")

@app.route("/friend_search", methods=["GET", "POST"])
def friend_search():

    if request.method == "GET":
        return render_template("friend_search.html", results = None)
    if request.method == "POST":
        # query database for usernames that are similar to query
        query = request.form.get("query")
        # returns error if no query
        if not query:
            return render_template ("friend_search.html", alert = True, message = "Please enter query")
        results = db.execute("SELECT username, id FROM users WHERE username LIKE ?", "%"+query+"%")
        # returns error if no results
        if not results:
            return render_template("friend_search.html", alert = True, message = "No users found")
        return render_template("friend_search.html", results = results)


@app.route("/add_friend/<int:id>", methods=["GET"])
def add_friend(id):
    if request.method == "GET":
        #check if the user is already friends
        repeats = db.execute("SELECT * FROM friends WHERE user_id = ? AND friend_id = ?", session["user_id"], id)
        if repeats:
            return render_template("friend_search.html", alert = True, message = "User is already your friend.")
        # update database
        db.execute("INSERT INTO friends (user_id, friend_id) VALUES (?, ?)", session["user_id"], id)
        return render_template("friend_search.html", alert = True, message = "User succesfully added as friend.")

@app.route("/delete_friend", methods = ["GET", "POST"])
def delete_friend():
    if request.method == "GET":
        # generate list of existing friends
        friends = db.execute("SELECT friend_id FROM friends WHERE user_id = ?", session["user_id"])
        friend_list = []
        for friend in friends:
            username_dict = db.execute("SELECT username, id FROM users WHERE id = ?", friend['friend_id'])
            if username_dict:
                username = username_dict[0]
                friend_list.append(username)
        return render_template("friend_remove.html", friends = friend_list)



@app.route("/deleted_friend/<int:id>", methods = ["GET"])
def deleted_friend(id):
    # update database so friend is removed where appropriate
    db.execute("DELETE FROM friends WHERE user_id = ? AND friend_id = ?", session['user_id'], id)
    friends = db.execute("SELECT friend_id FROM friends WHERE user_id = ?", session["user_id"])
    return render_template("friend_remove.html", friends = friends, alert=True, message = "Friend successfully removed")

@app.route("/friend_profile/<int:id>", methods = ["GET"])
def friend_profile(id):
    # find username and shelves of friend given friend's id
    shelves = db.execute("SELECT DISTINCT shelf, book_id, cover_url FROM shelved WHERE user_id = :user_id", user_id = id)
    username = db.execute("SELECT username FROM users WHERE id = ?", id)

    # create dictionary of shelves
    bookshelves = {}
    for item in shelves:
        shelf = item['shelf']
        book = item['book_id']
        cover_url = item['cover_url']
        if book != None:
            if shelf not in bookshelves:
                bookshelves[shelf] =[]
            bookshelves[shelf].append({'book_id': book, 'cover_url': cover_url})
    return render_template("friend_profile.html", bookshelves=bookshelves, friend= username[0]['username'])




@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
        # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("login.html", wrong=True, message="Must submit username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("login.html", wrong=True, message="Must submit password")

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return render_template("login.html", wrong=True, message="Username or password not found.")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html", wrong=False)


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    password = request.form.get("password")
    username = request.form.get("username")
    if request.method == "GET":
        return render_template("register.html")
    elif request.method == "POST":

        # check for all information
        if (not username or not password or not request.form.get("confirmation")):
            return render_template("register.html", wrong=True, message="Fill in all fields.")
        # check that passwords match
        elif password != request.form.get("confirmation"):
            return render_template("register.html", wrong=True, message="Passwords do not match.")

        # requirements for password - more than 6 letters and at least one uppercase
        elif (len(password) < 6):
            return render_template("register.html", wrong=True, message="Password must be more than 6 letters.")
        elif sum(1 for char in password if char.isupper()) == 0:
            return render_template("register.html", wrong=True, message="Password must contain at least one uppercase.")
        else:
            # check for duplicate usernames
            repeat = db.execute("SELECT id FROM users WHERE username = ?", username)
            if not repeat:

                # insert new user into users table
                db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, generate_password_hash(password),)
                user = db.execute("SELECT id FROM users WHERE username = ?", username)

                # automatically login user
                session["user_id"] = user[0]["id"]
                return redirect("/")
            else:
                return render_template("register.html", wrong=True, message="Username taken.")
    return render_template("register.html", wrong=True, message="please try again")
