from __init__ import app, db, bcrypt
from flask import request, jsonify, render_template, redirect, url_for, session, flash, send_file
from bson.objectid import ObjectId
from datetime import datetime
from utils import save_image, delete_image
import qrcode
import json
from io import BytesIO
import base64
from PIL import Image, ImageDraw, ImageFont
import secrets


@app.route('/')
@app.route('/events')
def events():
    user = db.users.find_one({'_id': ObjectId(session['user_id'])}) if 'user_id' in session else None
    events = list(db.events.find().sort('date'))
    now = datetime.now()
    
    today_events = [event for event in events if event.get('date').date() == now.date()]

    return render_template('events.html', events=events, user=user, today_events=today_events)

@app.route('/home')
def home():
    user = db.users.find_one({'_id': ObjectId(session['user_id'])}) if 'user_id' in session else None
    return render_template('home.html', user=user)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        pass
    return render_template('signup.html')


@app.route('/about')
def about():
    user = db.users.find_one({'_id': ObjectId(session['user_id'])}) if 'user_id' in session else None
    return render_template('about.html', user=user)

@app.route('/profile')
def profile():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = db.users.find_one({'_id': ObjectId(user_id)})
    org = db.organizations.find_one({'_id': ObjectId(user.get('organization_id'))}) if 'organization_id' in user else None
    
    if user.get('role') == 'admin':
        running_events = list(db.events.find().sort('date'))
    else:
        running_events = list(db.events.find({'organization_id': ObjectId(user.get('organization_id'))})) if 'organization_id' in user else []

    return render_template('profile.html', user=user, org=org, running_events=running_events)


@app.route('/change_password', methods=['POST'])
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password'].strip()
        new_password = request.form['new_password'].strip()
        confirm_password = request.form['confirm_password'].strip()

        if new_password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return redirect(url_for('profile'))
        
        user = db.users.find_one({'_id': ObjectId(session['user_id'])})
        
        if not bcrypt.check_password_hash(user['password'], current_password):
            flash('Current password is incorrect. Please try again.', 'danger')
            return redirect(url_for('profile'))
        
        db.users.update_one(
            {'_id': ObjectId(session['user_id'])},
            {'$set': {
                'password': bcrypt.generate_password_hash(new_password).decode('utf-8')
            }})
        flash('Password updated successfully!', 'success')

    return redirect(url_for('profile'))

@app.route('/edit_profile', methods=['POST'])
def edit_profile():
    if request.method == 'POST':
        user_id = request.form['user_id']
        first_name = request.form['first_name'].strip()
        last_name = request.form['last_name'].strip()
        email = request.form['email'].strip()
        contact = request.form['contact'].strip()

        user = db.users.find_one({'_id': ObjectId(user_id)})

        if user['email'] != email:
            if db.users.find_one({'email': email}):
                flash('Email already exists. Please use a different email.', 'danger')
                return redirect(url_for('profile'))
            
        db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'contact': contact
            }})
        flash('Profile updated successfully!', 'success')

    return redirect(url_for('profile'))


@app.route('/manage_users')
def manage_users():
    user = db.users.find_one({'_id': ObjectId(session['user_id'])}) if 'user_id' in session else None

    if user.get('role') == 'admin':
        users = list(db.users.find())
        organizations = list(db.organizations.find())
        for u in users:
            u['organization_name'] = next((org['name'] for org in organizations if str(org['_id']) == str(u.get('organization_id'))), 'N/A') if u.get('organization_id') else 'N/A'
        users = sorted(users, key=lambda x: x.get('first_name', '').lower())
    else:
        users = list(db.users.find({'organization_id': user.get('organization_id')})) if user and 'organization_id' in user else []
    return render_template('manage_users.html', users=users, user=user)


