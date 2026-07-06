# BusTracking_UAC 

Système de suivi et de géolocalisation en temps réel des bus de l'Université de l'Assomption au Congo (UAC). Ce projet combine une solution embarquée (ESP32, GPS, GSM/GPRS) et une plateforme web centralisée (Flask, Leaflet.js).

---

## 1. Architecture et Arborescence du Projet

Voici l'organisation des fichiers et dossiers à la racine du projet :

```text
BusTracking_UAC/
│
├── hardware/               # Code source destiné à la carte embarquée
│   └── esp32_firmware/
│       └── esp32_firmware.ino  # Script principal Arduino / C++
│
├── server/                 # Code source de l'application Backend & Frontend
│   ├── app.py              # Point d'entrée de l'application Flask (Serveur)
│   ├── database.db         # Base de données SQLite (générée au premier lancement)
│   │
│   ├── static/             # Fichiers statiques du Frontend
│   │   ├── css/
│   │   │   └── style.css   # Styles de l'interface web
│   │   └── js/
│   │       └── main.js     # Logique JavaScript (appels AJAX, Leaflet.js)
│   │
│   └── templates/          # Modèles HTML (Flask)
│       └── index.html      # Page d'accueil et cartographie temps réel
│
├── requirements.txt        # Liste des dépendances Python à installer
└── README.md               # Documentation du projet (ce fichier)git add

2. Rôle opérationnel des composants
esp32_firmware.ino : Récupère les coordonnées géographiques via le module GPS, package les données et les transmet au serveur web via des requêtes HTTP (via le réseau GPRS du module GSM).

app.py : Serveur Flask chargé de réceptionner les requêtes POST de l'ESP32, de stocker les coordonnées en base de données, et de servir l'interface web aux utilisateurs via des API REST (endpoints JSON).

database.db : Base de données relationnelle légère (SQLite) qui stocke l'historique des positions, l'identifiant des bus et les horodatages (timestamps).

index.html & main.js : Interface utilisateur. Le script JS interroge le serveur en arrière-plan (requêtes asynchrones) et met à jour dynamiquement la position des bus sur la carte interactive Leaflet.js sans recharger la page.

3. Guide de déploiement rapide (Local)
Pour tester ou auditer l'environnement de test en local, suivez les étapes suivantes :

Prérequis
Python 3.8 ou supérieur installé.

Un navigateur web moderne.

Installation et exécution
Cloner le répertoire :

Bash
git clone [https://github.com/isharakyamakyal/BusTracking_UAC.git](https://github.com/isharakyamakyal/BusTracking_UAC.git)
cd BusTracking_UAC/server
Installer les dépendances requises :

Bash
pip install -r ../requirements.txt
Lancer le serveur Flask :

Bash
python app.py
Accéder à l'application :
Ouvrez votre navigateur et accédez à l'adresse suivante : http://127.0.0.1:5000
