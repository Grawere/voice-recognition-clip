# Jarvis Clip – Voice‑controlled NVIDIA or AMD Instant Replay

Jarvis Clip est un petit outil Windows qui permet de déclencher le **clip NVIDIA Instant Replay** avec une **commande vocale hors‑ligne** ("Jarvis, clip ça !").  
La capture vidéo est entièrement gérée par **NVIDIA ShadowPlay / GeForce Experience**, ce qui minimise l'impact sur les performances.

> ⚠ **Important** :  
> **Le premier lancement peut être sensiblement plus long que les suivants**, le temps que le modèle de reconnaissance vocale soit chargé en mémoire et que le micro soit initialisé. C'est attendu.

---

## Fonctionnalités

- Reconnaissance vocale **offline** en français (Vosk).
- Déclenchement du raccourci NVIDIA Instant Replay (par défaut `Alt+F10`).
- Petite interface Tkinter pour :
  - afficher le raccourci actuel ;
  - changer la touche de clip via un bouton.
- Icône dans la barre des tâches (systray) avec menu :
  - **Ouvrir** la fenêtre de configuration ;
  - **Quitter** proprement l'application.
- Fichier de configuration `config.json` (sauvegarde du raccourci choisi).

---

## Prérequis

### NVIDIA

- **NVIDIA GeForce Experience** installé avec l'overlay en jeu activé.
- **Instant Replay** (ou "Rejouer instantanément") activé avec une durée définie (ex. 30–60 s).
- Un **raccourci clavier** configuré pour "Enregistrer les X dernières secondes"  
  (par défaut souvent `Alt+F10` dans GeForce Experience).

Vérifie que ce raccourci fonctionne **manuellement** (en appuyant sur la touche) avant d'utiliser Jarvis.

### Environnement Python (si tu lances depuis les sources)

- Windows 10 ou 11.
- Python 3.12+.
- Microphone fonctionnel.

---

## Installation depuis les sources

```bash
git clone https://github.com/<ton-user>/<ton-repo>.git
cd <ton-repo>
```

### 1. Créer et activer un environnement virtuel

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1   # PowerShell
# ou
venv\Scripts\activate.bat     # CMD classique
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Installer le modèle Vosk FR

1. Télécharger le modèle français "small" de Vosk (par ex. `vosk-model-small-fr-0.22`).
2. Décompresser le dossier dans :

```text
models/vosk-model-small-fr-0.22/
```

3. Vérifier que dans `jarvis.py` :

```python
MODEL_PATH = r"models/vosk-model-small-fr-0.22"
```

pointe bien vers ce dossier.

### 4. Lancer Jarvis

```bash
python jarvis.py
```

Au premier lancement, le chargement du modèle peut prendre quelques secondes.

---

## Utilisation

1. **Lancement**

   - Au lancement, une fenêtre "Jarvis – Clip" s'ouvre.
   - Une icône "J" apparaît dans la barre des tâches.

2. **Configuration du raccourci**

   - Le texte "Raccourci clip" affiche la touche actuellement utilisée (par exemple `alt+f10`).
   - Clique sur **"Changer la touche"**, puis appuie sur la combinaison voulue.
   - La touche est enregistrée dans `config.json` et sera réutilisée aux prochains lancements.
   - Assure‑toi que cette combinaison est la même que celle configurée dans GeForce Experience.

3. **Fermeture / réduction**

   - Fermer la fenêtre via la croix la masque (la fenêtre est retirée, Jarvis continue de tourner).
   - L'icône de la barre des tâches reste active :
     - **Ouvrir** : rouvre la fenêtre.
     - **Quitter** : arrête Jarvis proprement.

4. **Commande vocale**

   - Laisse Jarvis tourner en arrière‑plan.
   - Dis clairement : **"Jarvis, clip ça !"** (avec un micro fonctionnel).
   - Si la phrase est reconnue, Jarvis envoie le raccourci configuré à Windows.
   - NVIDIA Instant Replay enregistre alors les dernières X secondes de jeu / écran.

---

## Générer l'exécutable Windows

Depuis l'environnement virtuel :

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --collect-all vosk jarvis.py
```

L'exécutable se trouvera dans :

```text
dist/jarvis.exe
```

Structure recommandée pour l'utilisation de l'exe :

```text
JarvisClip/
├─ jarvis.exe
├─ config.json                     # créé automatiquement au premier lancement
└─ models/
   └─ vosk-model-small-fr-0.22/    # modèle Vosk FR
```

---

## Lancement automatique au démarrage (optionnel)

Pour lancer Jarvis à chaque ouverture de session :

1. Appuie sur `Win + R`, tape :

   ```text
   shell:startup
   ```

   puis Entrée.

2. Dans le dossier "Démarrage" qui s'ouvre, crée un **raccourci** vers `jarvis.exe`.

Jarvis se lancera alors automatiquement en tâche de fond à chaque connexion Windows.

---

## Notes et limitations

- Jarvis **ne capture pas la vidéo lui‑même** : il ne fait qu'envoyer le raccourci clavier à NVIDIA.
- La reconnaissance vocale est **100 % locale** (hors ligne).
- La commande "Jarvis, clip ça !" peut être ajustée en éditant les listes `WAKE_WORDS` et `CLIP_WORDS` dans `jarvis.py` pour tenir compte de ta prononciation.
- Le premier lancement est plus long à cause du chargement du modèle de reconnaissance vocale ; les suivants sont généralement plus rapides.
