# rfid_monitor.py

import socket
import threading
import time
import requests
import logging
import re
from datetime import datetime
from playsound import playsound
from colorama import init, Fore, Style

# Import configuration
try:
    from config import API_URL, API_KEY, RFID_HOST, RFID_PORT, ALARM_SOUND, SAFE_STATUSES, LOG_FILE
except ImportError:
    print("Erreur: Le fichier config.py n'a pas été trouvé ou est mal configuré.")
    exit()

# Initialize Colorama
init(autoreset=True)

# Cache simple pour éviter les appels API répétitifs
# Format: { 'tag_id': last_seen_timestamp }
tag_cache = {}
CACHE_TTL = 10  # secondes

# Configuration du logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def trigger_alarm(tag_id, asset_info):
    """Déclenche une alarme sonore, visuelle et dans les logs."""
    asset_name = asset_info.get('name', 'N/A')
    status_name = asset_info.get('status_label', {}).get('name', 'N/A')

    message = f"ALERTE SECURITE: Sortie non autorisée du matériel '{asset_name}' (Tag: {tag_id}, Statut: {status_name})."
    print(Fore.RED + Style.BRIGHT + message)
    logging.warning(message)

    try:
        playsound(ALARM_SOUND)
    except Exception as e:
        print(Fore.YELLOW + f"Attention: Impossible de jouer le son de l'alarme ({e})")

def log_authorized_exit(tag_id, asset_info):
    """Log une sortie autorisée."""
    asset_name = asset_info.get('name', 'N/A')
    assigned_to = asset_info.get('assigned_to')
    user_name = "Personne"
    if assigned_to and 'name' in assigned_to:
        user_name = assigned_to['name']

    message = f"Sortie autorisée: '{asset_name}' (Tag: {tag_id}) assigné à {user_name}."
    print(Fore.GREEN + message)
    logging.info(message)

def log_unknown_tag(tag_id):
    """Log un tag inconnu dans Snipe-IT."""
    message = f"ALERTE: Tag RFID '{tag_id}' détecté mais non trouvé dans Snipe-IT."
    print(Fore.YELLOW + message)
    logging.warning(message)

def check_snipeit_status(tag_id):
    """Interroge l'API Snipe-IT pour vérifier le statut d'un matériel."""
    if not API_KEY or API_KEY == "YOUR_API_KEY":
        print(Fore.RED + "Erreur: La clé API n'est pas configurée dans config.py.")
        return

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
    }

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
    """Extrait les tags EPC Gen2 de 24 caractères à l'aide d'expressions régulières."""
    # Recherche toutes les chaînes hexadécimales non-chevauchantes de 24 caractères
    possible_tags = re.findall(r'[0-9A-F]{24}', hex_string.upper())

    if not possible_tags:
        return

    for tag_id in possible_tags:
        current_time = time.time()
        if tag_id in tag_cache and (current_time - tag_cache[tag_id]) < CACHE_TTL:
            # Si le tag est dans le cache et n'a pas expiré, on l'ignore.
            continue

        # Mettre à jour le cache et vérifier le statut
        tag_cache[tag_id] = current_time
        print(f"Tag détecté: {tag_id}. Vérification du statut...")

        # Lancer la vérification dans un thread séparé pour ne pas bloquer
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

def main():
    """Fonction principale du serveur."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind((RFID_HOST, RFID_PORT))
        server.listen(5)
        print(Fore.CYAN + f"Serveur de surveillance RFID démarré. En écoute sur {RFID_HOST}:{RFID_PORT}")
        logging.info("Le service de surveillance RFID a démarré.")

        while True:
            client_sock, address = server.accept()
            # Démarrer un nouveau thread pour gérer ce client
            client_handler = threading.Thread(target=handle_client, args=(client_sock, address))
            client_handler.start()
    except OSError as e:
        print(Fore.RED + f"Erreur de démarrage du serveur: {e}. Le port est-il déjà utilisé?")
        logging.critical(f"Erreur de démarrage du serveur: {e}")
    finally:
        server.close()
        logging.info("Le service de surveillance RFID s'est arrêté.")

if __name__ == "__main__":
    main()
