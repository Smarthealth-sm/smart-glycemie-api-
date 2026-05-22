import pandas as pd  # Manipulation des données (DataFrame)
from sklearn.model_selection import train_test_split  # Division des données en train/test
from sklearn.preprocessing import StandardScaler  # Normalisation des données
from tensorflow.keras.models import Sequential  # Modèle de réseau de neurones séquentiel
from tensorflow.keras.layers import Dense  # Couches du réseau (neurones)

def train_model():
    """
    Cette fonction entraîne un modèle de Deep Learning pour prédire
    le risque de diabète à partir de données médicales.
    """

    # Dataset Pima Indians (dataset standard utilisé en recherche sur le diabète)
    url = "https://raw.githubusercontent.com/jbrownlee/Datasets/master/pima-indians-diabetes.data.csv"

    # Noms des colonnes (features médicales)
    columns = [
        "Pregnancies",  # Nombre de grossesses
        "Glucose",  # Taux de glucose
        "BloodPressure",  # Pression artérielle
        "SkinThickness",  # Épaisseur de la peau
        "Insulin",  # Niveau d'insuline
        "BMI",  # Indice de masse corporelle
        "DiabetesPedigreeFunction",  # Facteur héréditaire
        "Age",  # Âge
        "Outcome"  # Résultat (0 = sain, 1 = diabétique)
    ]
    
    # Chargement des données depuis le fichier CSV en ligne
    data = pd.read_csv(url, names=columns)

    # Séparation des variables explicatives (X) et de la variable cible (y)
    X = data.drop("Outcome", axis=1)  # Toutes les colonnes sauf Outcome
    y = data["Outcome"]  # Colonne à prédire

    # =========================
    # Normalisation des données
    # =========================
    
    # Standardisation (centrage-réduction) pour améliorer les performances du modèle
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # =========================
    # Division des données
    # =========================
    
    # 80% pour l'entraînement, 20% pour le test
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42
    )

    # =========================
    # Création du modèle IA
    # =========================
    
    # Réseau de neurones simple (Deep Learning)
    model = Sequential([
        Dense(16, activation='relu', input_dim=8),  # Couche d'entrée + 16 neurones
        Dense(8, activation='relu'),  # Couche cachée avec 8 neurones
        Dense(1, activation='sigmoid')  # Couche de sortie (probabilité entre 0 et 1)
    ])

    # Compilation du modèle
    model.compile(
        optimizer='adam',  # Algorithme d'optimisation
        loss='binary_crossentropy',  # Fonction de perte pour classification binaire
        metrics=['accuracy']  # Métrique d'évaluation
    )

    # =========================
    # Entraînement du modèle
    # =========================
    
    # Entraînement sur 50 itérations (epochs)
    model.fit(X_train, y_train, epochs=50, verbose=0)

    # Retourne le modèle entraîné + le scaler pour réutilisation
    return model, scaler