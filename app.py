from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_socketio import SocketIO

import pymysql
import datetime
app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret!'


socketio = SocketIO(app)

# Koneksi ke database MySQL
db = pymysql.connect(
    host="localhost",
    user="username",
    password="password",
    database="db"
)
cursor = db.cursor()

# Membuat tabel untuk menyimpan pesan
cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        sender VARCHAR(255) NOT NULL,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
db.commit()

# Tambahkan tabel pengguna
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nama VARCHAR(255) NOT NULL,
        url_foto VARCHAR(255),
        username VARCHAR(255) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
db.commit()

# Route untuk halaman chat
@app.route('/')
def chat():
    if 'username' in session:
        uname = session['username']
        cursor.execute("SELECT * FROM users WHERE username = %s", (uname))
        user = cursor.fetchall()
        return render_template('chat.html',user=user)
    else:
        return redirect(url_for('login'))

# Route untuk halaman login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        if user:
            session['username'] = username
            return redirect(url_for('chat'))
        else:
            return render_template('login.html', error='Invalid username or password.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nama = request.form['nama']
        username = request.form['username']
        password = request.form['password']
        try:
            cursor.execute("INSERT INTO users (nama, username, password) VALUES (%s,%s, %s)", (nama, username, password))
            db.commit()
            return redirect(url_for('login'))
        except pymysql.err.IntegrityError:
            return render_template('register.html', error='Username already exists.')
    return render_template('register.html')

# Handler untuk route API untuk mengirim pesan
@app.route('/send_message', methods=['POST'])
def send_message():
    if 'username' in session:
        data = request.get_json()
        sender = session['username']
        message = data['message']

        # Simpan pesan ke database
        cursor.execute("INSERT INTO messages (sender, message) VALUES (%s, %s)", (sender, message))
        db.commit()

        
        socketio.emit('new_message', {'sender': sender, 'message': message})
        return jsonify({'status': 'Message sent successfully'})
    else:
        return jsonify({'status': 'Unauthorized'})

@app.route('/get_messages')
def get_messages():
    now = datetime.datetime.now()
    # Mendapatkan tanggal hari ini
    tanggal_hari_ini = now.date()
    # Membuat objek datetime untuk jam 00:00:00 pada tanggal hari ini
    waktu_mulai_hari_ini = datetime.datetime.combine(tanggal_hari_ini, datetime.time.min)
    cursor.execute("SELECT * FROM messages WHERE created_at > %s ORDER BY created_at DESC", (waktu_mulai_hari_ini,))
    messages = cursor.fetchall()
    messages_list = [{'sender': message[1], 'message': message[2]} for message in messages]
    return jsonify(messages_list)

if __name__ == '__main__':
    socketio.run(app, debug=True)
