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


@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/profile')
def profile():
    user = {
        'first_name': 'john',
        'last_name': 'doe',
        'email': 'john.doe@example.com',
        'phone': '123-456-7890',
        'organization': 'Example Organization'
        }
    
    running_events = []
    for i in range(9):
        running_events.append({
            'title': f'Running Event {i+1}',
            'description': f'Description for running event {i+1}.',
            'date': datetime.now(),
            'url': '#'
        })

    return render_template('profile.html', user=user, running_events=running_events)


@app.route('/change_password', methods=['POST'])
def change_password():
    if request.method == 'POST':
        pass
    return render_template('change_password.html')

@app.route('/edit_profile', methods=['POST'])
def edit_profile():
    if request.method == 'POST':
        pass
    return render_template('edit_profile.html')

@app.route('/manage_users')
def manage_users():
    users = []
    for i in range(5):
        users.append({
            'first_name': 'user'+str(i+1),
            'last_name': 'user'+str(i+1),
            'email': 'user'+str(i+1)+'@example.com',
            'phone': '123-456-7890',
            'organization': 'Example Organization'
        })
    return render_template('manage_users.html', users=users)

@app.route('/create_event', methods=['POST'])
def create_event():
    if request.method == 'POST':
        pass
    return redirect(url_for('profile'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        print(f"Email: {email}, Password: {password}")
    return redirect(url_for('profile'))

@app.route('/logout')
def logout():
    pass
    return redirect(url_for('home'))