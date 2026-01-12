# mock_reader.py

import socket
import time
import random
import sys

try:
    from config import RFID_HOST, RFID_PORT
except ImportError:
    print("Erreur: Le fichier config.py n'a pas été trouvé. Assurez-vous qu'il existe.")
    sys.exit(1)

# --- Tags de test ---
# Important: Pour que ce test fonctionne, vous devez créer des actifs dans Snipe-IT
# avec les "Asset Tags" correspondants.

# 1. Un actif avec le statut "Ready to Deploy" (ou un autre statut non autorisé)
TAG_DEPLOYABLE = "414C41524D5F5441475F3031"  # "ALARM_TAG_01" en hexadécimal (24 caractères)
# 2. Un actif avec le statut "Deployed"
TAG_DEPLOYED = "534146455F5441475F3032"    # "SAFE_TAG_02" en hexadécimal (24 caractères)
# 3. Un tag qui n'existe pas dans la base de données
TAG_UNKNOWN = "554E4B4E5F5441475F3033"    # "UNKN_TAG_03" en hexadécimal (24 caractères)

# On peut ajouter des données "parasites" pour simuler une trame réelle
PREFIX = "A1B2C3D4"
SUFFIX = "E5F6"

TEST_TAGS = [
    f"{PREFIX}{TAG_DEPLOYABLE}{SUFFIX}",
    f"{PREFIX}{TAG_DEPLOYED}{SUFFIX}",
    f"{PREFIX}{TAG_UNKNOWN}{SUFFIX}"
]

def main():
    """Script principal du lecteur mock."""
    print("Démarrage du simulateur de lecteur RFID...")

    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                print(f"Tentative de connexion à {RFID_HOST}:{RFID_PORT}...")
                s.connect((RFID_HOST, RFID_PORT))
                print("Connexion réussie au serveur de surveillance.")

                while True:
                    # Choisir un tag au hasard
                    random_hex_tag_with_noise = random.choice(TEST_TAGS)

                    # Convertir la chaîne hexadécimale en bytes
                    data_to_send = bytes.fromhex(random_hex_tag_with_noise)

                    print(f"\nEnvoi du tag: {random_hex_tag_with_noise}")
                    s.sendall(data_to_send)

                    # Attendre avant d'envoyer le prochain tag
                    time.sleep(5)

        except ConnectionRefusedError:
            print(f"Erreur de connexion: Le serveur sur {RFID_HOST}:{RFID_PORT} n'est pas actif.")
            print("Veuillez démarrer rfid_monitor.py. Nouvelle tentative dans 10 secondes...")
            time.sleep(10)
        except (ConnectionResetError, BrokenPipeError):
            print("La connexion avec le serveur a été perdue. Tentative de reconnexion...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nArrêt du simulateur.")
            break
        except Exception as e:
            print(f"Une erreur inattendue est survenue: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
