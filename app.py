from flask import Flask, flash, redirect, render_template, request, session, abort
import os
from utils import insert_stats
import json
import urllib.request
from utils import insert_stats, get_counts

template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=template_dir)

hours = 72


@app.route("/")
def index():
    cols, rows = insert_stats(hours=hours, window=6)
    total_counts = list(map(list, get_counts(hours=24).items()))
    total_counts.insert(0, ['Website', 'Counts'])
    return render_template('charts.html',
                           cols=cols,
                           rows=rows,
                           counts=total_counts,
                           h=str(hours))


@app.route("/hello")
def hello():
    return "Hello World!"


if __name__ == "__main__":
    app.run(debug=True)