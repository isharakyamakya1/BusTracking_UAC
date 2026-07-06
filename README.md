# BusTracking_UAC 🚌📍

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