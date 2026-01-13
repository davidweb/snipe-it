# rfid_monitor.py

# IMPORTANT: Eventlet monkey patching must happen first
import eventlet
eventlet.monkey_patch()

import socket
import threading
import time
import requests
import logging
import re
from datetime import datetime
from playsound import playsound
from colorama import init, Fore, Style
from flask import Flask, render_template
from flask_socketio import SocketIO

# Import configuration
try:
    from config import API_URL, API_KEY, RFID_HOST, RFID_PORT, ALARM_SOUND, SAFE_STATUSES, LOG_FILE
except ImportError:
    print("Erreur: Le fichier config.py n'a pas été trouvé ou est mal configuré.")
    exit()

# Initialize Flask & SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='eventlet')

# Initialize Colorama
init(autoreset=True)

# Cache simple pour éviter les appels API répétitifs
tag_cache = {}
CACHE_TTL = 10  # secondes

# Configuration du logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Flask & SocketIO Routes / Handlers ---
@app.route('/')
def index():
    """Sert la page principale de l'interface web."""
    return render_template('index.html')

@socketio.on('get_asset_details')
def handle_get_asset_details(data):
    """Gère la demande de détails d'un actif depuis le client web."""
    tag_id = data.get('tag_id')
    if not tag_id:
        return

    print(f"Demande de détails reçue pour le tag: {tag_id}")
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
    }

    try:
        url = f"{API_URL}/hardware/bytag/{tag_id}"
        response = requests.get(url, headers=headers, timeout=5)

        if response.status_code == 200:
            asset_data = response.json()
            details = {
                "Nom": asset_data.get('name'),
                "Asset Tag": asset_data.get('asset_tag'),
                "Modèle": asset_data.get('model', {}).get('name'),
                "Numéro de Série": asset_data.get('serial'),
                "Statut": asset_data.get('status_label', {}).get('name'),
                "Catégorie": asset_data.get('category', {}).get('name'),
                "Assigné à": asset_data.get('assigned_to', {}).get('name'),
                "Date d'achat": asset_data.get('purchase_date', {}).get('formatted'),
            }
            socketio.emit('asset_details_response', details)
        else:
            socketio.emit('asset_details_response', {'error': f'Actif non trouvé ou erreur API (Code: {response.status_code})'})
    except requests.exceptions.RequestException as e:
        socketio.emit('asset_details_response', {'error': f'Erreur de connexion à l\'API Snipe-IT: {e}'})

# --- Core Application Logic ---
def trigger_alarm(tag_id, asset_info):
    """Déclenche une alarme sonore, visuelle, log et web."""
    asset_name = asset_info.get('name', 'N/A')
    status_name = asset_info.get('status_label', {}).get('name', 'N/A')

    message = f"ALERTE SECURITE: Sortie non autorisée du matériel '{asset_name}' (Tag: {tag_id}, Statut: {status_name})."
    print(Fore.RED + Style.BRIGHT + message)
    logging.warning(message)

    socketio.emit('new_event', {
        'message': message, 'type': 'alert',
        'timestamp': datetime.now().isoformat(), 'tag_id': tag_id
    })

    try:
        playsound(ALARM_SOUND)
    except Exception as e:
        print(Fore.YELLOW + f"Attention: Impossible de jouer le son de l'alarme ({e})")

def log_authorized_exit(tag_id, asset_info):
    """Log une sortie autorisée et l'envoie sur le web."""
    asset_name = asset_info.get('name', 'N/A')
    assigned_to = asset_info.get('assigned_to')
    user_name = "Personne"
    if assigned_to and 'name' in assigned_to:
        user_name = assigned_to['name']

    message = f"Sortie autorisée: '{asset_name}' (Tag: {tag_id}) assigné à {user_name}."
    print(Fore.GREEN + message)
    logging.info(message)

    socketio.emit('new_event', {
        'message': message, 'type': 'success',
        'timestamp': datetime.now().isoformat(), 'tag_id': tag_id
    })

