from __init__ import app, db, bcrypt
from flask import request, jsonify, render_template, redirect, url_for, session, flash
from bson.objectid import ObjectId
from datetime import datetime


@app.route('/')
@app.route('/events')
def events():
    events = []
    for i in range(10):
        pass
        events.append({
            'title': f'Event {i+1}',
            'description': f'Description for event {i+1}, this is a sample event description to demonstrate text overflow handling in the UI., which might be quite long depending on the event details. We need to ensure it displays correctly without breaking the layout.',
            'date': datetime.now(),
            'url': '#',
            'start_time': '18:00',
            'end_time': '21:00',
            'location': 'kampala, kampala road, lugogo show grounds'
        })
    return render_template('events.html', events=events)

@app.route('/home')
def home():
    events = []
    return render_template('home.html', events=events)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        pass
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        pass
    return render_template('login.html')