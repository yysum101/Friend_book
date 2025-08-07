from flask import Flask, request, redirect, url_for, session, flash, render_template_string
import sqlite3
import threading
import webbrowser

app = Flask(__name__)
app.secret_key = 'secret123'
DATABASE = 'friendbook.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

@app.before_request
def setup():
    init_db()

def render_page(content, user=None):
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Friendbook</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
      <div class="container-fluid d-flex justify-content-between align-items-center">
        <a class="navbar-brand" href="{{ url_for('index') }}">Friendbook</a>
        {% if user %}
          <div class="d-flex align-items-center gap-2">
            <span class="text-white">Hello, {{ user.username }}</span>
            <a class="btn btn-light btn-sm" href="{{ url_for('create_post') }}">New Post</a>
            <a class="btn btn-outline-light btn-sm" href="{{ url_for('logout') }}">Logout</a>
          </div>
        {% else %}
          <div class="d-flex gap-2">
            <a class="btn btn-outline-light btn-sm" href="{{ url_for('login') }}">Login</a>
            <a class="btn btn-light btn-sm" href="{{ url_for('register') }}">Register</a>
          </div>
        {% endif %}
      </div>
    </nav>

    <div class="container">
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                <div class="alert alert-info">
                    {% for message in messages %}
                        <div>{{ message }}</div>
                    {% endfor %}
                </div>
            {% endif %}
        {% endwith %}

        {{ content|safe }}
    </div>

    </body>
    </html>
    """
    return render_template_string(template, content=content, user=user)

@app.route('/')
def index():
    db = get_db()
    posts = db.execute('''
        SELECT posts.subject, posts.content, posts.created_at, users.username
        FROM posts JOIN users ON posts.user_id = users.id
        ORDER BY posts.created_at DESC
    ''').fetchall()
    post_html = "<h2>Recent Posts</h2>"
    for post in posts:
        post_html += f"""
        <div class="card mb-3">
            <div class="card-header fw-bold">{post['subject']}</div>
            <div class="card-body">
                <p>{post['content']}</p>
                <small class="text-muted">by <strong>{post['username']}</strong> at {post['created_at']}</small>
            </div>
        </div>
        """
    return render_page(post_html, session.get('user'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        if not username or not password:
            flash("Please fill in both fields.")
            return redirect(url_for('register'))
        try:
            db = get_db()
            db.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            db.commit()
            flash("Registration successful.")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists.")
            return redirect(url_for('register'))

    content = '''
    <h2>Register</h2>
    <form method="post">
        <div class="mb-3">
            <label>Username</label>
            <input name="username" class="form-control" required>
        </div>
        <div class="mb-3">
            <label>Password</label>
            <input name="password" type="password" class="form-control" required>
        </div>
        <button class="btn btn-primary">Register</button>
    </form>
    '''
    return render_page(content, session.get('user'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        if user:
            session['user'] = {'id': user['id'], 'username': user['username']}
            flash("Logged in.")
            return redirect(url_for('index'))
        else:
            flash("Invalid credentials.")
            return redirect(url_for('login'))

    content = '''
    <h2>Login</h2>
    <form method="post">
        <div class="mb-3">
            <label>Username</label>
            <input name="username" class="form-control" required>
        </div>
        <div class="mb-3">
            <label>Password</label>
            <input name="password" type="password" class="form-control" required>
        </div>
        <button class="btn btn-success">Login</button>
    </form>
    '''
    return render_page(content, session.get('user'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out.")
    return redirect(url_for('index'))

@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    user = session.get('user')
    if not user:
        flash("You must be logged in to post.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        subject = request.form['subject'].strip()
        content = request.form['content'].strip()
        if not subject or not content:
            flash("Subject and content cannot be empty.")
            return redirect(url_for('create_post'))
        db = get_db()
        db.execute('INSERT INTO posts (user_id, subject, content) VALUES (?, ?, ?)', (user['id'], subject, content))
        db.commit()
        flash("Post created.")
        return redirect(url_for('index'))

    form = '''
    <h2>Create Post</h2>
    <form method="post">
        <div class="mb-3">
            <label>Subject</label>
            <input name="subject" class="form-control" required>
        </div>
        <div class="mb-3">
            <label>Content</label>
            <textarea name="content" class="form-control" rows="4" required></textarea>
        </div>
        <button class="btn btn-primary">Post</button>
    </form>
    '''
    return render_page(form, user)

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == '__main__':
    # Open browser after 1 second
    threading.Timer(1.0, open_browser).start()
    app.run(host='0.0.0.0', port=5000, debug=True)