def log_unknown_tag(tag_id):
    """Log un tag inconnu et l'envoie sur le web."""
    message = f"ALERTE: Tag RFID '{tag_id}' détecté mais non trouvé dans Snipe-IT."
    print(Fore.YELLOW + message)
    logging.warning(message)

    socketio.emit('new_event', {
        'message': message, 'type': 'warning',
        'timestamp': datetime.now().isoformat(), 'tag_id': tag_id
    })

def check_snipeit_status(tag_id):
    """Interroge l'API Snipe-IT pour vérifier le statut d'un matériel."""
    if not API_KEY or API_KEY == "YOUR_API_KEY":
        print(Fore.RED + "Erreur: La clé API n'est pas configurée dans config.py.")
        return
    # ... (le reste de la fonction est inchangé)
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    try:
        url = f"{API_URL}/hardware/bytag/{tag_id}"
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            asset_data = response.json()
            status_meta = asset_data.get('status_label', {}).get('status_meta', '').lower()
            if status_meta in SAFE_STATUSES:
                log_authorized_exit(tag_id, asset_data)
            else:
                trigger_alarm(tag_id, asset_data)
        elif response.status_code == 404:
            log_unknown_tag(tag_id)
        else:
            error_message = f"Erreur API Snipe-IT pour le tag {tag_id}: {response.status_code} - {response.text}"
            print(Fore.RED + error_message)
            logging.error(error_message)
    except requests.exceptions.RequestException as e:
        error_message = f"Erreur de connexion à l'API Snipe-IT: {e}"
        print(Fore.RED + error_message)
        logging.error(error_message)

def parse_and_check_tag(hex_string):
    """Extrait les tags EPC Gen2 de 24 caractères."""
    possible_tags = re.findall(r'[0-9A-F]{24}', hex_string.upper())
    for tag_id in possible_tags:
        current_time = time.time()
        if tag_id in tag_cache and (current_time - tag_cache[tag_id]) < CACHE_TTL:
            continue
        tag_cache[tag_id] = current_time
        print(f"Tag détecté: {tag_id}. Vérification du statut...")
        threading.Thread(target=check_snipeit_status, args=(tag_id,)).start()

def handle_client(client_socket, address):
    """Gère la connexion d'un lecteur RFID."""
    print(f"Connexion acceptée de {address[0]}:{address[1]}")
    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            hex_data = data.hex().upper()
            print(f"Données brutes reçues de {address[0]}: {hex_data}")
            parse_and_check_tag(hex_data)
    except ConnectionResetError:
        print(f"Connexion perdue avec {address[0]}:{address[1]}")
    finally:
        client_socket.close()
        print(f"Connexion fermée avec {address[0]}:{address[1]}")

def start_tcp_server():
    """Fonction pour le serveur TCP."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind((RFID_HOST, RFID_PORT))
        server.listen(5)
        print(Fore.CYAN + f"Serveur de surveillance RFID démarré. En écoute sur {RFID_HOST}:{RFID_PORT}")
        logging.info("Le service de surveillance RFID a démarré.")
        while True:
            client_sock, address = server.accept()
            client_handler = threading.Thread(target=handle_client, args=(client_sock, address))
            client_handler.start()
    except OSError as e:
        print(Fore.RED + f"Erreur de démarrage du serveur TCP: {e}. Le port est-il déjà utilisé?")
        logging.critical(f"Erreur de démarrage du serveur TCP: {e}")
    finally:
        server.close()
        logging.info("Le service de surveillance RFID s'est arrêté.")

if __name__ == "__main__":
    print(Fore.YELLOW + "Démarrage des services...")
    tcp_thread = threading.Thread(target=start_tcp_server)
    tcp_thread.daemon = True
    tcp_thread.start()
    print(Fore.GREEN + "Interface web disponible sur http://127.0.0.1:5000")
    socketio.run(app, host='127.0.0.1', port=5000)