@app.route('/create_event', methods=['GET', 'POST'])
def create_event():
    user = db.users.find_one({'_id': ObjectId(session['user_id'])}) if 'user_id' in session else None
    if request.method == 'POST':
        title = request.form['title'].strip()
        description = request.form['description'].strip()
        location = request.form['location'].strip()
        venue = request.form['venue'].strip()
        image = save_image(request.files['event_image'])
        date = request.form['date']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        category = request.form['category']

        ticket_types = request.form.getlist('ticket_types[]')
        ticket_prices = request.form.getlist('ticket_prices[]')

        ticket_categories = {}
        for t_type, t_price in zip(ticket_types, ticket_prices):
            ticket_categories[t_type] = t_price

        st = datetime.strptime(start_time, '%H:%M')
        et = datetime.strptime(end_time, '%H:%M')

        sdt = datetime.strptime(date, '%Y-%m-%d').replace(hour=st.hour, minute=st.minute)
        edt = datetime.strptime(date, '%Y-%m-%d').replace(hour=et.hour, minute=et.minute)

        db.events.insert_one({
            'title': title,
            'description': description,
            'location': location,
            'venue': venue,
            'image': image,
            'date': datetime.strptime(date, '%Y-%m-%d'),
            'start_time': sdt,
            'end_time': edt,
            'category': category,
            'ticket_categories': ticket_categories,
            'organization_id': ObjectId(user.get('organization_id')) if user and 'organization_id' in user else None
        })

        flash('Event created and published successfully!', 'success')

        return redirect(url_for('profile'))
    
    return render_template('create_event.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password'].strip()
        
        user = db.users.find_one({'email': email})
        if not user:
            flash('Invalid email. Please try again.', 'danger')
            return redirect(url_for('login'))
        if not bcrypt.check_password_hash(user['password'], password):
            flash('Invalid password. Please try again.', 'danger')
            return redirect(url_for('login'))
        
        session['user_id'] = str(user['_id'])
        flash('Login successful!', 'success')

    return redirect(url_for('profile'))

@app.route('/logout')
def logout():
    user_id = session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))


@app.route('/delete_user', methods=['POST'])
def delete_user():
    if request.method == 'POST':
        user_id = request.form['user_id']
        db.users.delete_one({'_id': ObjectId(user_id)})
        flash('User deleted successfully!', 'success')
    return redirect(url_for('manage_users'))

@app.route('/edit_user', methods=['GET', 'POST'])
def edit_user():
    if request.method == 'POST':
        first_name = request.form['first_name'].strip()
        last_name = request.form['last_name'].strip()
        email = request.form['email'].strip()
        contact = request.form['contact'].strip()
        role = request.form['role']
        user_id = request.form['user_id']

        users = list(db.users.find())
        if str(email) in [str(user['email']) for user in users if str(user['_id']) != str(user_id)]:
            flash('Email already exists. Please use a different email.', 'danger')
            return redirect(url_for('manage_users'))
        
        db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'contact': contact,
                'role': role
            }})
        flash('User updated successfully!', 'success')

    return redirect(url_for('manage_users'))

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        first_name = request.form['first_name'].strip()
        last_name = request.form['last_name'].strip()
        email = request.form['email'].strip()
        contact = request.form['contact'].strip()
        organization_id = ObjectId(request.form['organization_id'])
        role = request.form['role']
        password = request.form['password'].strip()
        confirm_password = request.form['confirm_password'].strip()
        
        users = list(db.users.find())
        if str(email) in [str(user['email']) for user in users]:
            flash('Email already exists. Please use a different email.', 'danger')
            return redirect(url_for('manage_users'))
        
        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return redirect(url_for('manage_users'))

        db.users.insert_one({
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'contact': contact,
            'organization_id': organization_id,
            'role': role,
            'password': bcrypt.generate_password_hash(password).decode('utf-8')
        })
        flash('User added successfully!', 'success')   
    return redirect(url_for('manage_users'))

