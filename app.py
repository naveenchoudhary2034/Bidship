from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import secrets
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from flask_bcrypt import Bcrypt

app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)

# MongoDB Database Configuration
client = MongoClient("mongodb://localhost:27017/")
db = client["bidship_db"]  # Use your MongoDB database name
users_collection = db["users"]  # Users collection
bookings_collection = db["bookings"]  # Bookings collection

# Gmail SMTP Configuration
GMAIL_USER = 'bidshiptransport@gmail.com'  # Replace with your Gmail address
GMAIL_PASSWORD = 'njzl pvky fdfq pjmn'  # Replace with your Gmail password or App password

app.secret_key = secrets.token_hex(16)  # Generates a secure 32-character hex string

# Function to send email
def send_email(to_email, first_name, location1, location2):
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = to_email
        msg['Subject'] = "Your Parcel is on the Way!"

        # Email body
        body = f"Hi {first_name},\n\nYour parcel will be shipped shortly from {location1} to {location2}.\n\nBest regards,\nBidship Team"
        msg.attach(MIMEText(body, 'plain'))

        # Connect to Gmail's SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)

        # Send the email
        server.sendmail(GMAIL_USER, to_email, msg.as_string())
        server.quit()

        print(f"Email sent to {to_email} successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")

# Function to send SMS via email-to-SMS gateway
def send_sms(phone_number, carrier_gateway, message):
    try:
        # Construct recipient email
        recipient = f"{phone_number}@jionet.in"
        
        # Set up the email content
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = recipient
        msg['Subject'] = "SMS Message"
        
        # The body of the email
        msg.attach(MIMEText(message, 'plain'))
        
        # Connect to Gmail's SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        
        # Send the email
        server.sendmail(GMAIL_USER, recipient, msg.as_string())
        server.quit()
        
        print(f"SMS sent to {phone_number} successfully!")
    
    except Exception as e:
        print(f"Error sending SMS: {e}")

# Home route
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/service')
def serice():
    return render_template('bidservice.html')

@app.route('/order')
def order():
    return render_template('bidorder.html')


@app.route('/home')
def home():
    return render_template('1.html')

@app.route('/about')
def about():
    return render_template('bidabout.html')

@app.route('/contact')
def contact():
    return render_template('bidcontact.html')


@app.route('/location')
def location():
    return render_template('bidlocations.html')

# Dashboard route (example post-login)
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("You must be logged in to view the dashboard", "error")
        return render_template('index.html')
    return render_template('1.html')

# Route to book a ride
@app.route('/api/bookRide', methods=['POST'])
def book_ride():
    try:
        # Get the data sent from the front end
        data = request.get_json()

        # Extract data from the request
        first_name = data['firstName']
        last_name = data['lastName']
        mobile_number = data['mobileNumber']
        email = data['email']
        package_dimensions = data['packageDimensions']
        transport_mode = data['transportMode']
        location1 = data['location1']
        location2 = data['location2']
        bid_amount = data['bidamount']

        # Validate that no field is empty
        if not all([first_name, last_name, mobile_number, email, package_dimensions, transport_mode, location1, location2, bid_amount]):
            return jsonify({'message': 'All fields are required.'}), 400

        # Insert data into the bookings collection
        booking_data = {
            'first_name': first_name,
            'last_name': last_name,
            'mobile_number': mobile_number,
            'email': email,
            'package_dimensions': package_dimensions,
            'transport_mode': transport_mode,
            'location1': location1,
            'location2': location2,
            'bid_amount': bid_amount
        }

        result = bookings_collection.insert_one(booking_data)

        # Fetch details of the booked ride from the database (to send email and SMS)
        booking_details = bookings_collection.find_one({'_id': result.inserted_id})

        if booking_details:  # Ensure data is retrieved from the database
            user_name = booking_details['first_name']
            user_email = booking_details['email']
            start_location = booking_details['location1']
            end_location = booking_details['location2']
            # Send email with booking details
            send_email(user_email, user_name, start_location, end_location)

            # Send SMS to the user
            send_sms(mobile_number, 'jionet.in', f"Hi {first_name}, your parcel will be shipped shortly from {location1} to {location2}.")
            
        # Respond to the client
        return jsonify({'message': 'Ride booked successfully! A confirmation email and SMS have been sent.'}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'message': 'An error occurred!'}), 500

@app.route("/api/getBookings" , methods=['GET'])
def get_bookings():
    try:
        # Fetch all bookings from the database
        bookings = bookings_collection.find()
        bookings_list = []
        for booking in bookings:
            booking_data = {
                'firstName': booking['first_name'],
                'lastName': booking['last_name'],
                'mobileNumber': booking['mobile_number'],
                'email': booking['email'],
                'package_dimensions': booking['package_dimensions'],
                'transport_mode': booking['transport_mode'],
                'location1': booking['location1'],
                'location2': booking['location2'],
                'bid_amount': booking['bid_amount']
                }
            bookings_list.append(booking_data)
        return jsonify(bookings_list), 200
    except:
        return jsonify({'message': 'An error occurred!'}), 500
    


@app.route('/about')
def aboutus():
    return render_template('/templates/bidabout.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['username']
        password = request.form['password']

        # Retrieve the user from the database
        user = users_collection.find_one({'email': email})
        
        if user and bcrypt.check_password_hash(user['password'], password):
            # Store user info in session after successful login
            session['user_id'] = str(user['_id'])  # storing user_id as a string
            session['username'] = user['email']   # Optional: Store other details like username

            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))  # Redirect to dashboard after successful login
        else:
            flash('Invalid email or password', 'danger')
        
    return render_template('bidlogin.html')  # Render the login page

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['reg-username']
        email = request.form['reg-email']
        password = request.form['reg-password']

        if not first_name or not email or not password:
            flash('All fields are required', 'danger')
            return redirect(url_for('register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        try:
            user_data = {
                'first_name': first_name,
                'email': email,
                'password': hashed_password
            }

            users_collection.insert_one(user_data)

            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as err:
            flash(f'Error: {err}', 'danger')
    
    return render_template('bidlogin.html')

if __name__ == '__main__':
    app.run(debug=True, port=5500)
