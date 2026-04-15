from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = "secret_key_transport_uac"

DATABASE = "database.db"
UPLOAD_FOLDER = os.path.join("static", "uploads", "news")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(os.path.join(app.root_path, UPLOAD_FOLDER), exist_ok=True)

# =============================
# CONNEXION À LA BASE DE DONNÉES
# =============================
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_image(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        upload_dir = os.path.join(app.root_path, app.config["UPLOAD_FOLDER"])
        filepath = os.path.join(upload_dir, filename)
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(filepath):
            filename = f"{base}_{counter}{ext}"
            filepath = os.path.join(upload_dir, filename)
            counter += 1
        file.save(filepath)
        return filename
    return None

# =============================
# INITIALISATION DE LA BASE
# =============================
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Table des Utilisateurs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)

    # 2. Table des Lieux
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL UNIQUE,
        type TEXT NOT NULL,
        latitude REAL,
        longitude REAL
    )
    """)

    # 3. Table des Bus
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS buses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plaque TEXT NOT NULL UNIQUE,
        capacite INTEGER,
        statut TEXT DEFAULT 'actif',
        current_lat REAL,
        current_lon REAL,
        dernier_arret TEXT
    )
    """)

    # Ajout des colonnes manquantes pour les anciennes bases
    cursor.execute("PRAGMA table_info(buses)")
    buses_columns = [row[1] for row in cursor.fetchall()]
    if "current_lat" not in buses_columns:
        cursor.execute("ALTER TABLE buses ADD COLUMN current_lat REAL")
    if "current_lon" not in buses_columns:
        cursor.execute("ALTER TABLE buses ADD COLUMN current_lon REAL")
    if "dernier_arret" not in buses_columns:
        cursor.execute("ALTER TABLE buses ADD COLUMN dernier_arret TEXT")

    # 4. Table des Tarifs (Routes)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        depart_id INTEGER,
        destination_id INTEGER,
        prix_aller INTEGER DEFAULT 500,
        prix_retour INTEGER DEFAULT 500,
        FOREIGN KEY(depart_id) REFERENCES locations(id),
        FOREIGN KEY(destination_id) REFERENCES locations(id)
    )
    """)

    # 5. Table des Affectations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bus_id INTEGER,
        driver_id INTEGER,
        date TEXT,
        heure_depart TEXT,
        statut_travail TEXT DEFAULT 'OUI',
        FOREIGN KEY(bus_id) REFERENCES buses(id),
        FOREIGN KEY(driver_id) REFERENCES users(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bus_id INTEGER,
        driver_id INTEGER,
        date TEXT,
        heure_depart TEXT,
        destination TEXT,
        disponible TEXT DEFAULT 'oui',
        FOREIGN KEY(bus_id) REFERENCES buses(id),
        FOREIGN KEY(driver_id) REFERENCES users(id)
    )
    """)

    # 6. Table des Actualités
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titre TEXT NOT NULL,
        contenu TEXT NOT NULL,
        date DATETIME DEFAULT CURRENT_TIMESTAMP,
        admin_id INTEGER,
        image_path TEXT,
        FOREIGN KEY(admin_id) REFERENCES users(id)
    )
    """)

    # Mise à jour des colonnes existantes si nécessaire
    cursor.execute("PRAGMA table_info(users)")
    users_columns = [row[1] for row in cursor.fetchall()]
    if "telephone" not in users_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN telephone TEXT")
    if "permis" not in users_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN permis TEXT")

    cursor.execute("PRAGMA table_info(news)")
    news_columns = [row[1] for row in cursor.fetchall()]
    if "date" not in news_columns:
        cursor.execute("ALTER TABLE news ADD COLUMN date DATETIME DEFAULT CURRENT_TIMESTAMP")
    if "admin_id" not in news_columns:
        cursor.execute("ALTER TABLE news ADD COLUMN admin_id INTEGER")
    if "image_path" not in news_columns:
        cursor.execute("ALTER TABLE news ADD COLUMN image_path TEXT")

    cursor.execute("PRAGMA table_info(schedules)")
    schedules_columns = [row[1] for row in cursor.fetchall()]
    if "destination" not in schedules_columns:
        cursor.execute("ALTER TABLE schedules ADD COLUMN destination TEXT")
    if "disponible" not in schedules_columns:
        cursor.execute("ALTER TABLE schedules ADD COLUMN disponible TEXT DEFAULT 'oui'")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS news_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        news_id INTEGER NOT NULL,
        user_id INTEGER,
        contenu TEXT NOT NULL,
        date DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(news_id) REFERENCES news(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS news_likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        news_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        date DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(news_id, user_id),
        FOREIGN KEY(news_id) REFERENCES news(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # --- INSERTIONS PAR DÉFAUT ---
    # Insertion de l'admin par défaut (user: admin / pass: uac2026)
    hashed_pw = generate_password_hash("uac2026")
    cursor.execute("INSERT OR IGNORE INTO users (nom, email, password, role) VALUES (?, ?, ?, ?)",
                   ("Admin UAC", "admin", hashed_pw, "admin"))
    cursor.execute("UPDATE users SET password = ? WHERE email = ?", (hashed_pw, "admin"))

    # Insertion des lieux stratégiques
    lieux = [
        ('Takenga', 'station', -0.1234, 29.1234),
        ('Rawbank', 'station', -0.1235, 29.1235),
        ('Kambali', 'site', -0.1250, 29.1260),
        ('Mirador', 'site', -0.1280, 29.1290)
    ]
    cursor.executemany("INSERT OR IGNORE INTO locations (nom, type, latitude, longitude) VALUES (?, ?, ?, ?)", lieux)

    conn.commit()
    conn.close()

# Initialisation au lancement
with app.app_context():
    init_db()

# =============================
# ROUTES PRINCIPALES
# =============================

@app.route("/")
def index():
    conn = get_db()
    news = conn.execute("""
        SELECT n.*, u.nom AS admin_name,
            (SELECT COUNT(*) FROM news_comments c WHERE c.news_id = n.id) AS comment_count,
            (SELECT COUNT(*) FROM news_likes l WHERE l.news_id = n.id) AS like_count
        FROM news n
        LEFT JOIN users u ON n.admin_id = u.id
        ORDER BY n.date DESC
    """).fetchall()
    conn.close()
    return render_template("index.html", news=news)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["nom"] = user["nom"]
            session["role"] = user["role"]
            
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            elif user["role"] == "driver":
                return redirect(url_for("driver_dashboard"))
            else:
                return redirect(url_for("student_dashboard"))
        
        return "Identifiants incorrects", 401
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# =============================
# ESPACE ADMINISTRATION
# =============================

@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    
    conn = get_db()
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_drivers = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'driver'").fetchone()[0]
    total_students = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'student'").fetchone()[0]
    total_buses = conn.execute("SELECT COUNT(*) FROM buses").fetchone()[0]
    total_routes = conn.execute("SELECT COUNT(*) FROM routes").fetchone()[0]
    total_news = conn.execute("SELECT COUNT(*) FROM news").fetchone()[0]
    total_locations = conn.execute("SELECT COUNT(*) FROM locations").fetchone()[0]
    total_assignments = conn.execute("SELECT COUNT(*) FROM assignments").fetchone()[0]
    conn.close()
    
    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_drivers=total_drivers,
        total_students=total_students,
        total_buses=total_buses,
        total_routes=total_routes,
        total_news=total_news,
        total_locations=total_locations,
        total_assignments=total_assignments,
    )

@app.route("/driver")
def driver_dashboard():
    if session.get("role") != "driver":
        return redirect(url_for("login"))

    conn = get_db()
    user_id = session.get("user_id")

    driver_info = conn.execute("SELECT * FROM users WHERE id = ? AND role = 'driver'", (user_id,)).fetchone()

    driver_schedules = conn.execute("""
        SELECT s.*, b.plaque, b.capacite, b.current_lat, b.current_lon, b.dernier_arret
        FROM schedules s
        LEFT JOIN buses b ON s.bus_id = b.id
        WHERE s.driver_id = ?
        ORDER BY s.date ASC, s.heure_depart ASC
        LIMIT 8
    """, (user_id,)).fetchall()

    current_trip = driver_schedules[0] if driver_schedules else None

    current_bus = None
    if current_trip and current_trip["plaque"]:
        current_bus = conn.execute("""
            SELECT id, plaque, capacite, statut, current_lat, current_lon, dernier_arret
            FROM buses
            WHERE id = ?
        """, (current_trip["bus_id"],)).fetchone()

    recent_news = conn.execute("""
        SELECT n.*, u.nom AS admin_name
        FROM news n
        LEFT JOIN users u ON n.admin_id = u.id
        ORDER BY n.date DESC
        LIMIT 3
    """).fetchall()

    conn.close()

    return render_template(
        "driver/dashboard.html",
        driver_info=driver_info,
        driver_schedules=driver_schedules,
        current_trip=current_trip,
        current_bus=current_bus,
        recent_news=recent_news,
    )

@app.route("/driver/update-location", methods=["POST"])
def driver_update_location():
    if session.get("role") != "driver":
        return redirect(url_for("login"))

    user_id = session.get("user_id")
    latitude = request.form.get("current_lat")
    longitude = request.form.get("current_lon")
    dernier_arret = request.form.get("dernier_arret")

    if not latitude or not longitude:
        return redirect(url_for("driver_dashboard"))

    conn = get_db()
    assigned_bus = conn.execute("""
        SELECT s.bus_id
        FROM schedules s
        WHERE s.driver_id = ? AND s.bus_id IS NOT NULL
        ORDER BY s.date DESC, s.heure_depart DESC
        LIMIT 1
    """, (user_id,)).fetchone()

    if assigned_bus:
        conn.execute("""
            UPDATE buses
            SET current_lat = ?, current_lon = ?, dernier_arret = ?
            WHERE id = ?
        """, (latitude, longitude, dernier_arret, assigned_bus["bus_id"]))
        conn.commit()

    conn.close()
    return redirect(url_for("driver_dashboard"))

@app.route("/student")
def student_dashboard():
    if session.get("role") != "student":
        return redirect(url_for("login"))
    
    conn = get_db()
    
    # Récupérer les actualités récentes
    news = conn.execute("""
        SELECT n.*, u.nom AS admin_name,
            (SELECT COUNT(*) FROM news_comments c WHERE c.news_id = n.id) AS comment_count,
            (SELECT COUNT(*) FROM news_likes l WHERE l.news_id = n.id) AS like_count
        FROM news n
        LEFT JOIN users u ON n.admin_id = u.id
        ORDER BY n.date DESC
        LIMIT 5
    """).fetchall()
    
    # Récupérer les horaires disponibles
    schedules = conn.execute("""
        SELECT s.*, b.plaque, u.nom AS driver_name, b.capacite
        FROM schedules s 
        LEFT JOIN buses b ON s.bus_id = b.id 
        LEFT JOIN users u ON s.driver_id = u.id 
        WHERE s.disponible = 'oui'
        ORDER BY s.date ASC, s.heure_depart ASC
        LIMIT 10
    """).fetchall()
    
    # Récupérer les tarifs avec libellés de départ et destination
    routes = conn.execute("""
        SELECT r.*, l1.nom as depart, l2.nom as destination
        FROM routes r
        LEFT JOIN locations l1 ON r.depart_id = l1.id
        LEFT JOIN locations l2 ON r.destination_id = l2.id
        ORDER BY l1.nom, l2.nom
    """).fetchall()

    # Récupérer une position de bus en temps réel si disponible
    bus_current = conn.execute("""
        SELECT plaque, current_lat, current_lon, dernier_arret
        FROM buses
        WHERE current_lat IS NOT NULL AND current_lon IS NOT NULL
        ORDER BY id DESC
        LIMIT 1
    """).fetchone()
    
    # Informations de l'étudiant connecté
    user_id = session.get("user_id")
    user_info = None
    if user_id:
        user_info = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    
    conn.close()
    
    return render_template("student/dashboard.html", 
                         news=news, 
                         schedules=schedules, 
                         routes=routes,
                         bus_current=bus_current,
                         user_info=user_info)

@app.route("/api/comments/<int:news_id>")
def api_comments(news_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT c.id, c.contenu, c.date, u.nom as user_name
    FROM news_comments c
    LEFT JOIN users u ON c.user_id = u.id
    WHERE c.news_id = ?
    ORDER BY c.date DESC
    """, (news_id,))
    comments = cursor.fetchall()
    conn.close()
    return jsonify([dict(comment) for comment in comments])