@app.route('/change_user_password', methods=['GET', 'POST'])
def change_user_password():
    if request.method == 'POST':
        user_id = request.form['user_id']
        new_password = request.form['new_password'].strip()
        confirm_password = request.form['confirm_password'].strip()

        if new_password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return redirect(url_for('manage_users'))
        
        db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {
                'password': bcrypt.generate_password_hash(new_password).decode('utf-8')
            }})
        flash('Password updated successfully!', 'success')
    return redirect(url_for('manage_users'))

@app.route('/add_organization', methods=['POST'])
def add_organization():
    if request.method == 'POST':
        org_name = request.form['org_name'].strip()
        org_address = request.form['org_address'].strip()
        org_tin = request.form['org_tin'].strip()

        manager_first_name = request.form['manager_first_name'].strip()
        manager_last_name = request.form['manager_last_name'].strip()
        manager_email = request.form['manager_email'].strip()
        manager_contact = request.form['manager_contact'].strip()
        password = request.form['password'].strip()
        confirm_password = request.form['confirm_password'].strip()

        org = db.organizations.find_one({'name': org_name})
        if org:
            flash('Organization name already exists. Please use a different name.', 'danger')
            return redirect(url_for('profile'))
        
        org = db.organizations.find_one({'tin': org_tin})
        if org:
            flash('Organization TIN already exists. Please use your unique URA assigned TIN.', 'danger')
            return redirect(url_for('profile'))
        
        user = db.users.find_one({'email': manager_email})
        if user:
            flash('Manager email already exists. Please use a different email.', 'danger')
            return redirect(url_for('profile'))
        
        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return redirect(url_for('profile'))
        
        org_id = db.organizations.insert_one({
            'name': org_name,
            'address': org_address,
            'tin': org_tin
        }).inserted_id

        db.users.insert_one({
            'first_name': manager_first_name,
            'last_name': manager_last_name,
            'email': manager_email,
            'contact': manager_contact,
            'organization_id': org_id,
            'role': 'manager',
            'password': bcrypt.generate_password_hash(password).decode('utf-8')
        })

        flash('Organization and manager added successfully!', 'success')
    return redirect(url_for('profile'))


@app.route('/delete_event', methods=['POST'])
def delete_event():
    if request.method == 'POST':
        event_id = request.form['event_id']
        event = db.events.find_one({'_id': ObjectId(event_id)})

        bookings = list(db.bookings.find({'event_id': ObjectId(event_id)}))
        if len(bookings) > 0:
            flash('Cannot delete event with existing bookings.', 'danger')
            return redirect(request.referrer)
        
        if event and 'image' in event:
            delete_image(event.get('image'))
        
        db.events.delete_one({'_id': ObjectId(event_id)})
        flash('Event deleted successfully!', 'success')
        
    return redirect(request.referrer)


@app.route('/edit_event', methods=['POST'])
def edit_event():
    if request.method == 'POST':
        title = request.form['title'].strip()
        description = request.form['description'].strip()
        location = request.form['location'].strip()
        venue = request.form['venue'].strip()
        date = request.form['date']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        category = request.form['category']
        event_id = request.form['event_id']
        ticket_types = request.form.getlist('ticket_types[]')
        ticket_prices = request.form.getlist('ticket_prices[]')

        ticket_categories = {}
        for t_type, t_price in zip(ticket_types, ticket_prices):
            if t_type.strip() != '' and t_price.strip() != '':
                ticket_categories[t_type] = t_price
        
        st = datetime.strptime(start_time, '%H:%M')
        et = datetime.strptime(end_time, '%H:%M')

        sdt = datetime.strptime(date, '%Y-%m-%d').replace(hour=st.hour, minute=st.minute)
        edt = datetime.strptime(date, '%Y-%m-%d').replace(hour=et.hour, minute=et.minute)

        user = db.users.find_one({'_id': ObjectId(session['user_id'])}) if 'user_id' in session else None

        if user is None:
            flash('User not found. Please log in again.', 'danger')
            return redirect(url_for('login'))
        
        event_details = {
            'title': title,
            'description': description,
            'location': location,
            'venue': venue,
            'date': datetime.strptime(date, '%Y-%m-%d'),
            'start_time': sdt,
            'end_time': edt,
            'category': category,
            'ticket_categories': ticket_categories,
            'organization_id': ObjectId(user.get('organization_id')) if user and 'organization_id' in user else None
        }

        if 'event_image' in request.files and request.files['event_image'].filename != '':
            image = save_image(request.files['event_image'])
            event_details['image'] = image

            event = db.events.find_one({'_id': ObjectId(event_id)})
            if event and 'image' in event:
                delete_image(event.get('image'))

                
        db.events.update_one(
            {'_id': ObjectId(event_id)},
            {'$set': event_details}
        )
        
        flash('Event updated successfully!', 'success')
        
    return redirect(request.referrer)


