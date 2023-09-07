from flask import Flask, render_template, request, redirect, url_for
import requests
from urllib.parse import urlparse
import socket
import pymysql

app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'gcode'

db = pymysql.connect(host=app.config['MYSQL_HOST'],
                     user=app.config['MYSQL_USER'],
                     password=app.config['MYSQL_PASSWORD'],
                     db=app.config['MYSQL_DB'],
                     cursorclass=pymysql.cursors.DictCursor)

def get_ip_from_url(url):
    # Extract the domain from the URL
    domain = urlparse(url).netloc
    try:
        # Get the IP address associated with the domain
        ip = socket.gethostbyname(domain)
        return ip
    except socket.gaierror:
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def query_api():
    url = request.form['url']
    ip_address = get_ip_from_url(url)

    if ip_address:
        api_url = f"https://api.thegreenwebfoundation.org/api/v3/ip-to-co2intensity/{ip_address}"
        try:
            response = requests.get(api_url)
            response.raise_for_status()  # Check for HTTP errors

            data = response.json()

            # Extract the "generation_from_fossil" value from the API response
            generation_from_fossil = data.get('generation_from_fossil')

            # Use the URL as the website name
            website_name = url

            # Insert data into the MySQL table
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO website_data (website_name, carbon_intensity, generation_from_fossil, checked_ip) VALUES (%s, %s, %s, %s)",
                (website_name, data['carbon_intensity'], generation_from_fossil, data['checked_ip'])
            )
            db.commit()
            cursor.close()

            return redirect(url_for('result'))
        except requests.exceptions.RequestException as e:
            return f"Request Error: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"
    else:
        return "Invalid URL. Unable to resolve IP address."

@app.route('/result')
def result():
    # Fetch data from the MySQL table and order by the most recent entries at the top
    cursor = db.cursor()
    cursor.execute(
        "SELECT website_name, carbon_intensity, generation_from_fossil, checked_ip FROM website_data ORDER BY id DESC"
    )
    fossil_fuel_data = cursor.fetchall()
    cursor.close()

    return render_template('result.html', fossil_fuel_data=fossil_fuel_data)

if not db.open:
    print("Database connection is not open")

if __name__ == '__main__':
    app.run(debug=True)
