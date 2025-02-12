from flask import Flask, jsonify, request, send_from_directory, session, redirect, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import os


app = Flask(__name__, static_folder='frontend')

app.config['SECRET_KEY'] = os.urandom(24)  # klucz tajny dla sesji - podpisywanie ciasteczek
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'  # baza SQLite dla użytkowników, zadań i sesji
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ---------------------------
#  region MODELE
# ---------------------------

# tabela łącząca użytkowników z sesjami (relacja wiele do wielu)
user_sessions = db.Table('user_sessions',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('session_id', db.Integer, db.ForeignKey('session.id'), primary_key=True)
)

# MODEL ZADANIA – dane przechowywane w bazie
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)

    # każde zadanie jest przypisane do sesji
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=True)
    session = db.relationship('Session', back_populates='tasks')


# MODEL UŻYTKOWNIKA – dane przechowywane w bazie
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    # aktualna sesja użytkownika
    current_session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=True)
    
    # sesje, które użytkownik utworzył (relacja 1-do-wielu)
    owned_sessions = db.relationship(
        'Session',
        back_populates='owner',
        cascade="all, delete-orphan",
        foreign_keys=lambda: [Session.owner_id]
    )
    
    # sesje, do których użytkownik dołączył (relacja wiele-do-wielu)
    joined_sessions = db.relationship(
        'Session',
        secondary=user_sessions,
        back_populates='joined_users'
    )
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# MODEL SESJI - dane przechowywane w bazie
class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_private = db.Column(db.Boolean, default=True)
    
    # właściciel sesji
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    owner = db.relationship(
        'User',
        back_populates='owned_sessions',
        foreign_keys=[owner_id]
    )
    
    # zadania przypisane do sesji
    tasks = db.relationship('Task', back_populates='session', cascade="all, delete-orphan")
    
    # użytkownicy, którzy dołączyli do sesji (relacja wiele-do-wielu)
    joined_users = db.relationship(
        'User',
        secondary=user_sessions,
        back_populates='joined_sessions'
    )

# tworzenie tabeli zadań i użytkowników w bazie
with app.app_context():
    db.create_all()

# ---------------------------
# endregion MODELE
# ---------------------------


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
    return redirect(url_for('sessions'))

# ---------------------------
# Wylogowanie
# ---------------------------

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# ---------------------------
# region SESJE - PRYWATNA / GRUPOWA
# ---------------------------

# pobieranie wszystkich sesji
@app.route('/sessionslist', methods=['GET'])
def sessionslist():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    if user is None:
        return jsonify({'error': 'User not found'}), 404
    
    all_sessions = Session.query.filter(
        (Session.is_private == False) | (Session.owner_id == user.id)
    ).all()
    return jsonify([{
        'name': ses.name,
        'is_private': ses.is_private,
    } for ses in all_sessions])

@app.route('/sessions', methods=['GET'])
def sessions():
    return send_from_directory(app.static_folder, 'sessions.html')

# tworzenie nowej sesji
@app.route('/sessions', methods=['POST'])
def create_session():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    if user is None:
        return jsonify({'error': 'User not found'}), 404

    # odbieranie danych z formularza
    data = request.get_json()
    session_name = data.get('name')
    session_type = data.get('type')

    if not session_name or not session_type:
        return jsonify({'error': 'Session name and type are required'}), 400

    if session_type not in ['private', 'group']:
        return jsonify({'error': 'Invalid session type'}), 400

    is_private = True if session_type == 'private' else False
    new_session = Session(name=session_name, is_private=is_private, owner=user)

    print(f"Creating session: {session_name} | Type: {session_type} | Is Private: {is_private}")

    db.session.add(new_session)
    db.session.commit()

    # jeśli sesja jest grupowa, dodajemy właściciela do listy użytkowników
    if not is_private:
        print("Adding owner to group session.")
        new_session.joined_users.append(user)
        db.session.commit()

    print(f'New session created: {new_session.name}')

    # ustawiamy current_session_id dla użytkownika, jeśli to prywatna sesja
    if is_private:
        user.current_session_id = new_session.id
        db.session.commit()
        # return redirect(url_for('todos'))

    return jsonify({
        'id': new_session.id,
        'name': new_session.name,
        'is_private': new_session.is_private,
        'owner_id': new_session.owner_id
    }), 201