@app.route('/event_details/<event_id>', methods=['GET', 'POST'])
def event_details(event_id):
    user = db.users.find_one({'_id': ObjectId(session['user_id'])}) if 'user_id' in session else None
    event = db.events.find_one({'_id': ObjectId(event_id)})

    free_entry= True
    for price in event.get('ticket_categories', {}).values():
        if price != '0':
            free_entry = False
            break

    event_bookings = list(db.bookings.find({'event_id': ObjectId(event_id)}))

    bookings_by_category = {}
    for booking in event_bookings:
        category = booking.get('ticket_category', 'Unknown')
        if category not in bookings_by_category:
            bookings_by_category[category] = int(booking.get('quantity', 1))
        else:
            bookings_by_category[category] += int(booking.get('quantity', 1))

    return render_template('event_details.html', event=event, user=user, free_entry=free_entry, bookings_by_category=bookings_by_category)


@app.route('/buy_tickets', methods=['GET','POST'])
def buy_tickets():
    if request.method == 'POST':
        event_id = request.form['event_id']
        ticket_category = request.form['ticket_category']
        quantity = int(request.form['quantity'])

        event = db.events.find_one({'_id': ObjectId(event_id)})
        ticket_price = event.get('ticket_categories', {}).get(ticket_category, '0')
        total_price = quantity * float(ticket_price)

        return render_template('payment_page.html', event=event, ticket_price=ticket_price, ticket_category=ticket_category, quantity=quantity, total_price=total_price)


@app.route('/manage_events')
def manage_events():
    user = db.users.find_one({'_id': ObjectId(session['user_id'])}) if 'user_id' in session else None
    if user.get('role') == 'admin':
        events = list(db.events.find().sort('date'))
        organizations = list(db.organizations.find())
        for event in events:
            event['organization_name'] = next((org['name'] for org in organizations if str(org['_id']) == str(event.get('organization_id'))), 'N/A') if event.get('organization_id') else 'N/A'
    else:
        events = list(db.events.find({'organization_id': ObjectId(user.get('organization_id'))}).sort('date')) if user and 'organization_id' in user else []
    return render_template('manage_events.html', events=events, user=user)


