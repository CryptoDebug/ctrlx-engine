import re
import random
import urllib.request
import json
from config import GEMINI_API_KEY, DISCORD_INVITE_URL

EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u2b50\u200d\ufe0f]",
    flags=re.UNICODE
)

def strip_emojis(text: str) -> str:
    cleaned = EMOJI_PATTERN.sub("", text)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = cleaned.replace("\u2014", "-").replace("-" * 3, "-")
    return cleaned.strip()

def query_gemini(system_instruction: str, user_prompt: str) -> str:
    if not GEMINI_API_KEY:
        return ""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": user_prompt}
                ]
            }
        ],
        "systemInstruction": {
            "parts": [
                {"text": system_instruction}
            ]
        },
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 300
        }
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
    except Exception:
        pass
    return ""

def generate_reddit_reply(post_title: str, post_body: str, subreddit: str) -> str:
    system_inst = (
        "Tu es un developpeur francophone independant qui repond de maniere naturelle et spontanee sur Reddit. "
        "REGLES STRICTES ET NON NEGOCIABLES : "
        "1. AUCUN EMOJI. Zero emoji. "
        "2. Pas de tiret long ni de triples tirets. "
        "3. Ne parle JAMAIS comme une IA : pas de formules du type 'C'est une excellente question', 'Voici quelques conseils', 'En tant que'. "
        "4. Sois concis, pragmatique et humble (2 a 3 phrases maximum). "
        "5. Partage un retour d'experience dev sincere. Si le sujet concerne un projet ou un besoin de retours, mentionne brievement "
        "que tu es dans une communaute de builders basee sur l'echange mutuel de feedback (sans mettre de lien direct, dis juste de passer en MP si besoin)."
    )

    prompt = (
        f"Subreddit: r/{subreddit}\n"
        f"Titre du post: {post_title}\n"
        f"Contenu du post: {post_body[:500]}\n\n"
        "Ecris une reponse humaine, courte et pertinente."
    )

    generated = query_gemini(system_inst, prompt)
    if generated:
        return strip_emojis(generated)

    fallbacks = [
        "En vrai c'est un probleme classique quand on commence un projet. Tu as teste de decouper ton architecture en petits modules independants ? Ca m'avait pas mal debloque sur un script similaire.",
        "Projet interessant. Le plus dur reste d'avoir les premiers testeurs pour valider l'UX. Perso je passe par un groupe d'entraide ou on teste les apps des uns et des autres, ca evite de lancer dans le vide. Dis-moi si tu veux des retours dessus en MP.",
        "Bien joue pour le lancement. Tu comptes open-source le code ou garder ca ferme ? Si tu cherches du retour technique sur l'architecture n'hesite pas.",
        "Perso j'etais tombe sur le meme ecueil avec ce genre de stack. Le truc qui m'a sauve c'etait de reduire le scope au minimum avant de rajouter d'autres features."
    ]
    return random.choice(fallbacks)

def generate_reddit_post(topic: str = "feedback_problem") -> tuple[str, str]:
    system_inst = (
        "Tu es un dev qui partage une reflexion sincere sur Reddit dans une communaute de developpeurs. "
        "REGLES STRICTES : "
        "1. ZERO EMOJI. "
        "2. Aucun lien direct (les liens discord sont interdits dans les posts). "
        "3. Pas de tiret long ni de triples tirets. "
        "4. Style francais direct, honnete, oriente craft et retours d'experience. "
        "5. Termine en invitant les membres interesses par des tests croises a repondre en commentaire ou en MP."
    )

    prompt = (
        "Genere un titre percutant et un texte de 3 ou 4 courts paragraphes sur le probleme "
        "du manque de testeurs et de feedback quand on code des projets solo, et comment une logique d'entraide "
        "permet de progresser ensemble. Separe le titre et le texte par la ligne '###SEPARATOR###'."
    )

    generated = query_gemini(system_inst, prompt)
    if generated and "###SEPARATOR###" in generated:
        parts = generated.split("###SEPARATOR###", 1)
        title = strip_emojis(parts[0].replace("Titre :", "").replace("Titre:", "").strip())
        body = strip_emojis(parts[1].strip())
        return title, body

    default_title = "Le plus gros frein quand on dev solo : coder dans le vide sans testeurs"
    default_body = (
        "Salut tout le monde,\n\n"
        "Je discutais avec pas mal de devs ces derniers temps et le constat est toujours le meme : "
        "on passe des semaines a monter un side-project ou un outil cool, et des qu'on le partage, "
        "presque personne ne prend le temps de regarder le code ou de tester l'app.\n\n"
        "Sans retours concrets sur l'UX ou l'architecture, la motivation retombe vite.\n\n"
        "On essaie de tester un fonctionnement simple avec quelques confreres : donner du feedback constructif "
        "sur les projets des autres pour en recevoir en retour sur les siens. Si certains parmi vous ont des projets "
        "en cours et cherchent des regards critiques, dites-le en commentaire ou faites-moi signe en MP."
    )
    return default_title, default_body

def generate_twitter_reply(tweet_text: str, author_username: str) -> str:
    system_inst = (
        "Tu es un dev francophone authentique qui repond sur X / Twitter. "
        "REGLES STRICTES : "
        "1. ZERO EMOJI. "
        "2. Pas de tiret long. "
        "3. 1 a 2 phrases percutantes, naturelles et directes. "
        "4. Reponds au fond du tweet (technique, architecture ou build). "
        "5. Pas de pub lourde, sois un 'peer' technique interessant."
    )

    prompt = f"Tweet de @{author_username}: {tweet_text}\nEcris une reponse courte de dev."
    generated = query_gemini(system_inst, prompt)
    if generated:
        return strip_emojis(generated)

    fallbacks = [
        "Completement d'accord sur ce point. Le plus dur c'est souvent de maintenir la simplicite du code sur la duree.",
        "Bien vu. Tu as mesure l'impact sur la latence ou c'est encore trop tot dans le process ?",
        "En vrai c'est exactement pour ca qu'il vaut mieux ship vite et avoir des vrais retours plutot que de polir des details inutiles.",
        "Solide approche. C'est quelle stack derriere pour gerer la persistence ?"
    ]
    return random.choice(fallbacks)

def generate_twitter_post() -> str:
    system_inst = (
        "Tu es un build in public dev francophone sur Twitter / X. "
        "REGLES STRICTES : "
        "1. ZERO EMOJI. "
        "2. Pas de tiret long. "
        "3. 2 a 3 lignes max. "
        "4. Reflexion percutante sur le dev, les tests, le build in public ou le feedback entre pairs."
    )

    prompt = "Ecris un tweet technique percutant sur la realite de coder et ship des projets."
    generated = query_gemini(system_inst, prompt)
    if generated:
        return strip_emojis(generated)

    fallbacks = [
        "Un projet non teste en public ne vaut pas grand chose. Le plus vite tu le mets dans les mains d'autres devs, le plus vite tu apprends.",
        "Le meilleur moyen d'obtenir du feedback pertinent sur son code, c'est de commencer par en donner sur les projets des autres.",
        "Moins de temps a peaufiner une landing page, plus de temps a ship des fonctionnelles qui tournent en prod. Le reste c'est du decor."
    ]
    return random.choice(fallbacks)
