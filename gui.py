from email.mime.base import MIMEBase
from email import encoders
import os
import winsound
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
from model import train_model
from database import create_db, insert_data
from pdf_report import generate_pdf
import requests
import time

# =========================
# INITIALISATION
# =========================

create_db()

profiles = {

    "normal": [
    92, 95, 88, 100, 110, 105, 98,
    120, 125, 115, 108, 102, 99, 96,
    101, 104, 107, 109, 106, 100,
    97, 99, 103, 105, 110, 112,
    108, 104, 101, 98
],

    "hyper": [
    180, 185, 190, 160, 170, 195, 205,
    120, 130, 210, 220, 200, 195, 185,
    175, 160, 230, 240, 190, 180,
    170, 155, 200, 210, 215, 140,
    130, 225, 235, 200
],

    "hypo": [
    65, 62, 58, 55, 60, 70, 72,
    68, 66, 64, 59, 57, 55, 62,
    75, 80, 78, 60, 58, 65,
    70, 72, 74, 68, 66, 55,
    59, 61, 63, 70
],

    "instable": [
    60, 210, 70, 220, 65, 180, 90,
    240, 100, 55, 200, 75, 230, 85,
    190, 60, 220, 95, 175, 240,
    80, 65, 210, 70, 230, 90,
    180, 60, 200, 85
]
}


model = None
scaler = None

results_for_pdf = []
history_global = []

patient_info = {}
detailed_text_memory = ""
mode_affichage = "detail"


