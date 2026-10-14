import re
import random
import urllib.request
import json
from config import GEMINI_API_KEY, DISCORD_INVITE_URL
from database import is_content_already_used

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
            "temperature": 0.85,
            "maxOutputTokens": 300
        }
    }

    data_bytes = json.dumps(payload).encode("utf-8")
    models = [
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash"
    ]

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        try:
            req = urllib.request.Request(
                url,
                data=data_bytes,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        text = parts[0].get("text", "").strip()
                        if text:
                            return text
        except Exception:
            continue
    return ""

def select_unused_or_random(options: list) -> str:
    unused = [opt for opt in options if not is_content_already_used(opt)]
    if unused:
        return random.choice(unused)
    return random.choice(options)

def generate_reddit_reply(post_title: str, post_body: str, subreddit: str) -> str:
    is_english = subreddit.lower() in ["sideproject", "webdev", "python"]
    if is_english:
        system_inst = (
            "You are an independent developer replying naturally and concisely on Reddit. "
            "STRICT RULES: "
            "1. ZERO EMOJIS. None. "
            "2. No em dashes and no triple hyphens. "
            "3. Never sound like an AI assistant. Be direct, pragmatic, humble (1 to 2 sentences max). "
            "4. Respond directly to the specific technical choice, tool, or dilemma described by the author. "
            "5. Avoid generic praise like 'Great project' or 'Looks awesome'. Dive into a concrete angle."
        )
        prompt = (
            f"Subreddit: r/{subreddit}\n"
            f"Post title: {post_title}\n"
            f"Post content: {post_body[:600]}\n\n"
            "Write a unique, concise, context-specific developer reply."
        )
    else:
        system_inst = (
            "Tu es un développeur francophone indépendant qui intervient sur Reddit. "
            "RÈGLES STRICTES ET NON NÉGOCIABLES : "
            "1. AUCUN EMOJI. Zéro emoji. "
            "2. Pas de tiret long ni de triples tirets. "
            "3. Respecte rigoureusement l'orthographe française avec tous les accents nécessaires (é, è, ê, à, â, î, ï, ô, ù, û, ç). "
            "4. Ne parle JAMAIS comme une IA : pas de formules du type 'C'est une excellente question', 'Voici quelques conseils', 'En tant que développeur'. "
            "5. Sois très concis (1 à 2 phrases directes et percutantes). "
            "6. Réagis spécifiquement au sujet ou à la stack mentionnée dans le post (architecture, persistance, UX, maintien du code, validation). "
            "7. Si pertinent, invite à échanger en message privé pour des retours techniques mutuels."
        )
        prompt = (
            f"Subreddit: r/{subreddit}\n"
            f"Titre du post: {post_title}\n"
            f"Contenu du post: {post_body[:600]}\n\n"
            "Écris une réponse unique, courte et pertinente avec tous les accents français."
        )

    generated = query_gemini(system_inst, prompt)
    if generated:
        cleaned = strip_emojis(generated)
        if len(cleaned) > 15 and not is_content_already_used(cleaned):
            return cleaned

    if is_english:
        fallbacks = [
            "Nice execution. What stack did you choose for the backend? If you need honest technical feedback feel free to DM me.",
            "Solid project. Getting real developers to test early is always the hardest part. Let me know if you want detailed feedback.",
            "Had a very similar architecture challenge on a previous project. Keeping the scope strictly minimal saved me tons of refactoring time.",
            "Looks clean. Are you planning to open-source the core parts or keep it closed? Always curious about solo dev stacks.",
            "Great progress. How are you handling state persistence across sessions? Curious about the technical choices behind this.",
            "The UI looks minimal and functional. Have you had any real users test the core workflow yet?",
            "Clean implementation. What was the biggest bottleneck you ran into while building this MVP?",
            "Looks promising. If you ever need someone to stress-test your API or give UX feedback, feel free to drop a DM.",
            "Very solid start. Are you deploying this on a VPS or using serverless infrastructure for the backend?",
            "Smart approach. Focusing on one specific pain point before expanding features is definitely the right call.",
            "Interesting setup. How are you approaching database migrations as the data model evolves?",
            "Neat solution. Have you considered adding webhook support for devs who want to automate around this?",
            "Impressive solo build. Are you noticing any friction on the onboarding flow so far?",
            "Appreciate the honest writeup. Shipping early with rough edges beats polishing in isolation every single time."
        ]
    else:
        fallbacks = [
            "En vrai c'est un problème classique quand on commence un projet. Tu as testé de découper ton architecture en petits modules indépendants ? Ça m'avait pas mal débloqué sur un script similaire.",
            "Projet intéressant. Le plus dur reste d'avoir les premiers testeurs pour valider l'UX. Perso je passe par un groupe d'entraide où on teste les apps des uns et des autres, ça évite de lancer dans le vide. Dis-moi si tu veux des retours dessus en MP.",
            "Bien joué pour le lancement. Tu comptes open-source le code ou garder ça fermé ? Si tu cherches du retour technique sur l'architecture n'hésite pas.",
            "Perso j'étais tombé sur le même écueil avec ce genre de stack. Le truc qui m'a sauvé c'était de réduire le périmètre au minimum avant de rajouter d'autres fonctionnalités.",
            "Très propre comme réalisation. La plus grande difficulté reste souvent la rétention des utilisateurs initiaux. Si tu as besoin d'un regard critique extérieur fais signe en message privé.",
            "Belle initiative. Tu as prévu quoi pour gérer la montée en charge ou la persistance des données si le trafic augmente ?",
            "C'est souvent sur la phase d'onboarding que les premiers utilisateurs décrochent. Tu as déjà pu observer des testeurs utiliser l'interface en direct sans consignes ?",
            "Bonne approche sur le découpage technique. Si tu as besoin d'un test croisé approfondi sur l'ergonomie, on fait régulièrement ça entre confrères indépendants.",
            "Ce genre de brique technique est toujours gratifiant à coder. Tu penses monétiser le projet ou c'est un pur side-project d'apprentissage technique ?",
            "J'aime bien l'idée. Le principal défi c'est souvent d'éviter la complexité accidentelle au début. Moins de dépendances, plus de sérénité sur la maintenance.",
            "L'interface a l'air claire. Tu es parti sur quel framework CSS ou c'est fait maison ? Preneur de ton ressenti après ces semaines de dév.",
            "Sur des projets similaires, ce qui m'a fait gagner le plus de temps c'était de mettre en place une CI ultra légère dès le départ pour valider chaque release.",
            "Solide réalisation. Si tu cherches des retours constructifs et sans complaisance sur le code ou l'UX, hésite pas à m'envoyer un message privé.",
            "Le concept est pertinent. Est-ce que tu as déjà envisagé d'ajouter une API publique pour permettre à d'autres devs d'automatiser des flux dessus ?",
            "Chouette travail. Le plus difficile commence maintenant avec l'acquisition des premiers utilisateurs. Bon courage pour la suite de la roadmap technique.",
            "La simplification de l'architecture paie toujours sur la durée. Tu as mesuré l'impact sur la latence ou c'est encore trop tôt dans ton cycle ?"
        ]

    return select_unused_or_random(fallbacks)

def generate_reddit_post(topic: str = "feedback_problem") -> tuple[str, str]:
    system_inst = (
        "Tu es un dev qui partage une réflexion sincère sur Reddit dans une communauté de développeurs francophones. "
        "RÈGLES STRICTES : "
        "1. ZÉRO EMOJI. "
        "2. Aucun lien direct (les liens discord sont interdits dans les posts). "
        "3. Pas de tiret long ni de triples tirets. "
        "4. Orthographe française soignée avec tous les accents corrects (é, è, ê, à, ç, etc.). "
        "5. Style français direct, honnête, orienté craft et retours d'expérience. "
        "6. Termine en invitant les membres intéressés par des tests croisés à répondre en commentaire ou en MP."
    )

    prompt = (
        "Génère un titre percutant et un texte de 3 ou 4 courts paragraphes sur le problème "
        "du manque de testeurs et de feedback quand on code des projets solo, et comment une logique d'entraide "
        "permet de progresser ensemble. Sépare le titre et le texte par la ligne '===SEPARATOR==='."
    )

    generated = query_gemini(system_inst, prompt)
    if generated and "===SEPARATOR===" in generated:
        parts = generated.split("===SEPARATOR===", 1)
        title = strip_emojis(parts[0].replace("Titre :", "").replace("Titre:", "").strip())
        body = strip_emojis(parts[1].strip())
        if not is_content_already_used(title):
            return title, body

    default_posts = [
        (
            "Le plus gros frein quand on dév solo : coder dans le vide sans testeurs",
            "Salut tout le monde,\n\nJe discutais avec pas mal de développeurs ces derniers temps et le constat est toujours le même : on passe des semaines à monter un side-project ou un outil cool, et dès qu'on le partage, presque personne ne prend le temps de regarder le code ou de tester l'application.\n\nSans retours concrets sur l'UX ou l'architecture, la motivation retombe vite.\n\nOn essaie de tester un fonctionnement simple avec quelques confrères : donner du feedback constructif sur les projets des autres pour en recevoir en retour sur les siens. Si certains parmi vous ont des projets en cours et cherchent des regards critiques, dites-le en commentaire ou faites-moi signe en MP."
        ),
        (
            "Pourquoi c'est si dur d'avoir un retour sincère sur son code en solo ?",
            "Bonjour à tous,\n\nQuand on bosse en équipe, la code review et les retours font partie du quotidien. Mais dès qu'on se lance sur un outil ou un side-project solo, on se retrouve souvent seul face à son écran sans personne pour challenger nos choix d'architecture ou pointer un défaut d'ergonomie évident.\n\nDemander des avis sur les réseaux donne souvent des félicitations polies mais rarement des critiques constructives en profondeur.\n\nEst-ce que certains d'entre vous ont réussi à mettre en place un système de peer-testing régulier entre devs ? Preneur de vos retours d'expérience là-dessus."
        )
    ]
    for t, b in default_posts:
        if not is_content_already_used(t):
            return t, b
    return default_posts[0]

def generate_twitter_reply(tweet_text: str, author_username: str) -> str:
    system_inst = (
        "Tu es un dev francophone authentique qui répond sur X / Twitter. "
        "RÈGLES STRICTES : "
        "1. ZÉRO EMOJI. "
        "2. Pas de tiret long. "
        "3. Orthographe française impeccable avec tous les accents nécessaires (é, è, ê, à, â, î, ï, ô, ù, û, ç). "
        "4. 1 à 2 phrases percutantes, naturelles et directes. "
        "5. Réponds au fond du tweet (technique, architecture ou build). "
        "6. Pas de pub lourde, sois un 'peer' technique intéressant."
    )

    prompt = f"Tweet de @{author_username}: {tweet_text}\nÉcris une réponse courte de dev avec tous les accents français."
    generated = query_gemini(system_inst, prompt)
    if generated:
        cleaned = strip_emojis(generated)
        if len(cleaned) > 10 and not is_content_already_used(cleaned):
            return cleaned

    fallbacks = [
        "Complètement d'accord sur ce point. Le plus dur c'est souvent de maintenir la simplicité du code sur la durée.",
        "Bien vu. Tu as mesuré l'impact sur la latence ou c'est encore trop tôt dans le process ?",
        "En vrai c'est exactement pour ça qu'il vaut mieux livrer vite et avoir des vrais retours plutôt que de polir des détails inutiles.",
        "Solide approche. C'est quelle stack derrière pour gérer la persistance ?",
        "Tellement vrai. Trop de devs passent trois semaines sur l'UI avant même de valider la logique métier.",
        "Le découpage modulaire paie toujours dès que le code commence à grandir.",
        "Totalement aligné. Les premiers testeurs apprennent plus en dix minutes que trois semaines d'hypothèses en solo."
    ]
    return select_unused_or_random(fallbacks)

def generate_twitter_post() -> str:
    system_inst = (
        "Tu es un dev build in public francophone sur Twitter / X. "
        "RÈGLES STRICTES : "
        "1. ZÉRO EMOJI. "
        "2. Pas de tiret long. "
        "3. Orthographe française impeccable avec tous les accents corrects (é, è, ê, à, â, î, ï, ô, ù, û, ç). "
        "4. 2 à 3 lignes max. "
        "5. Réflexion percutante sur le dev, les tests, le build in public ou le feedback entre pairs."
    )

    prompt = "Écris un tweet technique percutant et unique sur la réalité de coder et livrer des projets avec tous les accents français."
    generated = query_gemini(system_inst, prompt)
    if generated:
        cleaned = strip_emojis(generated)
        if len(cleaned) > 15 and not is_content_already_used(cleaned):
            return cleaned

    fallbacks = [
        "Un projet non testé en public ne vaut pas grand-chose. Le plus vite tu le mets dans les mains d'autres développeurs, le plus vite tu apprends.",
        "Le meilleur moyen d'obtenir du feedback régulier sur son code, c'est de commencer par tester les projets de ses confrères.",
        "Moins de temps à peaufiner une landing page, plus de temps à livrer des fonctionnalités qui tournent en prod. Le reste c'est du décor.",
        "L'erreur classique du dev solo : coder pendant six mois en secret pour réaliser le premier jour que personne ne comprend l'interface.",
        "Livrer un MVP imparfait et observer les retours surpasse n'importe quel plan d'architecture rédigé dans le vide.",
        "La meilleure documentation d'une application reste une interface où l'utilisateur n'a jamais besoin de deviner quoi faire."
    ]
    return select_unused_or_random(fallbacks)

def generate_facebook_post() -> str:
    system_inst = (
        "Tu es un développeur qui partage une réflexion utile sur Facebook dans des communautés de développeurs francophones. "
        "RÈGLES STRICTES : "
        "1. ZÉRO EMOJI. Absolument aucun emoji. "
        "2. Pas de tiret long ni de triples tirets. "
        "3. Orthographe française soignée avec tous les accents nécessaires (é, è, ê, à, â, î, ï, ô, ù, û, ç). "
        "4. Ton constructif, bienveillant et orienté entraide technique (2 à 3 paragraphes courts). "
        "5. Parle de la difficulté d'avoir des retours techniques objectifs quand on dev en solo, et propose d'échanger des tests croisés en MP."
    )

    prompt = "Écris un post pour un groupe Facebook de développeurs sur l'importance du peer-testing et des retours constructifs avec tous les accents."
    generated = query_gemini(system_inst, prompt)
    if generated:
        cleaned = strip_emojis(generated)
        if len(cleaned) > 20 and not is_content_already_used(cleaned):
            return cleaned

    fallbacks = [
        "Petite réflexion de développeur : on passe souvent des semaines à construire un side-project dans son coin, et une fois en ligne, difficile d'avoir des retours pertinents sans budget marketing.\n\nLe moyen le plus efficace que j'ai trouvé, c'est l'échange direct : tester l'outil d'un autre dev en profondeur en échange d'un retour similaire sur le mien. Si certains d'entre vous ont des projets à tester en ce moment, faites signe en MP ou en commentaire.",
        "À quel moment considérez-vous qu'un projet est prêt à être montré ? Perso j'avais tendance à attendre que tout soit parfait, mais c'est le meilleur moyen de perdre du temps sur de mauvaises suppositions.\n\nMaintenant je montre une version brute le plus tôt possible à quelques confrères de confiance. Preneur de votre façon de faire là-dessus.",
        "Coder un outil solo c'est stimulant, mais sans regards extérieurs on a vite des angles morts sur l'ergonomie ou l'architecture.\n\nOn a lancé des sessions d'échanges et de revues mutuelles entre développeurs pour s'entraider sur nos projets respectifs. Si vous avez une application ou un projet en cours et cherchez des retours sincères, écrivez-moi en MP."
    ]
    return select_unused_or_random(fallbacks)

def should_and_generate_followup_reply(incoming_text: str, context_text: str = "", language: str = "fr") -> str | None:
    is_en = language.lower() in ["en", "english"]
    if is_en:
        system_inst = (
            "You are a developer in a tech discussion. A user replied to your previous message. "
            "DECISION RULES: "
            "1. If the message is a polite closing statement without any question or need for reply "
            "(e.g. 'thanks', 'cool', 'sadly no', 'ok', 'no problem', 'understood', 'perfect'), output EXACTLY 'NO_REPLY'. "
            "2. If the user asks a question, requests details, mentions an issue, or asks for a link / contact, "
            "write a short, humble, genuine developer reply (1 to 2 sentences max). "
            "3. ZERO EMOJIS. No em dashes or triple hyphens."
        )
        prompt = f"Received message: '{incoming_text}'\nContext: '{context_text}'\nDecide if reply is needed or output NO_REPLY."
    else:
        system_inst = (
            "Tu es un développeur intervenant dans une discussion technique. Un utilisateur a répondu à l'un de tes messages. "
            "RÈGLES DÉCISIONNELLES : "
            "1. Si le message reçu est une réponse de fin de conversation ne demandant rien "
            "(ex: 'merci', 'cool', 'ok', 'pas de souci', 'd\\'accord', 'super', 'top', 'parfait', 'ça marche'), "
            "réponds STRICTEMENT 'NO_REPLY'. "
            "2. Si l'utilisateur pose une question, demande des précisions, exprime un besoin d'aide ou demande des détails ou un contact, "
            "rédige une réponse courte, humble et naturelle (1 à 2 phrases max). "
            "3. Respecte impérativement l'orthographe française avec tous les accents corrects (é, è, ê, à, â, î, ï, ô, ù, û, ç). "
            "4. ZÉRO EMOJI. Pas de tirets longs."
        )
        prompt = f"Message reçu : '{incoming_text}'\nContexte : '{context_text}'\nDétermine si une réponse est nécessaire ou écris NO_REPLY."

    generated = query_gemini(system_inst, prompt)
    if generated:
        cleaned = strip_emojis(generated).strip()
        if "NO_REPLY" in cleaned or len(cleaned) < 5:
            return None
        return cleaned

    low = incoming_text.lower().strip()
    closed_cues = [
        "merci", "merci bcp", "merci beaucoup", "thanks", "thank you", "thx",
        "cool", "top", "super", "ok", "d'accord", "dac", "no problem", "pas de souci",
        "sadly no", "yes", "oui", "parfait", "bien vu", "ça marche", "ca marche", "noted"
    ]
    if any(low == cue or low.startswith(cue + " ") or low.endswith(" " + cue) for cue in closed_cues) and "?" not in low:
        return None

    request_cues = [
        "comment", "pourquoi", "lien", "mp", "discord", "stack", "combien",
        "repo", "github", "chaud", "intéressé", "intéressée", "test", "dispo",
        "tu penses", "tu utilises", "votre", "ton projet", "adresse", "contact"
    ]
    if "?" in low or any(k in low for k in request_cues):
        if is_en:
            fallbacks_en = [
                "Totally, feel free to drop me a DM if you want to chat more about this or exchange feedback.",
                "Glad to help. Shoot me a direct message if you want us to take a look at your build.",
                "Happy to check it out. Send over a DM with the repo or link whenever you have a moment."
            ]
            return select_unused_or_random(fallbacks_en)
        else:
            fallbacks_fr = [
                "Carrément, hésite pas à m'envoyer un message privé si tu veux en discuter plus en détail ou tester nos projets respectifs.",
                "Avec plaisir, passe en MP quand tu veux pour qu'on regarde ça et qu'on échange nos retours techniques.",
                "C'est une bonne question. En gros on privilégie l'échange direct de retours entre devs. Envoie-moi un MP si tu veux qu'on teste ton projet.",
                "Je serais ravi de jeter un œil. Envoie-moi un message en privé avec le lien du projet dès que tu as cinq minutes."
            ]
            return select_unused_or_random(fallbacks_fr)

    return None
