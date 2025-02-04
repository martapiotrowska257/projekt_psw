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

# MODEL UŻYTKOWNIKA – dane przechowywane w bazie
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# tworzenie tabeli użytkowników w bazie
with app.app_context():
    db.create_all()


tasks = [] # pusta lista, w której będą przechowywane zadania
next_id = 1 # licznik do nadawania kolejnych identyfikatorów zadań

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
# Wyogowanie
# ---------------------------

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


# ---------------------------
# region CRUD
# ---------------------------

# Tworzenie nowego zadania
@app.route('/todos', methods=['POST'])
def create_todo():
    global next_id
    data = request.get_json()
    title = data.get('title')
    if not title:
        return jsonify({'error': 'Brakuje tytułu zadania'}), 400
    new_task = {'id': next_id, 'title': title, 'completed': False}
    next_id += 1
    tasks.append(new_task)
    
    socketio.emit('todo created', new_task)
    print(f'Wysłano zadanie: {new_task}')
    return jsonify(new_task), 201

# Pobieranie wszystkich zadań
@app.route('/todos', methods=['GET'])
def get_todos():
    return jsonify(tasks)

# Pobieranie pojedynczego zadania
@app.route('/todos/<int:task_id>', methods=['GET'])
def get_todo(task_id):
    task = next((t for t in tasks if t['id'] == task_id), None)
    if task is None:
        return jsonify({'error': 'Nie znaleziono zadania'}), 404
    return jsonify(task)

# Aktualizacja zadania
@app.route('/todos/<int:task_id>', methods=['PUT'])
def update_todo(task_id):
    data = request.get_json()
    task = next((t for t in tasks if t['id'] == task_id), None)
    if task is None:
        return jsonify({'error': 'Nie znaleziono zadania'}), 404
    title = data.get('title')
    completed = data.get('completed')
    if title is not None:
        task['title'] = title
    if completed is not None:
        task['completed'] = completed
    
    socketio.emit('todo updated', task)
    print(f'Zmieniono status zadania: {task}')
    return jsonify(task)

# Usuwanie zadania
@app.route('/todos/<int:task_id>', methods=['DELETE'])
def delete_todo(task_id):
    global tasks
    task = next((t for t in tasks if t['id'] == task_id), None)
    if task is None:
        return jsonify({'error': 'Nie znaleziono zadania'}), 404
    tasks = [t for t in tasks if t['id'] != task_id]
    
    socketio.emit('todo deleted', task)
    print(f'Usunięto zadanie: {task}')
    return jsonify(task)


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