def load_patient_from_db(email):
    conn = sqlite3.connect("glycemia.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT sexe, grossesses, age, bmi, diabetique, email, telephone, profile
        FROM patient
        WHERE email=?
    """, (email,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "sexe": row[0],
            "grossesses": row[1],
            "age": row[2],
            "bmi": row[3],
            "diabetique": row[4],
            "email": row[5],
            "telephone": row[6],
            "profile": row[7]
        }

    return {}  # important


# =========================
# API FLASK
# =========================

# =========================
# FONCTIONS UTILITAIRES
# =========================
def refresh_patient():
    global patient_info
    email = patient_info.get("email", "")
    if email:
        db_data = load_patient_from_db(email)
        if db_data:
            patient_info = db_data

def get_trend(history):
    if len(history) < 2:
        return "Stable"
    if history[-1] > history[-2]:
        return "⬆️ Augmentation"
    elif history[-1] < history[-2]:
        return "⬇️ Diminution"
    return "Stable"


def check_alert(g):
    if g < 60:
        return "🚨 URGENCE HYPOGLYCÉMIE"
    elif g > 180:
        return "🚨 URGENCE HYPERGLYCÉMIE"
    elif g > 140:
        return "⚠️ Glycémie élevée"
    return ""


def get_medical_analysis(glucose, score, trend, alert, day):
    if glucose < 70:
        etat = "Hypoglycémie sévère"
        reco = "Prendre du sucre immédiatement."
    elif glucose <= 140:
        etat = "Glycémie normale"
        reco = "Continuer le suivi."
    elif glucose <= 199:
        etat = "Hyperglycémie modérée"
        reco = "Surveiller alimentation."
    else:
        etat = "Hyperglycémie sévère"
        reco = "Consulter un médecin."

    return (
        f"📅 {day}\n"
        f"📊 Glycémie: {glucose} mg/dL\n"
        f"🩺 État: {etat}\n"
        f"📈 {trend}\n"
        f"🤖 Score IA: {score*100:.2f}%\n"
        f"🚨 {alert if alert else 'Aucune alerte'}\n"
        f"💊 Recommandation: {reco}\n"
        f"{'='*60}\n\n"
    )
def send_diagnostic_with_pdf(period_name):
    sender_email = "smart.glycemie.monitor@gmail.com"
    receiver_email = patient_info.get("email", "")
    app_password = "evii tsqh fzpy dwty"

    subject = f"🩺 Diagnostic {period_name} + PDF"

    diagnostic_text = generate_summary()

    avg = sum(history_global) / len(history_global)
    max_val = max(history_global)
    min_val = min(history_global)

    score_global, interpretation, reco = calculate_ai_metrics()

    # génération du pdf
    pdf_file = create_complete_pdf()

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject

    body = f"""
Bonjour,

Veuillez trouver ci-joint le diagnostic {period_name.lower()}.

{diagnostic_text}

Cordialement,
Smart Glycémie Monitor
"""

    msg.attach(MIMEText(body, "plain", "utf-8"))

    # pièce jointe PDF
    with open(pdf_file, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())

    encoders.encode_base64(part)

    part.add_header(
        "Content-Disposition",
        f"attachment; filename={os.path.basename(pdf_file)}"
    )

    msg.attach(part)

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()

        print("✅ Diagnostic + PDF envoyé")

    except Exception as e:
        print("❌ Erreur mail PDF :", e)
        
def send_email_alert(day, glucose, alert_type):
    sender_email = "smart.glycemie.monitor@gmail.com"
    receiver_email = patient_info.get("email", "")

    # mot de passe d'application Gmail (pas le mot de passe normal)
    app_password = "evii tsqh fzpy dwty"

    subject = "🚨 Alerte glycémique détectée"

    body = f"""
Bonjour,

Une anomalie glycémique a été détectée.

📅 Jour : {day}
🩸 Taux de glycémie : {glucose} mg/dL
🚨 Type d'alerte : {alert_type}

Veuillez vérifier votre état de santé immédiatement.

Cordialement,
Système Expert IA
"""

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()

        print("✅ Email envoyé avec succès")

    except Exception as e:
        print("❌ Erreur email :", e)
        
def send_periodic_report(period_name, values):
    sender_email = "smart.glycemie.monitor@gmail.com"
    receiver_email = patient_info.get("email", "")
    app_password = "evii tsqh fzpy dwty"

    avg = sum(values) / len(values)
    max_val = max(values)
    min_val = min(values)

    subject = f"📊 Rapport {period_name} - Smart Glycémie Monitor"

    body = f"""
Bonjour,

Veuillez trouver ci-dessous le rapport {period_name.lower()}.

📈 Nombre de mesures : {len(values)}
📊 Moyenne glycémique : {avg:.2f} mg/dL
🔺 Valeur maximale : {max_val} mg/dL
🔻 Valeur minimale : {min_val} mg/dL

Merci de consulter votre évolution.

Cordialement,
Smart Glycémie Monitor
"""

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()

        print(f"✅ Rapport {period_name} envoyé")

    except Exception as e:
        print("❌ Erreur rapport :", e)

def send_diagnostic_email(period_name):
    sender_email = "smart.glycemie.monitor@gmail.com"
    receiver_email = patient_info.get("email", "")
    app_password = "evii tsqh fzpy dwty"

    subject = f"🩺 Diagnostic {period_name} - Smart Glycémie Monitor"

    diagnostic_text = generate_summary()

    body = f"""
Bonjour,

Veuillez trouver ci-dessous le diagnostic {period_name.lower()} généré par le système IA.

{diagnostic_text}

Cordialement,
Smart Glycémie Monitor
"""

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()

        print(f"✅ Diagnostic {period_name} envoyé avec succès")

    except Exception as e:
        print("❌ Erreur envoi diagnostic :", e)

def send_alert_notification(message):
    print("ALERTE ENVOYÉE :", message)


notifications = []
notification_height = 80
notification_spacing = 10
max_notifications = 5

def play_alert_sound():
    try:
        winsound.Beep(1200, 600)
    except:
        pass

def trigger_alert(title, message, glucose):

    play_alert_sound()

    show_popup_alert(title, message, glucose)

    try:

        requests.post(
    https://smart-glycemie-api.onrender.com/add_alert",
    json={
        "email": patient_info.get("email", ""),
        "title": title,
        "message": message,
        "glucose": glucose
    }
)

    except Exception as e:

        print("Erreur API alert :", e)

def show_popup_alert(title, message, glucose):
    play_alert_sound()  # 🔊 son conservé

    notif = tk.Frame(
        root,
        bg="#d9534f",
        bd=0,
        highlightthickness=0
    )

    tk.Label(
        notif,
        text=f"🚨 {title}\n{message}\n🩸 {glucose} mg/dL",
        font=("Segoe UI", 10, "bold"),
        fg="white",
        bg="#d9534f",
        justify="left"
    ).pack(padx=10, pady=8)

    notif.place_forget()

    notifications.append(notif)
    reposition_notifications()

    # disparition automatique après 5s
    root.after(5000, lambda: remove_notification(notif))

def reposition_notifications():
    root.update_idletasks()

    width = 320
    x = root.winfo_width() - width - 20

    for i, notif in enumerate(reversed(notifications)):
        y = root.winfo_height() - 20 - ((i + 1) * (notification_height + 10))

        notif.place(
            x=x,
            y=y,
            width=width,
            height=notification_height
        )


def remove_notification(notif):
    global notifications

    if notif in notifications:
        notifications.remove(notif)
        notif.destroy()
        reposition_notifications()

def open_patient_sheet():
    refresh_patient()  
    
    sheet = tk.Toplevel(root)
    sheet.title("Fiche Patient")
    sheet.geometry("420x450")
    sheet.configure(bg="white")
    sheet.resizable(False, False)

    tk.Label(
        sheet,
        text="🩺 FICHE PATIENT",
        font=("Segoe UI", 14, "bold"),
        bg="white",
        fg="#0C254A"
    ).pack(pady=15)

    fields = {}

# =========================
# SEXE
# =========================

    frame_sexe = tk.Frame(sheet, bg="white")
    frame_sexe.pack(fill="x", padx=20, pady=6)

    tk.Label(frame_sexe, text="Sexe :", width=15, anchor="w",
         font=("Segoe UI", 10, "bold"), bg="white").pack(side="left")

    combo_sexe = ttk.Combobox(frame_sexe, values=["Homme", "Femme"], state="readonly")
    sexe_db = patient_info.get("sexe", "")
    if sexe_db.lower() not in ["homme", "femme"]:
        sexe_db = "Homme"
    combo_sexe.set(sexe_db)
    combo_sexe.pack(side="left", fill="x", expand=True)

    fields["sexe"] = combo_sexe


# =========================
# GROSSESSES مباشرة تحت SEXE
# =========================

    grossesse_frame = tk.Frame(sheet, bg="white")
    grossesse_frame.pack(fill="x", padx=20, pady=6)   # 👈 ICI IMPORTANT

    tk.Label(grossesse_frame, text="Grossesses :", width=15,
         anchor="w", font=("Segoe UI", 10, "bold"),
         bg="white").pack(side="left")

    grossesse_entry = tk.Entry(grossesse_frame, font=("Segoe UI", 10))
    grossesse_entry.insert(0, str(patient_info.get("grossesses", 0)))
    grossesse_entry.pack(side="left", fill="x", expand=True)

    fields["grossesses"] = grossesse_entry
# =========================
# PROFILE
# =========================

    profile_frame = tk.Frame(sheet, bg="white")
    profile_frame.pack(fill="x", padx=20, pady=6)

       

    current_profile = patient_info.get("profile", "normal")

    if current_profile == "":
        current_profile = "normal"

# =========================
# AUTRES CHAMPS
# =========================

    labels = [
        ("Âge", "age"),
        ("BMI", "bmi"),
        ("Diabétique", "diabetique"),
        ("Email", "email"),
        ("Téléphone", "telephone")
    ]

    for label_text, key in labels:
        frame = tk.Frame(sheet, bg="white")
        frame.pack(fill="x", padx=20, pady=6)
        tk.Label(
            frame,
            text=label_text + " :",
            width=15,
            anchor="w",
            font=("Segoe UI", 10, "bold"),
            bg="white"
        ).pack(side="left")

        entry = tk.Entry(frame, font=("Segoe UI", 10))
        entry.insert(0, str(patient_info.get(key, "")))
        entry.pack(side="left", fill="x", expand=True)

        fields[key] = entry

# =========================
# AFFICHER/CACHER GROSSESSES
# =========================

    def update_grossesse(*args):

        if combo_sexe.get() == "Femme":
            grossesse_frame.pack(fill="x", padx=20, pady=6)
        else:
            grossesse_frame.pack_forget()

    combo_sexe.bind("<<ComboboxSelected>>", update_grossesse)

# affichage initial
    update_grossesse()


    def save_patient():
        global patient_info

        data = {key: fields[key].get() for key in fields}
        data["sexe"] = combo_sexe.get()

    # =========================
    # PROFILE AUTO DIFFERENT
    # =========================

        profiles_list = ["normal", "hyper", "hypo", "instable"]

        conn = sqlite3.connect("glycemia.db")
        cursor = conn.cursor()

        cursor.execute("""
    SELECT profile
    FROM patient
    ORDER BY id DESC
    LIMIT 1
            """)

        last_profile_row = cursor.fetchone()
        conn.close()

        if last_profile_row:
            last_profile = last_profile_row[0]

            available_profiles = [
                p for p in profiles_list
                if p != last_profile
            ]

            data["profile"] = random.choice(available_profiles)

        else:
            data["profile"] = random.choice(profiles_list)

        try:
            response = requests.post(
                https://smart-glycemie-api.onrender.com/update_patient",
                json=data
            )

            if response.status_code == 200:
                patient_info.update(data)

                messagebox.showinfo(
                "Succès",
                "Fiche patient synchronisée et mise à jour !"
                )

                refresh_display()
                sheet.destroy()

            else:
                messagebox.showerror(
                "Erreur",
                "Le serveur a retourné une erreur."
            )

        except Exception as e:
            messagebox.showerror(
            "Erreur de connexion",
            f"Impossible de joindre le serveur : {e}"
        )
    tk.Button(
        sheet,
        text="💾 Enregistrer",
        font=("Segoe UI", 10, "bold"),
        bg="#0C254A",
        fg="white",
        command=save_patient
    ).pack(pady=20)
# =========================
# IA ET SYNTHÈSE
# =========================

def calculate_ai_metrics():
    if not history_global:
        return 0, "N/A", "Aucune donnée"

    max_val = max(history_global)
    min_val = min(history_global)

    patient_base = [2, 100, 70, 20, 85, 25, 0.5, 30]
    scores = []

    for g in history_global:
        patient = list(patient_base)
        patient[1] = g
        prob = model.predict(
            scaler.transform([patient]),
            verbose=0
        )[0][0]
        scores.append(prob)

    score_global = sum(scores) / len(scores)

    if max_val > 200 and min_val < 60:
        interpretation = "INSTABILITÉ CRITIQUE"
        reco = "⚠️ Fortes variations détectées."
    elif min_val < 60:
        interpretation = "RISQUE D'HYPOGLYCÉMIE"
        reco = "Alerte glycémie basse."
    elif max_val > 200:
        interpretation = "HYPERGLYCÉMIE SÉVÈRE"
        reco = "Pic glycémique dangereux."
    else:
        interpretation = "SAIN / STABLE"
        reco = "Continuez votre suivi."

    return score_global, interpretation, reco


def generate_summary():
    if not history_global:
        return "Aucune donnée disponible."

    score_global, interpretation, reco = calculate_ai_metrics()

    avg = sum(history_global) / len(history_global)
    max_val = max(history_global)
    min_val = min(history_global)

    # Comptage des anomalies
    hypo_count = len([x for x in history_global if x < 70])
    hyper_count = len([x for x in history_global if x > 180])
    high_count = len([x for x in history_global if 140 < x <= 180])
    normal_count = len([x for x in history_global if 70 <= x <= 140])

    # Evaluation globale
    if avg < 70:
        etat_general = "RISQUE D’HYPOGLYCÉMIE CHRONIQUE"
    elif avg <= 140:
        etat_general = "ÉQUILIBRE GLYCÉMIQUE SATISFAISANT"
    elif avg <= 180:
        etat_general = "HYPERGLYCÉMIE MODÉRÉE"
    else:
        etat_general = "INSTABILITÉ GLYCÉMIQUE SÉVÈRE"

    return (
        "====================================================\n"
        "      RAPPORT GLOBAL DE DIAGNOSTIC MÉDICAL IA       \n"
        "====================================================\n\n"

        "[INFORMATIONS PATIENT]\n"
        f"• Sexe : {patient_info.get('sexe', 'N/A')}\n"
        f"• Âge : {patient_info.get('age', 'N/A')} ans\n"
        f"• BMI : {patient_info.get('bmi', 'N/A')}\n"
        f"• Grossesses          : {patient_info['grossesses'] if patient_info['sexe'].lower() == 'femme' else 'N/A'}\n"
        f"• Diabétique          : {patient_info['diabetique']}\n\n"

        "[INDICATEURS CLINIQUES]\n"
        f"• Nombre de jours     : {len(history_global)}\n"
        f"• Moyenne glycémique  : {avg:.2f} mg/dL\n"
        f"• Valeur maximale     : {max_val} mg/dL\n"
        f"• Valeur minimale     : {min_val} mg/dL\n"
        f"• Valeurs normales    : {normal_count}\n"
        f"• Hyperglycémies      : {high_count}\n"
        f"• Pics critiques      : {hyper_count}\n"
        f"• Hypoglycémies       : {hypo_count}\n\n"

        "[ANALYSE]\n"
        f"• Score de risque     : {score_global*100:.2f}%\n"
        f"• Interprétation   : {interpretation}\n"
        f"• État global         : {etat_general}\n\n"

        "[DIAGNOSTIC MÉDICAL]\n"
        "Le profil glycémique met en évidence "
        f"{hyper_count} épisode(s) d’hyperglycémie sévère "
        f"et {hypo_count} épisode(s) d’hypoglycémie.\n"
        "L’évolution observée suggère une surveillance "
        "rapprochée du patient afin de prévenir tout "
        "déséquilibre métabolique.\n\n"

        "[RECOMMANDATIONS CLINIQUES]\n"
        f"• {reco}\n"
        "• Maintenir un suivi glycémique quotidien.\n"
        "• Contrôle alimentaire conseillé.\n"
        "• Consultation médicale si pics répétés.\n"
        "====================================================\n"
    )


# =========================
# AFFICHAGE
# =========================

def refresh_display():
    text_analysis.config(state="normal")
    text_analysis.delete("1.0", tk.END)

    if mode_affichage == "detail":
        content = detailed_text_memory
    else:
        content = generate_summary()

    text_analysis.insert(tk.END, content)

    # titre principal
    text_analysis.tag_add("title", "1.0", "2.end")

    # sections importantes
    sections = [
        "[INFORMATIONS PATIENT]",
        "[INDICATEURS CLINIQUES]",
        "[ANALYSE]",
        "[DIAGNOSTIC MÉDICAL]",
        "[RECOMMANDATIONS CLINIQUES]"
    ]

    for section in sections:
        start = "1.0"
        while True:
            pos = text_analysis.search(section, start, tk.END)
            if not pos:
                break
            end = f"{pos}+{len(section)}c"
            text_analysis.tag_add("section", pos, end)
            start = end

    # coloration états critiques
    keywords_red = [
        "INSTABILITÉ CRITIQUE",
        "HYPERGLYCÉMIE SÉVÈRE",
        "RISQUE D’HYPOGLYCÉMIE"
    ]

    for word in keywords_red:
        start = "1.0"
        while True:
            pos = text_analysis.search(word, start, tk.END)
            if not pos:
                break
            end = f"{pos}+{len(word)}c"
            text_analysis.tag_add("critical", pos, end)
            start = end

    text_analysis.config(state="disabled")


def show_detail():
    global mode_affichage
    mode_affichage = "detail"
    refresh_display()


def show_summary():
    global mode_affichage
    mode_affichage = "resume"
    refresh_display()


def reset_data():
    global history_global, detailed_text_memory, notifications

    history_global.clear()
    detailed_text_memory = ""

    text_diag_detail.delete("1.0", tk.END)
    text_analysis.delete("1.0", tk.END)

    ax.clear()
    canvas.draw()

    # supprimer toutes les alertes
    for notif in notifications:
        notif.destroy()

    notifications.clear()

    notification_frame.place_forget()


# =========================
# SIMULATION
# =========================
def start_simulation():
    print("🚀 Bouton cliqué - démarrage analyse")

    global model, scaler

    try:
        if not patient_info:
            messagebox.showwarning(
        "Patient",
        "Veuillez remplir la fiche patient."
            )
            return
        if model is None or scaler is None:
            print("🧠 Entraînement du modèle...")
            model, scaler = train_model()

        thread = threading.Thread(target=simulate)
        thread.start()

    except Exception as e:
        print("❌ Erreur start_simulation :", e)
        messagebox.showerror("Erreur", str(e))

def simulate():
    global detailed_text_memory

    try:

        history_global.clear()
        detailed_text_memory = ""
        text_diag_detail.delete("1.0", tk.END)

        history = []

        patient_profile = patient_info.get("profile")

        if not patient_profile:
            patient_profile = "normal"

        glucose_values = profiles.get(
            patient_profile,
            profiles["normal"]
        )

        global days_labels

        days_labels = [
            f"Jour {i+1}"
            for i in range(len(glucose_values))
        ]

        for i, g in enumerate(glucose_values):

            try:

                current_day = days_labels[i]

                # sauvegarde database
                insert_data(
                    patient_info.get("email", ""),
                    current_day,
                    g,
                    "Simulation"
                )

                # rapport hebdomadaire
                if (i + 1) % 7 == 0:

                    avg = sum(history_global) / len(history_global)
                    max_val = max(history_global)
                    min_val = min(history_global)

                    score_global, interpretation, reco = \
                        calculate_ai_metrics()

                    summary_text = generate_summary()

                    try:

                        pdf_file = generate_pdf(
                            history_global,
                            avg,
                            max_val,
                            min_val,
                            score_global,
                            interpretation,
                            reco,
                            patient_info,
                            summary_text,
                            report_name=f"{patient_info['email']}_Semaine_{(i + 1)//7}"
                        )

                        print(f"✅ Rapport semaine {(i + 1)//7} créé")

                    except Exception as e:
                        print("❌ Erreur PDF semaine :", e)

                pregnancies = (
                    int(patient_info["grossesses"])
                    if patient_info["sexe"].lower() == "femme"
                    else 0
                )

                current_patient = [
                    pregnancies,
                    g,
                    80,
                    25,
                    100,
                    float(patient_info["bmi"]),
                    0.5,
                    int(patient_info["age"])
                ]

                prob = model.predict(
                    scaler.transform([current_patient]),
                    verbose=0
                )[0][0]

                history.append(g)
                history_global.append(g)

                trend = get_trend(history)
                alert = check_alert(g)

                # alertes
                if g > 180:

                    trigger_alert(
                        "ALERTE GLYCÉMIQUE",
                        "Pic détecté",
                        g
                    )

                    send_alert_notification(
                        f"Pic détecté ({g} mg/dL)"
                    )

                    send_email_alert(
                        current_day,
                        g,
                        "Hyperglycémie"
                    )

                elif g < 60:

                    trigger_alert(
                        "ALERTE GLYCÉMIQUE",
                        "Hypoglycémie détectée",
                        g
                    )

                    send_alert_notification(
                        f"Hypoglycémie détectée ({g} mg/dL)"
                    )

                    send_email_alert(
                        current_day,
                        g,
                        "Hypoglycémie"
                    )

                # diagnostic
                diag = get_medical_analysis(
                    g,
                    prob,
                    trend,
                    alert,
                    current_day
                )
                # ✅ mise à jour diagnostic en temps réel
                root.after(0, refresh_display)

                # ✅ mise à jour graphe en temps réel
                root.after(0, lambda h=history.copy(): update_graph(h))

                # ✅ animation lente
                time.sleep(0.5)
                detailed_text_memory += diag

                color = "red" if alert else "green"

                root.after(
                    0,
                    lambda d=current_day, val=g, tr=trend, al=alert, c=color:
                    text_diag_detail.insert(
                        tk.END,
                        f"[{d}] {val} mg/dL | {tr} | {al}\n",
                        c
                    )
                )

                text_diag_detail.tag_config(
                    "red",
                    foreground="red"
                )

                text_diag_detail.tag_config(
                    "green",
                    foreground="green"
                )

            except Exception as e:
                print(f"❌ Erreur jour {i+1} :", e)


        avg = sum(history_global) / len(history_global)
        max_val = max(history_global)
        min_val = min(history_global)

        score_global, interpretation, reco = calculate_ai_metrics()

        summary_text = generate_summary()

        # rapport mensuel
        try:

            generate_pdf(
                history_global,
                avg,
                max_val,
                min_val,
                score_global,
                interpretation,
                reco,
                patient_info,
                summary_text,
                report_name=f"{patient_info['email']}_Rapport_Mensuel"
            )

            print("✅ Rapport mensuel créé")

        except Exception as e:
            print("❌ Erreur rapport mensuel :", e)

    except Exception as e:

        print("❌ Erreur générale simulation :", e)

        messagebox.showerror(
            "Erreur Simulation",
            str(e)
        )


def update_graph(values):

    ax.clear()
    ax.set_ylim(40, 260)
    # sécurité si liste vide
    if not values:
        canvas.draw()
        return

    x = list(range(len(values)))

    ax.plot(
        x,
        values,
        marker='o',
        color='#0C254A',
        linewidth=2,
        label="Glycémie"
    )

    ax.axhline(
        y=70,
        color='red',
        linestyle='--',
        linewidth=1.5,
        label="Seuil HYPO"
    )

    ax.axhline(
        y=180,
        color='red',
        linestyle='-.',
        linewidth=1.5,
        label="Seuil PIC"
    )

    hypo_x = []
    hypo_y = []
    pic_x = []
    pic_y = []

    for i, v in enumerate(values):

        if v < 70:
            hypo_x.append(i)
            hypo_y.append(v)

        elif v > 180:
            pic_x.append(i)
            pic_y.append(v)

    ax.scatter(hypo_x, hypo_y, marker='v', s=80, label="Hypo")
    ax.scatter(pic_x, pic_y, marker='^', s=80, label="Pic")

    # ticks sécurisés
    ticks = x[::2]
    labels = days_labels[::2]

    if len(ticks) == len(labels):
        ax.set_xticks(ticks)
        ax.set_xticklabels(labels, rotation=45)

    ax.set_title("Suivi Glycémique Journalier")
    ax.set_xlabel("Jours")
    ax.set_ylabel("mg/dL")

    ax.legend(loc="upper left", fontsize=8)

    fig.tight_layout()

    canvas.draw()

def create_complete_pdf():
    if not history_global:
        return None

    score_global, interpretation, reco = calculate_ai_metrics()

    avg = sum(history_global) / len(history_global)
    max_val = max(history_global)
    min_val = min(history_global)

    summary_text = generate_summary()

    pdf_file = generate_pdf(
    history_global,
    avg,
    max_val,
    min_val,
    score_global,
    interpretation,
    reco,
    patient_info,
    summary_text
)

    return pdf_file

def save_report():
    if not history_global:
        messagebox.showwarning(
            "Aucune donnée",
            "Veuillez d'abord lancer une analyse."
        )
        return

    score_global, interpretation, reco = calculate_ai_metrics()

    avg = sum(history_global) / len(history_global)
    max_val = max(history_global)
    min_val = min(history_global)

    try:
        pdf_file = create_complete_pdf()

        messagebox.showinfo(
        "Succès",
        f"PDF enregistré : {pdf_file}"
    )

    except Exception as e:
        messagebox.showerror(
        "Erreur PDF",
        f"Erreur lors de l'export : {e}"
    )



# =========================
# INTERFACE
# =========================

root = tk.Tk()
root.title("Système Expert de Diagnostic Diabétologie")
root.geometry("1200x850")
root.configure(bg="#f0f2f5")

# =========================
# HEADER
# =========================

header = tk.Frame(root, bg="#0C254A", pady=12)
header.pack(fill="x")

tk.Label(
    header,
    text="Smart Glycémie Monitor",
    font=("Segoe UI", 18, "bold"),
    fg="white",
    bg="#0C254A"
).pack()

# =========================
# BARRE D’OUTILS
# =========================

tools = tk.Frame(root, bg="#e1e4e8", pady=8)
tools.pack(fill="x")

tk.Button(
    tools,
    text="🚀 Démarrer Analyse",
    command=start_simulation,
    font=("Segoe UI", 11, "bold"),
    padx=15,
    pady=8,
    width=15
).pack(side="left", padx=15)

tk.Button(
    tools,
    text="📄 Exporter PDF",
    command=save_report,
    font=("Segoe UI", 11, "bold"),
    padx=15,
    pady=8,
    width=13
).pack(side="left", padx=10)

tk.Button(
    tools,
    text="🗑️ Reset",
    command=reset_data,
    font=("Segoe UI", 11, "bold"),
    padx=15,
    pady=8,
    width=12
).pack(side="left", padx=10)

tk.Button(
    tools,
    text="🩺 Fiche Patient",
    command=open_patient_sheet,
    font=("Segoe UI", 11, "bold"),
    padx=15,
    pady=8,
    width=13
).pack(side="right", padx=20)

# =========================
# ZONES PRINCIPALES
# =========================

main_v_paned = tk.PanedWindow(
    root,
    orient=tk.VERTICAL,
    sashwidth=4,
    bg="#d0d0d0"
)
main_v_paned.pack(fill="both", expand=True)

top_h_paned = tk.PanedWindow(
    main_v_paned,
    orient=tk.HORIZONTAL,
    sashwidth=4,
    bg="#d0d0d0"
)
main_v_paned.add(top_h_paned, height=380)

# =========================
# ZONE HAUT GAUCHE
# =========================

frame_quick = tk.Frame(top_h_paned, bg="white")

text_diag_detail = tk.Text(
    frame_quick,
    font=("Segoe UI", 11),
    wrap="word"
)
text_diag_detail.pack(fill="both", expand=True)

top_h_paned.add(frame_quick, width=500)

# =========================
# GRAPHE
# =========================

frame_graph = tk.Frame(top_h_paned, bg="white")

fig, ax = plt.subplots(figsize=(4.5, 3))

canvas = FigureCanvasTkAgg(fig, master=frame_graph)
canvas.get_tk_widget().pack(fill="both", expand=True)

top_h_paned.add(frame_graph)

# =========================
# ZONE ANALYSE BAS
# =========================

frame_analysis = tk.Frame(main_v_paned, bg="white")

# =========================
# MENU BAS
# =========================
menu_bottom = tk.Frame(frame_analysis, bg="#e1e4e8", pady=5)
menu_bottom.pack(fill="x")

btn_resume = tk.Button(
    menu_bottom,
    text="📄 Résumé",
    command=show_summary,
    font=("Segoe UI", 10, "bold"),
    padx=12,
    pady=5
)
btn_resume.pack(side="left", padx=10)

btn_global = tk.Button(
    menu_bottom,
    text="🩺 Diagnostic Détaillé",
    command=show_detail,
    font=("Segoe UI", 10, "bold"),
    padx=12,
    pady=5
)
btn_global.pack(side="left", padx=10)

# =========================
# ZONE TEXTE BAS
# =========================
text_analysis = tk.Text(
    frame_analysis,
    font=("Segoe UI", 11),
    wrap="word"
)
text_analysis.pack(fill="both", expand=True)

main_v_paned.add(frame_analysis)

# =========================
# NOTIFICATIONS
# =========================

notification_frame = tk.Frame(
    root,
    bg="#d9534f",
    bd=0,
    highlightthickness=0
)

notification_label = tk.Label(
    notification_frame,
    text="",
    font=("Segoe UI", 11, "bold"),
    fg="white",
    bg="#d9534f",
    padx=13,
    pady=5,
    justify="left"
)

notification_label.pack(fill="both", expand=True)
notification_frame.place_forget()

root.mainloop()