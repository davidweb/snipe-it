# Instructions de Configuration et de Lancement

Ce guide vous explique comment configurer votre instance Snipe-IT et comment lancer le système de surveillance RFID.

## 1. Configuration de Snipe-IT

### a. Créer une Clé API

1.  Connectez-vous à votre instance Snipe-IT avec un compte administrateur.
2.  Allez dans votre profil utilisateur (en haut à droite) et cliquez sur **"Manage API Keys"**.
3.  Cliquez sur **"Create New Token"**.
4.  Donnez-lui un nom (ex: `RFID_Monitor`) et sauvegardez.
5.  **Copiez la clé API immédiatement**. Vous ne pourrez plus la voir après avoir quitté cette page. C'est cette clé que vous mettrez dans `config.py`.

### b. Configurer les "Status Labels"

Le script se base sur le champ `status_meta` des statuts pour décider si une sortie est autorisée. Assurez-vous que votre Snipe-IT est configuré correctement.

1.  Allez dans **Settings** (icône roue crantée) > **Status Labels**.
2.  Vérifiez que vous avez des statuts qui correspondent à la logique suivante :
    *   **Statut pour matériel déployé/sorti (Autorisé)** :
        *   **Name** : `Deployed`, `Sorti`, `Attribué`, etc.
        *   **Status Type (meta)** : Doit être **`Deployed`**. C'est la valeur par défaut pour les matériels assignés.
    *   **Statuts pour matériel en stock (Non-autorisé)** :
        *   **Name** : `Ready to Deploy`, `En stock`, `Archivé`, `En réparation`, etc.
        *   **Status Type (meta)** : Doit être `Deployable`, `Pending`, ou `Archived`.

> Dans le fichier `config.py`, la variable `SAFE_STATUSES` est configurée par défaut à `['deployed']`. Vous pouvez l'adapter si vous avez des `status_meta` personnalisés que vous considérez comme sûrs.

### c. Créer des Matériels de Test

Pour que le script `mock_reader.py` fonctionne, vous devez créer au moins deux actifs dans Snipe-IT :

1.  **Actif Non-Autorisé (doit déclencher l'alarme)** :
    *   Créez un nouvel actif.
    *   Dans le champ **"Asset Tag"**, mettez exactement `414C41524D5F5441475F3031`.
    *   Assignez-lui un statut dont le `status_meta` est `Deployable` (ex: "Ready to Deploy").

2.  **Actif Autorisé (ne doit pas déclencher l'alarme)** :
    *   Créez un autre actif.
    *   Dans le champ **"Asset Tag"**, mettez exactement `534146455F5441475F3032`.
    *   Assignez-lui un statut `Deployed`. Pour cela, vous devez **assigner (checkout) l'actif à un utilisateur**.

## 2. Lancement des Scripts

### a. Pré-requis

*   Python 3 installé.
*   Un fichier son pour l'alarme. Créez un simple fichier `.mp3` et nommez-le `alarm.mp3` dans le même dossier que les scripts, ou changez le chemin dans `config.py`.

### b. Installation

1.  Ouvrez un terminal ou une invite de commande.
2.  Naviguez jusqu'au dossier `rfid-middleware` où se trouvent les fichiers :
    ```bash
    cd rfid-middleware
    ```
3.  Installez les dépendances Python avec la commande :
    ```bash
    pip install -r requirements.txt
    ```

### c. Configuration

1.  Ouvrez le fichier `config.py`.
2.  Remplacez `https://your-snipe-it-instance.com/api/v1` par l'URL de l'API de votre instance.
3.  Remplacez `YOUR_API_KEY` par la clé API que vous avez générée à l'étape 1a.
4.  Vérifiez que `RFID_HOST` et `RFID_PORT` correspondent à votre configuration réseau (les valeurs par défaut `localhost` et `6000` sont parfaites pour tester localement).

### d. Exécution

Vous devez ouvrir **deux terminaux distincts**.

*   **Terminal 1 : Lancer le Moniteur**
    ```bash
    python rfid_monitor.py
    ```
    Vous devriez voir le message : `Serveur de surveillance RFID démarré. En écoute sur localhost:6000`.

*   **Terminal 2 : Lancer le Simulateur de Lecteur**
    ```bash
    python mock_reader.py
    ```
    Ce script va commencer à envoyer des tags de test au moniteur.

Vous verrez alors les messages d'autorisation (en vert) et les alertes de sécurité (en rouge) apparaître dans le **Terminal 1**. Les événements seront également enregistrés dans `security_events.log`.