@app.route('/airtel_payment_process', methods=['POST'])
def airtel_payment_process():
    if request.method == 'POST':
        event_id = request.form['event_id']
        quantity = request.form['quantity']
        ticket_category = request.form['ticket_category']
        ticket_price = request.form['ticket_price']
        total_price = request.form['total_price']
        event_title = request.form['event_title']
        event_category = request.form['event_category']
        event_date = request.form['event_date']
        event_start_time = request.form['event_start_time']
        event_end_time = request.form['event_end_time']
        event_location = request.form['event_location']
        event_venue = request.form['event_venue']
        payment_method = request.form['payment_method']
        phone_number = request.form['phone_number'].strip()

        event = db.events.find_one({'_id': ObjectId(event_id)})

        # logic for mobile money api integration goes here
        transaction_id = secrets.token_hex(8)

        ticket_io_strs = []
        for i in range(int(quantity)):
            booking_id = db.bookings.insert_one({
                'event_id': ObjectId(event_id),
                'organization_id': ObjectId(event.get('organization_id')),
                'ticket_category': ticket_category,
                'ticket_price': ticket_price,
                'quantity': int(quantity),
                'total_price': float(total_price),
                'payment_method': payment_method,
                'phone_number': phone_number,
                'status': 'paid',
                'booking_date': datetime.now(),
                'transaction_id': transaction_id
            }).inserted_id

            qrcode_details = {
                'event_id': event_id,
                'event_title': event_title,
                'event_category': event_category,
                'event_date': event_date,
                'start_time': event_start_time,
                'end_time': event_end_time,
                'event_location': event_location,
                'event_venue': event_venue,
                'ticket_category': ticket_category,
                'ticket_price': ticket_price,
                'phone_number': phone_number,
                'booking_id': str(booking_id),
                'transaction_id': transaction_id
            }

            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(json.dumps(qrcode_details))
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            img_io = BytesIO()
            img.save(img_io, 'PNG')
            img_io.seek(0)
            qr_code = base64.b64encode(img_io.getvalue()).decode()

            db.bookings.update_one(
                {'_id': booking_id},
                {'$set': {'qr_code': qr_code}}
            )

            # Creating ticket
            ticket_width, ticket_height = 600, 200
            ticket = Image.new('RGB', (ticket_width, ticket_height), color='#f0f0f0')
            draw = ImageDraw.Draw(ticket)

            # Load event image
            event_image = Image.open(f"static/event_images/{event.get('image')}")
            event_image = event_image.resize((ticket_width, ticket_height))
            event_image.putalpha(int(255 * 0.2))  # Set opacity to 20%
            ticket.paste(event_image, (0, 0), event_image)

            # Add gradient-like border
            # draw.rectangle([10, 10, ticket_width-10, ticket_height-10], outline="#000000", width=3)

            # Add event title in header
            try:
                title_font = ImageFont.truetype("arial.ttf", 20)
                detail_font = ImageFont.truetype("DejaVuSans.ttf", 16)  # Changed to a sans-serif font
            except:
                title_font = ImageFont.load_default()
                detail_font = ImageFont.load_default()

            draw.text((30, 25), f"{event_title}", fill="#cb2247", font=title_font, weight="bold")

            # Add event details text on the left side
            y_offset = 60
            line_height = 25
            details = [
                f"{event_date}  |  {event_start_time} - {event_end_time}",
                f"{event_location}  |  {event_venue}",
                f"Ticket : {ticket_category}  |  Qty : {quantity}",
                f"Price : {ticket_price} UGX",
                f"Booking ID : {str(booking_id)}"
            ]
        
            for detail in details:
                draw.text((30, y_offset), detail, fill='#2c3e50', font=detail_font)
                y_offset += line_height

            # Add vertical line in the middle
            mid_x = ticket_width // 2
            draw.line([(mid_x, 15), (mid_x, ticket_height - 15)], fill="#000000", width=2)

            # Add QR code to the right side
            qr_img = Image.open(BytesIO(base64.b64decode(qr_code)))
            qr_img = qr_img.resize((150, 150))
            ticket.paste(qr_img, (390, 25))

            # Save ticket
            ticket_io = BytesIO()
            ticket.save(ticket_io, 'PNG')
            ticket_io.seek(0)

            db.bookings.update_one(
                {'_id': booking_id},
                {'$set': {'ticket': base64.b64encode(ticket_io.getvalue()).decode()}}
            )

            ticket_io_str = base64.b64encode(ticket_io.getvalue()).decode()
            ticket_io_strs.append({'ticket_io_str': ticket_io_str, 'ticket_id': str(booking_id), 'event_title': event_title})
                
        flash('Payment Processed Successfully', 'success')
        return render_template('ticket.html', event=event, ticket_io_strs=ticket_io_strs)
    

