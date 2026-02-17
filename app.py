from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "clourf_secret_key"
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB por arquivo

# Criação inicial do banco de dados
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        is_admin INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        filename TEXT,
        folder TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        content TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    conn.commit()
    conn.close()

init_db()

# ---------------- Rotas ---------------- #

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        is_admin = 0
        c.execute("SELECT COUNT(*) FROM users")
        if c.fetchone()[0] == 0:
            is_admin = 1
        try:
            c.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
                      (username, password, is_admin))
            conn.commit()
            flash("Conta criada com sucesso!", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Nome de usuário já existe.", "danger")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session["user_id"] = user[0]
            session["username"] = user[1]
            session["is_admin"] = user[3]
            return redirect(url_for("dashboard"))
        else:
            flash("Usuário ou senha incorretos", "danger")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_id = session["user_id"]
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM files WHERE user_id=?", (user_id,))
    files = c.fetchall()
    c.execute("SELECT * FROM notes WHERE user_id=?", (user_id,))
    notes = c.fetchall()
    conn.close()
    return render_template("dashboard.html", files=files, notes=notes)

@app.route("/upload", methods=["POST"])
def upload():
    if "user_id" not in session:
        return redirect(url_for("login"))
    file = request.files["file"]
    folder = request.form.get("folder", "default")
    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], str(session["user_id"]), folder)
    os.makedirs(save_path, exist_ok=True)
    file.save(os.path.join(save_path, filename))
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO files (user_id, filename, folder) VALUES (?, ?, ?)",
              (session["user_id"], filename, folder))
    conn.commit()
    conn.close()
    flash("Arquivo enviado com sucesso!", "success")
    return redirect(url_for("dashboard"))

@app.route("/add_note", methods=["POST"])
def add_note():
    if "user_id" not in session:
        return redirect(url_for("login"))
    content = request.form["content"]
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO notes (user_id, content) VALUES (?, ?)",
              (session["user_id"], content))
    conn.commit()
    conn.close()
    flash("Nota criada!", "success")
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
