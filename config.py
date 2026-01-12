# config.py

# Snipe-IT API Configuration
API_URL = "https://your-snipe-it-instance.com/api/v1"  # Remplacez par l'URL de votre instance Snipe-IT
API_KEY = "YOUR_API_KEY"  # Remplacez par votre clé API Snipe-IT

# RFID Reader Configuration
RFID_HOST = "localhost"  # Adresse IP sur laquelle le moniteur écoute
RFID_PORT = 6000  # Port TCP pour le lecteur RFID

# Alarm Configuration
ALARM_SOUND = "alarm.mp3"  # Chemin vers le fichier son de l'alarme
SAFE_STATUSES = ["deployed"]  # Statuts considérés comme autorisés pour la sortie

# Logging Configuration
LOG_FILE = "security_events.log"