@app.route('/mtn_payment_process', methods=['POST'])
def mtn_payment_process():
    if request.method == 'POST':
        event_id = request.form['event_id']
        quantity = request.form['quantity']
        ticket_category = request.form['ticket_category']
        ticket_price = request.form['ticket_price']
        total_price = request.form['total_price']
        event_title = request.form['event_title']
        event_category = request.form['event_category']
        event_date = request.form['event_date']
        event_start_time = request.form['event_start_time']
        event_end_time = request.form['event_end_time']
        event_location = request.form['event_location']
        event_venue = request.form['event_venue']
        payment_method = request.form['payment_method']
        phone_number = request.form['phone_number'].strip()

        event = db.events.find_one({'_id': ObjectId(event_id)})

        # logic for mobile money api integration goes here
        transaction_id = secrets.token_hex(8)

        ticket_io_strs = []
        for i in range(int(quantity)):
            booking_id = db.bookings.insert_one({
                'event_id': ObjectId(event_id),
                'organization_id': ObjectId(event.get('organization_id')),
                'ticket_category': ticket_category,
                'ticket_price': ticket_price,
                'quantity': int(quantity),
                'total_price': float(total_price),
                'payment_method': payment_method,
                'phone_number': phone_number,
                'status': 'paid',
                'booking_date': datetime.now(),
                'transaction_id': transaction_id
            }).inserted_id

            qrcode_details = {
                'event_id': event_id,
                'event_title': event_title,
                'event_category': event_category,
                'event_date': event_date,
                'start_time': event_start_time,
                'end_time': event_end_time,
                'event_location': event_location,
                'event_venue': event_venue,
                'ticket_category': ticket_category,
                'ticket_price': ticket_price,
                'phone_number': phone_number,
                'booking_id': str(booking_id),
                'transaction_id': transaction_id
            }

            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(json.dumps(qrcode_details))
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            img_io = BytesIO()
            img.save(img_io, 'PNG')
            img_io.seek(0)
            qr_code = base64.b64encode(img_io.getvalue()).decode()

            db.bookings.update_one(
                {'_id': booking_id},
                {'$set': {'qr_code': qr_code}}
            )

            # Creating ticket
            ticket_width, ticket_height = 600, 200
            ticket = Image.new('RGB', (ticket_width, ticket_height), color='#f0f0f0')
            draw = ImageDraw.Draw(ticket)

            # Load event image
            event_image = Image.open(f"static/event_images/{event.get('image')}")
            event_image = event_image.resize((ticket_width, ticket_height))
            event_image.putalpha(int(255 * 0.2))  # Set opacity to 20%
            ticket.paste(event_image, (0, 0), event_image)

            # Add gradient-like border
            # draw.rectangle([10, 10, ticket_width-10, ticket_height-10], outline="#000000", width=3)

            # Add event title in header
            try:
                title_font = ImageFont.truetype("arial.ttf", 20)
                detail_font = ImageFont.truetype("DejaVuSans.ttf", 16)  # Changed to a sans-serif font
            except:
                title_font = ImageFont.load_default()
                detail_font = ImageFont.load_default()

            draw.text((30, 25), f"{event_title}", fill="#cb2247", font=title_font, weight="bold")

            # Add event details text on the left side
            y_offset = 60
            line_height = 25
            details = [
                f"{event_date}  |  {event_start_time} - {event_end_time}",
                f"{event_location}  |  {event_venue}",
                f"Ticket : {ticket_category}  |  Qty : {quantity}",
                f"Price : {ticket_price} UGX",
                f"Booking ID : {str(booking_id)}"
            ]
        
            for detail in details:
                draw.text((30, y_offset), detail, fill='#2c3e50', font=detail_font)
                y_offset += line_height

            # Add vertical line in the middle
            mid_x = ticket_width // 2
            draw.line([(mid_x, 15), (mid_x, ticket_height - 15)], fill="#000000", width=2)

            # Add QR code to the right side
            qr_img = Image.open(BytesIO(base64.b64decode(qr_code)))
            qr_img = qr_img.resize((150, 150))
            ticket.paste(qr_img, (390, 25))

            # Save ticket
            ticket_io = BytesIO()
            ticket.save(ticket_io, 'PNG')
            ticket_io.seek(0)

            db.bookings.update_one(
                {'_id': booking_id},
                {'$set': {'ticket': base64.b64encode(ticket_io.getvalue()).decode()}}
            )

            ticket_io_str = base64.b64encode(ticket_io.getvalue()).decode()
            ticket_io_strs.append({'ticket_io_str': ticket_io_str, 'ticket_id': str(booking_id), 'event_title': event_title})
                
        flash('Payment Processed Successfully', 'success')
        return render_template('ticket.html', event=event, ticket_io_strs=ticket_io_strs)
    

