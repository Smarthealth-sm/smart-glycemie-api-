from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import sqlite3
import os
import glob
from database import create_db
import random
create_db()

app = Flask(__name__)
CORS(app)
BASE_URL = "https://smart-glycemie-api.onrender.com"
# =========================
# ALERTS STORAGE (RAM)
# =========================
alerts = []
# =========================
# PATIENT LOGIC (AJOUT ICI)
# =========================
def update_patient_logic(patient):
    if patient.get("sexe", "").lower() == "homme":
        patient["grossesses"] = 0
    return patient
# =========================
# GLYCEMIA DATA
# =========================
@app.route('/glycemia', methods=['GET'])
def get_glycemia():

    email = request.args.get("email")

    conn = sqlite3.connect("glycemia.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT date, value
        FROM glycemia
        WHERE email=?
        ORDER BY id DESC
        LIMIT 30
    """, (email,))

    rows = cursor.fetchall()

    conn.close()

    return jsonify([
        {
            "date": r[0],
            "value": r[1]
        }
        for r in rows
    ])

@app.route("/login", methods=["POST"])
def login():

    data = request.json

    email = data.get("email")
    password = data.get("password")

    conn = sqlite3.connect("glycemia.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM users
        WHERE email=? AND password=?
    """, (email, password))

    user = cursor.fetchone()

    conn.close()

    if user:
        return jsonify({
        "success": True,
        "email": email
    })

    return jsonify({
        "success": False
    }), 401
# =========================
# PATIENT
# =========================
@app.route("/patient", methods=["GET"])
def get_patient():

    email = request.args.get("email")

    conn = sqlite3.connect("glycemia.db")
    cursor = conn.cursor()

    cursor.execute("""
SELECT sexe, grossesses, age, bmi, diabetique, email, telephone, profile
FROM patient
WHERE email=?
ORDER BY rowid DESC
LIMIT 1
""", (email,))
    print("EMAIL RECEIVED:", email)
    row = cursor.fetchone()

    conn.close()

    if row:

        patient = {
            "sexe": row[0],
            "grossesses": row[1],
            "age": row[2],
            "bmi": row[3],
            "diabetique": row[4],
            "email": row[5],
            "telephone": row[6],
            "profile": row[7]
        }

        patient = update_patient_logic(patient)

        return jsonify(patient)

    return jsonify({})

# =========================
# SIGNUP
# =========================
@app.route("/signup", methods=["POST"])
def signup():

    try:

        data = request.json

        email = data.get("email")
        password = data.get("password")

        conn = sqlite3.connect("glycemia.db")
        cursor = conn.cursor()

        # =========================
        # vérifier user existe déjà
        # =========================
        cursor.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            conn.close()

            return jsonify({
                "success": False,
                "message": "Compte existe déjà"
            }), 400

        # =========================
        # créer user
        # =========================
        cursor.execute(
            "INSERT INTO users(email, password) VALUES(?, ?)",
            (email, password)
        )

        # =========================
        # vérifier patient existe déjà
        # =========================
        cursor.execute(
            "SELECT * FROM patient WHERE email=?",
            (email,)
        )

        existing_patient = cursor.fetchone()

        # =========================
        # créer patient seulement si absent
        # =========================
        if not existing_patient:

            cursor.execute("""
            INSERT INTO patient (
                email,
                sexe,
                grossesses,
                age,
                bmi,
                diabetique,
                telephone,
                profile
            )
            VALUES (?, ?, 0, 0, 0, 'non', '', 'normal')
            """, (email,))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True
        })

    except Exception as e:

        print("ERREUR SIGNUP :", e)

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
# =========================
# UPDATE PATIENT
# =========================
@app.route("/update_patient", methods=["POST"])
def update_patient():

    data = request.json

    email = data.get("email")

    conn = sqlite3.connect("glycemia.db")
    cursor = conn.cursor()

    # =========================
    # vérifier patient existe
    # =========================
    cursor.execute(
        "SELECT * FROM patient WHERE email=?",
        (email,)
    )

    existing_patient = cursor.fetchone()

    # =========================
    # UPDATE si existe
    # =========================
    if existing_patient:

        cursor.execute("""
        UPDATE patient
        SET
            sexe=?,
            grossesses=?,
            age=?,
            bmi=?,
            diabetique=?,
            telephone=?
        WHERE email=?
    """, (
        data["sexe"],
        data["grossesses"],
        data["age"],
        data["bmi"],
        data["diabetique"],
        data["telephone"],
        email
    ))

    # =========================
    # INSERT sinon
    # =========================
    else:

        cursor.execute("""
            INSERT INTO patient(
                sexe,
                grossesses,
                age,
                bmi,
                diabetique,
                email,
                telephone,
                profile
            )
            VALUES (?, ?, ?, ?, ?, ?, ?,?)
        """, (
            data.get("sexe", ""),
            data.get("grossesses", 0),
            data.get("age", 0),
            data.get("bmi", 0),
            data.get("diabetique", ""),
            email,
            data.get("telephone", ""),
            data.get("profile", ""),
        ))

    conn.commit()
    conn.close()

    return jsonify({"success": True})

# =========================
# ALERTS
# =========================
@app.route('/alerts', methods=['GET'])
def get_alerts():

    email = request.args.get("email")

    conn = sqlite3.connect("glycemia.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT title, message, glucose
        FROM alerts
        WHERE email=?
        ORDER BY id DESC
    """, (email,))

    rows = cursor.fetchall()

    conn.close()

    return jsonify([
        {
            "title": r[0],
            "message": r[1],
            "glucose": r[2]
        }
        for r in rows
    ])

@app.route('/add_alert', methods=['POST'])
def add_alert():

    data = request.json

    conn = sqlite3.connect("glycemia.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO alerts (
            email,
            title,
            message,
            glucose
        )
        VALUES (?, ?, ?, ?)
    """, (
        data.get("email"),
        data.get("title"),
        data.get("message"),
        data.get("glucose")
    ))

    conn.commit()
    conn.close()

    return jsonify({"success": True})


# =========================
# PDF LIST
# =========================
@app.route("/pdfs")
def get_pdfs():

    email = request.args.get("email")

    folder = os.path.join(os.getcwd(), "pdfs")

    if not os.path.exists(folder):
        return jsonify([])

    files = glob.glob(os.path.join(folder, "*.pdf"))

    rapports = []

    for file in files:

        filename = os.path.basename(file)

        # ✅ غير ملفات هذا اليوزر
        if not filename.startswith(email):
            continue

        lower = filename.lower()

        if "semaine" in lower:

            rapports.append({
                "type": "week",
                "title": filename,
                "file": filename,
                "view_url": f"{BASE_URL}/view/{filename}",
                "download_url": f"{BASE_URL}/download/{filename}"
            })

        elif "mensuel" in lower:

            rapports.append({
                "type": "month",
                "title": "Rapport Mensuel",
                "file": filename,
                "view_url": f"{BASE_URL}/view/{filename}",
                "download_url": f"{BASE_URL}/download/{filename}"
            })

    return jsonify(rapports)


# =========================
# DOWNLOAD / VIEW PDF
# =========================
@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory("pdfs", filename, as_attachment=True)


@app.route("/view/<filename>")
def view_file(filename):
    return send_from_directory("pdfs", filename)


# =========================
# START SERVER
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)