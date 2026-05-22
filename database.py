
import sqlite3

DB_NAME = "glycemia.db"


def create_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # =========================
    # TABLE GLYCEMIA
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS glycemia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        date TEXT,
        value INTEGER,
        source TEXT,
        UNIQUE(email, date)
    )
    """)

    # =========================
    # TABLE PATIENT
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patient (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    sexe TEXT,
    grossesses INTEGER,
    age INTEGER,
    bmi REAL,
    diabetique TEXT,
    telephone TEXT,
    profile TEXT DEFAULT 'normal'
)
    """)

    # =========================
    # TABLE ALERTS
    # =========================
    cursor.execute("""
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
    title TEXT,
    message TEXT,
    glucose INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

    # =========================
    # TABLE USERS
    # =========================
    cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    password TEXT
)
""")



    # =========================
    # DEFAULT USER
    # =========================
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO users(email, password)
        VALUES('test@gmail.com', '1234')
        """)

    conn.commit()
    conn.close()

    
# =========================
# INSERT DATA
# =========================
def insert_data(email, date, value, source):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT INTO glycemia (email, date, value, source)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(email, date)
    DO UPDATE SET
        value = excluded.value,
        source = excluded.source
    """, (email, date, value, source))

    conn.commit()
    conn.close()

# =========================
# GET ALL DATA
# =========================
def get_data():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT value FROM glycemia")
    data = [row[0] for row in cursor.fetchall()]

    conn.close()
    return data


# =========================
# GET FULL DATA (optionnel utile API)
# =========================
def get_all_records(email):

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT date, value, source
    FROM glycemia
    WHERE email=?
    ORDER BY id DESC
    """, (email,))

    rows = cursor.fetchall()

    conn.close()

    return [
        {
            "date": r[0],
            "value": r[1],
            "source": r[2]
        }
        for r in rows
    ]