import csv
import datetime
import pytz
import requests

from flask import redirect, session, request
from functools import wraps


def lookup(query):
        url = "https://openlibrary.org/search.json?q={}&language=eng".format(query)
        response = requests.get(url)
        data = response.json()
        if response.status_code == 200:
            results = []

            for book in data.get("docs", []):
                olid = book.get("cover_edition_key")
                author_names = book.get("author_name", [])
                first_author = author_names[0] if author_names else None
                book_info = {
                    "book_id": olid,
                    "title": book.get("title"),
                    "author": first_author,
                    "year": book.get("first_publish_year"),
                    "cover_url": "https://covers.openlibrary.org/b/olid/{}-S.jpg".format(olid),
                    "cover_url_large": "https://covers.openlibrary.org/b/olid/{}-M.jpg".format(olid),
                    "first_sentence": book.get("first_sentence"),
                    "page_count": book.get("number_of_pages_median")
                }
                results.append(book_info)
            return results
        elif data['numFound'] == 0:
            results=['none']
            return results
        else:
            results=['none']
            return results

def small_lookup(query):
    url = "https://openlibrary.org/search.json?q={}&language=eng".format(query)
    response = requests.get(url)
    data = response.json()
    if response.status_code == 200:
        results = []
        for book in data.get("docs", []):
            olid = book.get("cover_edition_key")
            book_info = {
                "book_id": olid,
                "title": book.get("title"),
                "cover_url": "https://covers.openlibrary.org/b/olid/{}-S.jpg".format(olid),
            }
            results.append(book_info)
        return results
    elif data['numFound'] == 0:
        results=['none']
        return results
    else:
        results=['none']
        return results



def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function
