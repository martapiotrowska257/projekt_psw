from flask import Flask, jsonify, request, send_from_directory, render_template, session, redirect, url_for
from flask_socketio import SocketIO, emit
import os
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__, static_folder='frontend')
socketio = SocketIO(app, cors_allowed_origins="*")
app.secret_key = os.urandom(24)  # Losowy klucz, używany do podpisywania ciasteczek sesyjnych

users = {}

tasks = [] # pusta lista, w której będą przechowywane zadania
next_id = 1 # licznik do nadawania kolejnych identyfikatorów zadań

# ---------------------------
# Rejestracja
# ---------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template("register.html")
    else:
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return "Username and password required", 400
        if username in users:
            return "User already exists", 400
        users[username] = generate_password_hash(password)
        return redirect(url_for('login'))

# ---------------------------
# Logowanie
# ---------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template("login.html")
    else:
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return "Username and password required", 400
        if username not in users or not check_password_hash(users[username], password):
            return "Invalid username or password", 401
        session['username'] = username
        return redirect(url_for('index'))


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
    return send_from_directory(app.static_folder, 'index.html')

# pozostałe pliki statyczne (tj. style.css, script.js)
@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)

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