# --- GESTION DES BUS ---
@app.route("/admin/buses", methods=["GET", "POST"])
def admin_buses():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    if request.method == "POST":
        plaque = request.form.get("plaque")
        capacite = request.form.get("capacite")
        statut = request.form.get("statut", "actif")
        try:
            conn.execute("INSERT INTO buses (plaque, capacite, statut) VALUES (?, ?, ?)",
                         (plaque, capacite, statut))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "Cette plaque existe déjà", 400

    buses = conn.execute("SELECT * FROM buses").fetchall()
    conn.close()
    return render_template("admin/buses.html", buses=buses)

@app.route("/admin/add_bus", methods=["POST"])
def admin_add_bus():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    plaque = request.form.get("plaque")
    capacite = request.form.get("capacite")
    statut = request.form.get("statut", "actif")
    conn = get_db()
    try:
        conn.execute("INSERT INTO buses (plaque, capacite, statut) VALUES (?, ?, ?)",
                     (plaque, capacite, statut))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "Cette plaque existe déjà", 400
    conn.close()
    return redirect(url_for("admin_buses"))

@app.route("/admin/edit_bus/<int:bus_id>", methods=["GET", "POST"])
def admin_edit_bus(bus_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        plaque = request.form.get("plaque")
        capacite = request.form.get("capacite")
        statut = request.form.get("statut")
        conn.execute("UPDATE buses SET plaque = ?, capacite = ?, statut = ? WHERE id = ?",
                     (plaque, capacite, statut, bus_id))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_buses"))
    bus = conn.execute("SELECT * FROM buses WHERE id = ?", (bus_id,)).fetchone()
    conn.close()
    return render_template("admin/edit_bus.html", bus=bus)

@app.route("/admin/delete_bus/<int:bus_id>")
def admin_delete_bus(bus_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    conn = get_db()
    conn.execute("DELETE FROM buses WHERE id = ?", (bus_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_buses"))

@app.route("/admin/drivers")
def admin_drivers():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    conn = get_db()
    drivers = conn.execute("SELECT * FROM users WHERE role = 'driver' ORDER BY nom").fetchall()
    conn.close()
    return render_template("admin/drivers.html", drivers=drivers)

@app.route("/admin/add_driver", methods=["POST"])
def admin_add_driver():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    nom = request.form.get("nom")
    telephone = request.form.get("telephone")
    permis = request.form.get("permis")
    email = request.form.get("email") or f"driver_{int(datetime.now().timestamp())}@uac"
    raw_password = request.form.get("password")
    if not nom or not telephone or not permis or not email or not raw_password:
        return "Tous les champs sont requis", 400
    password = generate_password_hash(raw_password)
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (nom, email, password, role, telephone, permis) VALUES (?, ?, ?, ?, ?, ?)",
                     (nom, email, password, "driver", telephone, permis))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "Ce chauffeur existe déjà", 400
    conn.close()
    return redirect(url_for("admin_drivers"))

@app.route("/admin/edit_driver/<int:driver_id>", methods=["GET", "POST"])
def admin_edit_driver(driver_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        nom = request.form.get("nom")
        telephone = request.form.get("telephone")
        permis = request.form.get("permis")
        raw_password = request.form.get("password")
        if raw_password:
            hashed_password = generate_password_hash(raw_password)
            conn.execute("UPDATE users SET nom = ?, telephone = ?, permis = ?, password = ? WHERE id = ?",
                         (nom, telephone, permis, hashed_password, driver_id))
        else:
            conn.execute("UPDATE users SET nom = ?, telephone = ?, permis = ? WHERE id = ?",
                         (nom, telephone, permis, driver_id))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_drivers"))
    driver = conn.execute("SELECT * FROM users WHERE id = ? AND role = 'driver'", (driver_id,)).fetchone()
    conn.close()
    return render_template("admin/edit_driver.html", driver=driver)

@app.route("/admin/delete_driver/<int:driver_id>")
def admin_delete_driver(driver_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id = ? AND role = 'driver'", (driver_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_drivers"))

@app.route("/admin/edit_user/<int:user_id>", methods=["GET", "POST"])
def admin_edit_user(user_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        nom = request.form.get("nom")
        email = request.form.get("email")
        role = request.form.get("role")
        raw_password = request.form.get("password")
        if raw_password:
            hashed_password = generate_password_hash(raw_password)
            conn.execute("UPDATE users SET nom = ?, email = ?, role = ?, password = ? WHERE id = ?",
                         (nom, email, role, hashed_password, user_id))
        else:
            conn.execute("UPDATE users SET nom = ?, email = ?, role = ? WHERE id = ?",
                         (nom, email, role, user_id))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_users"))
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return render_template("admin/edit_user.html", user=user)

@app.route("/admin/delete_user/<int:user_id>")
def admin_delete_user(user_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_users"))

@app.route("/admin/schedules", methods=["GET", "POST"])
def admin_schedules():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        bus_id = request.form.get("bus_id")
        driver_id = request.form.get("driver_id")
        date_trajet = request.form.get("date")
        heure = request.form.get("heure_depart")
        destination = request.form.get("destination")
        disponible = request.form.get("disponible", "oui")
        conn.execute("INSERT INTO schedules (bus_id, driver_id, date, heure_depart, destination, disponible) VALUES (?, ?, ?, ?, ?, ?)",
                     (bus_id, driver_id, date_trajet, heure, destination, disponible))
        conn.commit()
    buses = conn.execute("SELECT * FROM buses WHERE statut = 'actif'").fetchall()
    drivers = conn.execute("SELECT * FROM users WHERE role = 'driver'").fetchall()
    schedules = conn.execute("SELECT s.*, b.plaque, u.nom AS driver_name FROM schedules s LEFT JOIN buses b ON s.bus_id = b.id LEFT JOIN users u ON s.driver_id = u.id ORDER BY s.date DESC, s.heure_depart ASC").fetchall()
    conn.close()
    return render_template("admin/schedules.html", buses=buses, drivers=drivers, schedules=schedules)

@app.route("/admin/locations", methods=["GET", "POST"])
def admin_locations():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        nom = request.form.get("nom")
        type_ = request.form.get("type")
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")
        conn.execute("INSERT INTO locations (nom, type, latitude, longitude) VALUES (?, ?, ?, ?)",
                     (nom, type_, latitude, longitude))
        conn.commit()
    locations = conn.execute("SELECT * FROM locations ORDER BY nom").fetchall()
    conn.close()
    return render_template("admin/locations.html", locations=locations)

@app.route("/admin/edit_location/<int:loc_id>", methods=["GET", "POST"])
def admin_edit_location(loc_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        nom = request.form.get("nom")
        type_ = request.form.get("type")
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")
        conn.execute("UPDATE locations SET nom = ?, type = ?, latitude = ?, longitude = ? WHERE id = ?",
                     (nom, type_, latitude, longitude, loc_id))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_locations"))
    location = conn.execute("SELECT * FROM locations WHERE id = ?", (loc_id,)).fetchone()
    conn.close()
    return render_template("admin/edit_location.html", location=location)

@app.route("/admin/delete_location/<int:loc_id>")
def admin_delete_location(loc_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    conn = get_db()
    conn.execute("DELETE FROM locations WHERE id = ?", (loc_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_locations"))

@app.route("/admin/news", methods=["GET", "POST"])
def admin_news():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        titre = request.form.get("titre")
        contenu = request.form.get("contenu")
        image = request.files.get("image")
        image_name = save_uploaded_image(image) if image else None
        conn.execute("INSERT INTO news (titre, contenu, admin_id, image_path) VALUES (?, ?, ?, ?)",
                     (titre, contenu, session.get("user_id"), image_name))
        conn.commit()
    news_items = conn.execute("SELECT n.*, u.nom as admin_name FROM news n LEFT JOIN users u ON n.admin_id = u.id ORDER BY n.date DESC").fetchall()
    conn.close()
    return render_template("admin/news.html", news_items=news_items)

@app.route("/admin/edit_news/<int:news_id>", methods=["GET", "POST"])
def admin_edit_news(news_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        titre = request.form.get("titre")
        contenu = request.form.get("contenu")
        image = request.files.get("image")
        image_name = save_uploaded_image(image) if image else None
        if image_name:
            conn.execute("UPDATE news SET titre = ?, contenu = ?, image_path = ? WHERE id = ?",
                         (titre, contenu, image_name, news_id))
        else:
            conn.execute("UPDATE news SET titre = ?, contenu = ? WHERE id = ?",
                         (titre, contenu, news_id))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_news"))
    news_item = conn.execute("SELECT * FROM news WHERE id = ?", (news_id,)).fetchone()
    conn.close()
    return render_template("admin/edit_news.html", news=news_item)

@app.route("/admin/delete_news/<int:news_id>")
def admin_delete_news(news_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    conn = get_db()
    conn.execute("DELETE FROM news WHERE id = ?", (news_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_news"))

@app.route("/news/<int:news_id>")
def news_detail(news_id):
    conn = get_db()
    news_item = conn.execute("SELECT n.*, u.nom as admin_name FROM news n LEFT JOIN users u ON n.admin_id = u.id WHERE n.id = ?", (news_id,)).fetchone()
    comments = conn.execute("SELECT c.*, u.nom as user_name FROM news_comments c LEFT JOIN users u ON c.user_id = u.id WHERE c.news_id = ? ORDER BY c.date DESC", (news_id,)).fetchall()
    like_count = conn.execute("SELECT COUNT(*) FROM news_likes WHERE news_id = ?", (news_id,)).fetchone()[0]
    user_liked = False
    if session.get("user_id"):
        liked = conn.execute("SELECT 1 FROM news_likes WHERE news_id = ? AND user_id = ?", (news_id, session.get("user_id"))).fetchone()
        user_liked = bool(liked)
    conn.close()
    return render_template("news_detail.html", news_item=news_item, comments=comments, like_count=like_count, user_liked=user_liked)

@app.route("/news/<int:news_id>/comment", methods=["POST"])
def submit_comment(news_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    contenu = request.form.get("contenu")
    if not contenu:
        return redirect(url_for("news_detail", news_id=news_id))
    conn = get_db()
    conn.execute("INSERT INTO news_comments (news_id, user_id, contenu) VALUES (?, ?, ?)",
                 (news_id, session.get("user_id"), contenu))
    conn.commit()
    conn.close()
    return redirect(url_for("news_detail", news_id=news_id))

@app.route("/news/<int:news_id>/like", methods=["POST"])
def toggle_like(news_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    conn = get_db()
    exists = conn.execute("SELECT id FROM news_likes WHERE news_id = ? AND user_id = ?", (news_id, session.get("user_id"))).fetchone()
    if exists:
        conn.execute("DELETE FROM news_likes WHERE id = ?", (exists[0],))
    else:
        conn.execute("INSERT OR IGNORE INTO news_likes (news_id, user_id) VALUES (?, ?)", (news_id, session.get("user_id")))
    conn.commit()
    conn.close()
    return redirect(url_for("news_detail", news_id=news_id))

# --- GESTION DES TARIFS (ROUTES) ---
@app.route("/admin/routes", methods=["GET", "POST"])
def admin_routes():

    if session.get("role") != "admin":
        return redirect(url_for("login"))
    
    conn = get_db()
    if request.method == "POST":
        depart_id = request.form.get("depart_id")
        dest_id = request.form.get("destination_id")
        p_aller = request.form.get("prix_aller")
        p_retour = request.form.get("prix_retour")
        
        conn.execute("""
            INSERT INTO routes (depart_id, destination_id, prix_aller, prix_retour) 
            VALUES (?, ?, ?, ?)
        """, (depart_id, dest_id, p_aller, p_retour))
        conn.commit()
    
    routes = conn.execute("""
        SELECT r.*, l1.nom as depart, l2.nom as destination 
        FROM routes r
        JOIN locations l1 ON r.depart_id = l1.id
        JOIN locations l2 ON r.destination_id = l2.id
    """).fetchall()
    locations = conn.execute("SELECT * FROM locations").fetchall()
    conn.close()
    return render_template("admin/routes.html", routes=routes, locations=locations)

# --- GESTION DES UTILISATEURS ---
@app.route("/admin/users", methods=["GET", "POST"])
def admin_users():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    
    conn = get_db()
    if request.method == "POST":
        nom = request.form.get("nom")
        email = request.form.get("email")
        role = request.form.get("role")
        # Mot de passe par défaut : uac2026
        raw_password = request.form.get("password")
        if not nom or not email or not role or not raw_password:
            conn.close()
            return "Tous les champs sont requis", 400
        password = generate_password_hash(raw_password)
        
        try:
            conn.execute("INSERT INTO users (nom, email, password, role) VALUES (?, ?, ?, ?)",
                         (nom, email, password, role))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Cet email ou matricule existe déjà", 400
            
    users = conn.execute("SELECT * FROM users ORDER BY role").fetchall()
    conn.close()
    return render_template("admin/users.html", users=users)

@app.route("/admin/students", methods=["GET", "POST"])
def admin_students():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    
    conn = get_db()
    if request.method == "POST":
        nom = request.form.get("nom")
        email = request.form.get("email")
        password = request.form.get("password")
        if not nom or not email or not password:
            return "Tous les champs sont requis", 400
        hashed_password = generate_password_hash(password)
        try:
            conn.execute("INSERT INTO users (nom, email, password, role) VALUES (?, ?, ?, ?)",
                         (nom, email, hashed_password, "student"))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "Cet email ou matricule existe déjà", 400
    students = conn.execute("SELECT id, nom, email FROM users WHERE role = 'student' ORDER BY nom").fetchall()
    conn.close()
    return render_template("admin/students.html", students=students)

# --- AFFECTATIONS (PLANIFICATION) ---
@app.route("/admin/assignments", methods=["GET", "POST"])
def admin_assignments():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    
    conn = get_db()
    if request.method == "POST":
        bus_id = request.form.get("bus_id")
        driver_id = request.form.get("driver_id")
        date_trajet = request.form.get("date")
        heure = request.form.get("heure_depart")
        
        conn.execute("""
            INSERT INTO assignments (bus_id, driver_id, date, heure_depart) 
            VALUES (?, ?, ?, ?)
        """, (bus_id, driver_id, date_trajet, heure))
        conn.commit()
    
    # Récupérer les données pour les menus déroulants
    buses = conn.execute("SELECT * FROM buses WHERE statut = 'actif'").fetchall()
    drivers = conn.execute("SELECT * FROM users WHERE role = 'driver'").fetchall()
    
    # Liste des affectations avec jointures pour l'affichage
    assignments = conn.execute("""
        SELECT a.*, b.plaque, u.nom as chauffeur
        FROM assignments a
        JOIN buses b ON a.bus_id = b.id
        JOIN users u ON a.driver_id = u.id
        ORDER BY a.date DESC, a.heure_depart ASC
    """).fetchall()
    
    conn.close()
    return render_template("admin/assignments.html", buses=buses, drivers=drivers, assignments=assignments)

if __name__ == "__main__":
    app.run(debug=True)
