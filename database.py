import os
import sqlite3
import psycopg2

def get_connection():

    db_url = os.getenv("DATABASE_URL")

    if db_url:
        return psycopg2.connect(db_url)

    return sqlite3.connect("glycemia.db")
# =========================
# CREATE DATABASE
# =========================

def create_db():

    conn = get_connection()
    cursor = conn.cursor()

    # =========================
    # TABLE GLYCEMIA
    # =========================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS glycemia (
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
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
        VALUES(%s, %s)
        """, ('test@gmail.com', '1234'))

    conn.commit()
    conn.close()

# =========================
# INSERT DATA
# =========================

def insert_data(email, date, value, source):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO glycemia (
        email,
        date,
        value,
        source
    )
    VALUES (%s, %s, %s, %s)

    ON CONFLICT(email, date)
    DO UPDATE SET
        value = EXCLUDED.value,
        source = EXCLUDED.source
    """, (email, date, value, source))

    conn.commit()
    conn.close()

# =========================
# GET DATA
# =========================

def get_data():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT value FROM glycemia")

    data = [row[0] for row in cursor.fetchall()]

    conn.close()

    return data

# =========================
# GET ALL RECORDS
# =========================

def get_all_records(email):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT date, value, source
    FROM glycemia
    WHERE email=%s
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