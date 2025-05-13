from flask import Flask, render_template, redirect, url_for, request, session, send_from_directory
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
from models import db, User, Message

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['UPLOAD_FOLDER'] = 'uploads'

db.init_app(app)
socketio = SocketIO(app)
login_manager = LoginManager()
login_manager.init_app(app)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('chat'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hash_pw = generate_password_hash(request.form['password'])
        new_user = User(username=request.form['username'], password=hash_pw)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/chat')
@login_required
def chat():
    messages = Message.query.all()
    return render_template('chat.html', username=current_user.username, messages=messages)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@socketio.on('join')
def handle_join(data):
    join_room(data['room'])
    emit('status', {'msg': f"{data['username']} has joined the room."}, room=data['room'])

@socketio.on('message')
def handle_message(data):
    msg = Message(room=data['room'], sender=data['username'], content=data['message'])
    db.session.add(msg)
    db.session.commit()
    emit('message', data, room=data['room'])

@socketio.on('image')
def handle_image(data):
    filename = secure_filename(data['filename'])
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with open(filepath, "wb") as f:
        f.write(data['file'])
    emit('image', {'username': data['username'], 'url': f"/uploads/{filename}"}, room=data['room'])

if __name__ == '__main__':
    socketio.run(app, debug=True)
