# CTRLX Social Growth & Automation Engine

Moteur d'automatisation autonome 24/7 pour le développement et la visibilité de la communauté CTRLX sur X / Twitter, Reddit et Facebook.

### Fonctionnalités Clés
* **Connexion automatique et autonome :** Au lancement, le script vérifie les sessions. Si une session manque et qu'un écran est disponible, le navigateur s'ouvre automatiquement pour vous connecter une seule fois et mémoriser l'état.
* **Fonctionnement continu 24/7 :** Tourne en continu en tâche de fond avec gestion des cycles, pauses aléatoires et quotas journaliers stricts.
* **Découverte de groupes Facebook français :** Recherche et répertorie automatiquement les groupes d'entraide informatique et de développeurs français pour y participer naturellement.
* **Suivi conversationnel intelligent :** Si un utilisateur répond à l'une de vos réponses, le script analyse le message. S'il s'agit d'une simple fermeture (ex: "merci", "cool", "ok"), il ne répond pas. S'il pose une question ou demande des détails, il répond de manière humble et concise.
* **Politique stricte zéro doublon :** Double vérification par base SQLite (`seen_items` et `social_actions`) pour ne jamais interagir deux fois avec le même message ou post.
* **Orthographe française soignée avec accents :** Respect rigoureux de tous les accents français (é, è, ê, à, â, î, ï, ô, ù, ç) sans aucun emoji.
* **Compatibilité Raspberry Pi :** Optimisé pour fonctionner sur Raspberry Pi OS avec Chromium headless et drapeaux de mémoire partagée adaptés.

### Structure du Dossier
* `config.py` : Paramètres, quotas quotidiens et subreddits surveillés.
* `database.py` : Base SQLite `social_data.sqlite` traçant l'historique, les éléments vus et les groupes Facebook.
* `content_engine.py` : Moteur de génération de texte indétectable avec accents et filtrage conversationnel.
* `browser_manager.py` : Gestionnaire Playwright headless/headed avec persistance des cookies dans `sessions/`.
* `reddit_bot.py` : Bot Reddit avec gestion des flairs, détection des réponses et boîte de réception.
* `twitter_bot.py` : Bot Twitter / X avec publication navigateur, veille et gestion des mentions.
* `facebook_bot.py` : Bot Facebook avec découverte de groupes tech français et publication rotative.
* `orchestrator.py` : Point d'entrée principal (mode continu 24/7 par défaut).

### Utilisation Rapide

1. **Lancement standard 24/7 (recommandé) :**
```bash
python social/orchestrator.py
```
Le script vérifie vos accès, ouvre la fenêtre de connexion si nécessaire, puis tourne en continu 24/7.

2. **Afficher les statistiques et l'historique :**
```bash
python social/orchestrator.py --stats
```

3. **Lancer un cycle unique :**
```bash
python social/orchestrator.py --once
```

4. **Connexion interactive manuelle :**
```bash
python social/orchestrator.py --auth facebook
python social/orchestrator.py --auth twitter
python social/orchestrator.py --auth all
```

5. **Découvrir de nouveaux groupes Facebook français :**
```bash
python social/orchestrator.py --discover-groups
```

### Déploiement sur Raspberry Pi

1. Sur votre PC Windows, effectuez la première connexion pour générer les fichiers de session :
   * `social/sessions/twitter_state.json`
   * `social/sessions/facebook_state.json`
2. Copiez le dossier du projet ou le dossier `social/` sur votre Raspberry Pi (ex: `axellqt@raspberrypi:~/CTRLX/social/`).
3. Sur le Raspberry Pi, installez Chromium si ce n'est pas déjà fait :
```bash
sudo apt update && sudo apt install -y chromium-browser
```
4. Lancez le script en arrière-plan :
```bash
nohup python3 social/orchestrator.py > social.log 2>&1 &
```
Le script tourne alors en totale autonomie sans nécessiter d'écran.
