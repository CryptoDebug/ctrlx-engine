# CTRLX Social Growth & Automation Engine

Module d'automatisation pour le developpement et la visibilite de la communaute CTRLX sur Reddit et X / Twitter.

### Fonctionnalites Cles
* **Veille ciblée des discussions de developpeurs :** Surveillance des subreddits tech (r/developpeurs, r/france_tech, r/SideProject, r/webdev, r/Python) et des flux X.
* **Reponses contextuelles indetectables :** Generation IA via Gemini 2.5 Flash Lite configuree avec des regles strictes anti-bot (zero emoji, ton developpeur authentique et humble, reponses courtes de 1 a 3 phrases).
* **Publications de discussions authentiques :** Generation de sujets de discussion sans liens externes dans le corps de texte (pour eviter les filtres AutoModerator Reddit).
* **Garde-fous anti-spam et limitations :** Quotas stricts par jour, cooldowns avec jitter aleatoire entre chaque action, base SQLite d'historique pour ne jamais repondre deux fois au meme post.
* **Mode DRY_RUN par defaut :** Permet de tester et visualiser les contenus generes sans poster reellement tant que les cles API ne sont pas actives.

### Structure du Dossier
* `config.py` : Parametres, seuils d'actions quotidiennes et subreddits surveilles.
* `database.py` : Base SQLite `social_data.sqlite` tracant les posts vus et les actions menees.
* `content_engine.py` : Moteur de generation de contenu indetectable avec filtre strict anti-emojis.
* `reddit_bot.py` : Connecteur REST OAuth vers Reddit (scans, reponses, publications).
* `twitter_bot.py` : Connecteur OAuth 1.0a / Bearer vers X / Twitter (recherche, reponses, tweets).
* `orchestrator.py` : Chef d'orchestre CLI et service continu.

### Utilisation CLI

1. **Voir les statistiques et actions du jour :**
```bash
python orchestrator.py --stats
```

2. **Lancer un cycle unique de scan et reponse :**
```bash
python orchestrator.py --once
```

3. **Generer et publier un sujet de discussion sur Reddit :**
```bash
python orchestrator.py --post-reddit --subreddit developpeurs
```

4. **Generer et publier un tweet authentique sur X :**
```bash
python orchestrator.py --post-twitter
```

5. **Lancer en arriere-plan continu (daemon) :**
```bash
python orchestrator.py --daemon
```