# dołączanie do sesji grupowej
@app.route('/sessions/<int:session_id>/join', methods=['POST'])
def join_session(session_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    if user is None:
        return jsonify({'error': 'User not found'}), 404

    session_to_join = Session.query.get(session_id)
    if session_to_join is None:
        return jsonify({'error': 'Session not found'}), 404

    if session_to_join.is_private:
        return jsonify({'error': 'Cannot join private session'}), 403

    if user in session_to_join.joined_users:
        return jsonify({'error': 'User already joined this session'}), 400

    session_to_join.joined_users.append(user)
    db.session.commit()

    return jsonify({
        'id': session_to_join.id,
        'name': session_to_join.name,
        'is_private': session_to_join.is_private,
        'owner_id': session_to_join.owner_id
    }), 200


# ---------------------------
# endregion
# ---------------------------




# ---------------------------
# region CRUD - zadania z todo list
# ---------------------------

# Tworzenie nowego zadania
@app.route('/todos', methods=['POST'])
def create_todo():
    data = request.get_json()
    title = data.get('title')
    if not title:
        return jsonify({'error': 'Brakuje tytułu zadania'}), 400
    
    # szukamy użytkownika w bazie
    user = User.query.filter_by(username=session['username']).first()

    # sprawdzamy, czy użytkownik ma ustawioną aktualną sesję
    if not user or not user.current_session_id:
        return jsonify({'error': 'Użytkownik nie ma ustawionej sesji'}), 401

    # tworzenie nowego zadania w bazie
    new_task = Task(title=title, session_id=user.current_session_id)
    db.session.add(new_task)
    db.session.commit()
    
    socketio.emit('todo created', {
        'id': new_task.id,
        'title': new_task.title,
        'completed': new_task.completed,
        'session_id': new_task.session_id
    })
    print(f'Wysłano zadanie: {new_task}')
    return jsonify({
        'id': new_task.id,
        'title': new_task.title,
        'completed': new_task.completed
    }), 201


# Pobieranie wszystkich zadań
@app.route('/todoslist', methods=['GET'])
def get_todos():
    user = User.query.filter_by(username=session['username']).first()
    if not user or not user.current_session_id:
        return jsonify({'error': 'Użytkownik nie ma ustawionej sesji'}), 401
    
    tasks = Task.query.filter_by(session_id=user.current_session_id).all()
    return jsonify([{
        'id': task.id,
        'title': task.title,
        'completed': task.completed
    } for task in tasks])

@app.route('/todos', methods=['GET'])
def todos():
    return send_from_directory(app.static_folder, 'index.html')

# Pobieranie pojedynczego zadania
@app.route('/todos/<int:task_id>', methods=['GET'])
def get_todo(task_id):
    user = User.query.filter_by(username=session['username']).first()
    task = Task.query.filter_by(id=task_id, session_id=user.current_session_id).first()
    if task is None:
        return jsonify({'error': 'Nie znaleziono zadania'}), 404
    return jsonify({'id': task.id, 'title': task.title, 'completed': task.completed})

# Aktualizacja zadania
@app.route('/todos/<int:task_id>', methods=['PUT'])
def update_todo(task_id):
    data = request.get_json()
    user = User.query.filter_by(username=session['username']).first()
    task = Task.query.filter_by(id=task_id, session_id=user.current_session_id).first()
    if task is None:
        return jsonify({'error': 'Nie znaleziono zadania'}), 404
    
    title = data.get('title')
    completed = data.get('completed')
    if title is not None:
        task.title = title
    if completed is not None:
        task.completed = completed
    db.session.commit()
    
    socketio.emit('todo updated', {
        'id': task.id,
        'title': task.title,
        'completed': task.completed,
        'session_id': task.session_id
    })
    print(f'Zmieniono status zadania: {task}')
    return jsonify({'id': task.id, 'title': task.title, 'completed': task.completed})

# Usuwanie zadania
@app.route('/todos/<int:task_id>', methods=['DELETE'])
def delete_todo(task_id):
    user = User.query.filter_by(username=session['username']).first()
    task = Task.query.filter_by(id=task_id, session_id=user.current_session_id).first()
    if task is None:
        return jsonify({'error': 'Nie znaleziono zadania'}), 404
    
    db.session.delete(task)  # Usuwamy zadanie z bazy danych
    db.session.commit()
    
    socketio.emit('todo deleted', {
        'id': task.id,
        'title': task.title,
        'completed': task.completed,
        'session_id': task.session_id
    })
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



