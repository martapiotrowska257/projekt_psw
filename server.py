from flask import Flask, jsonify, request, send_from_directory, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import os

app = Flask(__name__, static_folder='frontend')

app.config['SECRET_KEY'] = os.urandom(24)  # klucz tajny dla sesji - podpisywanie ciasteczek
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'  # baza SQLite dla użytkowników
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ---------------------------
#  region MODELE
# ---------------------------

# MODEL ZADANIA – dane przechowywane w bazie
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', back_populates='tasks')

# MODEL UŻYTKOWNIKA – dane przechowywane w bazie
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    tasks = db.relationship('Task', back_populates='user', cascade="all, delete-orphan")

    # sesje stworzone przez użytkownika
    sessions = db.relationship('Session', back_populates='owner', cascade="all, delete-orphan")

    # sesje do których użytkownik dołączył - relacja wiele do wielu
    joined_sessions = db.relationship('Session', secondary='session_users', back_populates='users')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# MODEL SESJI - dane przechowywane w bazie
class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) # nazwa sesji
    is_private = db.Column(db.Boolean, default=True) # czy sesja jest prywatna


    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    owner = db.relationship('User', back_populates='session')

    # użytkownicy należący do sesji - relacja wiele do wielu
    users = db.relationship('User', secondary='session_users', back_populates='joined_sessions')

# tworzenie tabeli zadań i użytkowników w bazie
with app.app_context():
    db.create_all()

# ---------------------------
# endregion MODELE
# ---------------------------


# tasks = [] # pusta lista, w której będą przechowywane zadania
# next_id = 1 # licznik do nadawania kolejnych identyfikatorów zadań

# ---------------------------
# Rejestracja
# ---------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return send_from_directory(app.static_folder, 'register.html')
    username = request.form.get('username')
    password = request.form.get('password')
    if not username or not password:
        return "Username and password required", 400
        
    if User.query.filter_by(username=username).first():
        return "User already exists", 400
        
    new_user = User(username=username)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for('login'))

# ---------------------------
# Logowanie
# ---------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return send_from_directory(app.static_folder, 'login.html')  # Pobiera plik z frontend
    
    username = request.form.get('username')
    password = request.form.get('password')
    if not username or not password:
        return "Username and password required", 400
        
    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(password):
        return "Invalid username or password", 401
    
    session['username'] = username
    session.permanent = True
    return redirect(url_for('index'))

# ---------------------------
# Wylogowanie
# ---------------------------

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


# ---------------------------
# region WYBÓR SESJI - PRYWATNA / GRUPOWA
# ---------------------------

@app.route('/sessions', methods=['GET', 'POST'])
def choose_session():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    if user is None:
        return jsonify({'error': 'User not found'}), 404

    if request.method == 'GET':
        return jsonify({'session': user.session}) # pobieramy aktualny typ sesji
    
    data = request.get_json()
    session_type = data.get('type')

    if session_type not in ['private', 'group']:
        return jsonify({'error': 'Invalid session type'}), 400
    
    user.session = session_type
    db.session.commit()
    return jsonify({'session': user.session}) # potwierdzamy zmianę sesji


# ---------------------------
# endregion
# ---------------------------


# ---------------------------
# region WYSZUKIWANIE WZORCÓW
# ---------------------------

# @app.route('/todos', methods=['GET'])
# def search():
#     pass



# ---------------------------
# endregion
# ---------------------------


# ---------------------------
# region CRUD - zadania z todo list
# ---------------------------

# Tworzenie nowego zadania
@app.route('/todos', methods=['POST'])
def create_todo():
    # global next_id
    data = request.get_json()
    title = data.get('title')
    if not title:
        return jsonify({'error': 'Brakuje tytułu zadania'}), 400
    
    # szukanie użytkownika w bazie
    user = User.query.filter_by(username=session['username']).first()

    # tworzenie nowego zadania w bazie
    new_task = Task(title=title, user_id=user.id)
    db.session.add(new_task)
    db.session.commit()
    
    socketio.emit('todo created', {'id': new_task.id, 'title': new_task.title, 'completed': new_task.completed, 'user_id': new_task.user_id})
    print(f'Wysłano zadanie: {new_task}')
    return jsonify({'id': new_task.id, 'title': new_task.title, 'completed': new_task.completed}), 201

# Pobieranie wszystkich zadań
@app.route('/todos', methods=['GET'])
def get_todos():
    user = User.query.filter_by(username=session['username']).first()
    tasks = Task.query.filter_by(user_id=user.id).all()  # pobieramy zadania przypisane do użytkownika
    return jsonify([{'id': task.id, 'title': task.title, 'completed': task.completed} for task in tasks])

# Pobieranie pojedynczego zadania
@app.route('/todos/<int:task_id>', methods=['GET'])
def get_todo(task_id):
    user = User.query.filter_by(username=session['username']).first()
    task = Task.query.filter_by(id=task_id, user_id=user.id).first()  # sprawdzamy, czy zadanie należy do tego użytkownika
    if task is None:
        return jsonify({'error': 'Nie znaleziono zadania'}), 404
    return jsonify({'id': task.id, 'title': task.title, 'completed': task.completed})

# Aktualizacja zadania
@app.route('/todos/<int:task_id>', methods=['PUT'])
def update_todo(task_id):
    data = request.get_json()
    user = User.query.filter_by(username=session['username']).first()
    task = Task.query.filter_by(id=task_id, user_id=user.id).first()
    if task is None:
        return jsonify({'error': 'Nie znaleziono zadania'}), 404
    
    title = data.get('title')
    completed = data.get('completed')

    if title is not None:
        task.title = title
    if completed is not None:
        task.completed = completed

    db.session.commit()  # Zapisujemy zmiany w bazie danych


    socketio.emit('todo updated', {'id': task.id, 'title': task.title, 'completed': task.completed, 'user_id': task.user_id})
    print(f'Zmieniono status zadania: {task}')
    return jsonify({'id': task.id, 'title': task.title, 'completed': task.completed})

# Usuwanie zadania
@app.route('/todos/<int:task_id>', methods=['DELETE'])
def delete_todo(task_id):
    user = User.query.filter_by(username=session['username']).first()
    task = Task.query.filter_by(id=task_id, user_id=user.id).first()
    if task is None:
        return jsonify({'error': 'Nie znaleziono zadania'}), 404
    
    db.session.delete(task)  # Usuwamy zadanie z bazy danych
    db.session.commit()
    
    socketio.emit('todo deleted', {'id': task.id, 'title': task.title, 'completed': task.completed, 'user_id': task.user_id})
    print(f'Usunięto zadanie: {task}')
    return jsonify({'id': task.id, 'title': task.title, 'completed': task.completed})


# ---------------------------
# endregion CRUD
# ---------------------------

# ---------------------------
# Serwowanie plików statycznych
# ---------------------------

# główna strona - zwraca index.html z folderu frontend
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))  # wymuszenie logowania
    return send_from_directory(app.static_folder, 'index.html') # jeśli użytkownik jest zalogowany, zwraca stronę główną

# pozostałe pliki statyczne (tj. style.css, script.js)
@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)

# ---------------------------
# Obsługa Socket.IO - nasłuchiwanie na zdarzenia
# ---------------------------
@socketio.on('connect')
def on_connect():
    print('Klient połączony')

@socketio.on('disconnect')
def on_disconnect():
    print('Klient rozłączony')


if __name__ == "__main__":
    url = f"http://127.0.0.1:3000"
    print(f"Serwer działa na: {url}")
    socketio.run(app, host="0.0.0.0", port=3000)