@app.route('/validation')
def validation():
    return render_template('validation.html')

@app.route('/validate_qr', methods=['POST'])
def validate_qr():
    if request.method == 'POST':
        qr_data = request.form.get('qr_data')
        try:
            qr_details = json.loads(qr_data)
            booking_id = qr_details.get('booking_id')
            booking = db.bookings.find_one({'_id': ObjectId(booking_id)})
            event_details = db.events.find_one({'_id': ObjectId(booking.get('event_id'))}) if booking else None
            if not booking:
                flash('Invalid QR Code. Booking not found.', 'danger')
                return redirect(request.referrer)
            if booking.get('status') == 'used':
                flash('This ticket has already been used.', 'warning')
                return redirect(request.referrer)
            db.bookings.update_one(
                {'_id': ObjectId(booking_id)},
                {'$set': {'status': 'used'}}
            )
            flash(f'Ticket is valid for {event_details.get("title") if event_details else "Unknown Event"}.', 'success')
        except Exception as e:
            flash('Error processing QR Code. Please try again.', 'danger')

    return redirect(request.referrer)


@app.route('/manage_organizations')
def manage_organizations():
    user = db.users.find_one({'_id': ObjectId(session['user_id'])}) if 'user_id' in session else None
    organizations = list(db.organizations.find())
    return render_template('manage_organizations.html', organizations=organizations, user=user)

@app.route('/edit_organization', methods=['POST'])
def edit_organization():
    if request.method == 'POST':
        organization_id = request.form['organization_id']
        name = request.form['name'].strip()
        address = request.form['address'].strip()
        tin = request.form['tin'].strip()

        existing_org = db.organizations.find_one({'name': name})

        if existing_org and str(existing_org['_id']) != organization_id:
            flash('Organization name already exists. Please use a different name.', 'danger')
            return redirect(request.referrer)
        
        existing_org = db.organizations.find_one({'tin': tin})

        if existing_org and str(existing_org['_id']) != organization_id:
            flash('Organization TIN already exists. Please use your unique URA assigned TIN.', 'danger')
            return redirect(request.referrer)

        db.organizations.update_one(
            {'_id': ObjectId(organization_id)},
            {'$set': {
                'name': name,
                'address': address,
                'tin': tin
            }}
        )
        flash('Organization updated successfully!', 'success')

    return redirect(request.referrer)


@app.route('/delete_organization', methods=['POST'])
def delete_organization():
    if request.method == 'POST':
        organization_id = request.form['organization_id']

        users = list(db.users.find({'organization_id': ObjectId(organization_id)}))
        if len(users) > 0:
            flash('Cannot delete organization with existing users.', 'danger')
            return redirect(request.referrer)
        
        events = list(db.events.find({'organization_id': ObjectId(organization_id)}))
        if len(events) > 0:
            flash('Cannot delete organization with existing events.', 'danger')
            return redirect(request.referrer)
        
        db.organizations.delete_one({'_id': ObjectId(organization_id)})
        flash('Organization deleted successfully!', 'success')

    return redirect(request.referrer)