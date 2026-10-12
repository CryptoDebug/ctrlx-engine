import aiohttp
import logging
from config import GEMINI_API_KEY

logger = logging.getLogger("CTRLX.Gemini")

GEMINI_MODELS = ["gemini-3.8-flash", "gemini-flash-latest", "gemini-3.1-flash-lite"]

def sanitize_text(text: str) -> str:
    if not text:
        return ""
    return text.replace("—", "-").replace("–", "-")

async def call_gemini(prompt: str, temperature: float = 0.7, max_tokens: int = 1500) -> str:
    if not GEMINI_API_KEY:
        return ""

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
    }

    async with aiohttp.ClientSession() as session:
        for model in GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            try:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        candidates = data.get("candidates", [])
                        if candidates and "content" in candidates[0]:
                            parts = candidates[0]["content"].get("parts", [])
                            if parts:
                                return sanitize_text(parts[0].get("text", "").strip())
                    elif resp.status in (429, 503, 404):
                        continue
                    else:
                        break
            except Exception as e:
                logger.error(f"Gemini call exception on {model}: {e}")

    return ""

async def format_job_offer(raw_title: str, raw_company: str, raw_description: str, job_url: str, job_type: str = "CDI / CDD", location: str = "Paris / Télétravail") -> dict:
    prompt = f"""Tu es le bot officiel de CTRLX, communauté tech & cybersécurité francophone.
Voici les informations d'une offre d'emploi :
- Titre : {raw_title}
- Entreprise : {raw_company}
- Type de contrat supposé : {job_type}
- Localisation : {location}
- Description brute : {raw_description[:1200]}
- Lien : {job_url}

Consigne : Reformate cette offre en respectant STRICTEMENT le format markdown suivant, en français soigné :
N'utilise JAMAIS le caractère tiret cadratin '—' (utilise uniquement un tiret normal '-' ou des deux-points ':').

**Entreprise / Structure :** [Nom de l'entreprise]
**Poste :** [Titre du poste concis]
**Type de contrat :** [CDI / CDD / Stage / Alternance / Mission Freelance]
**Localisation :** [Ville et modalité télétravail/hybride]
**Rémunération :** [Salaire si mentionné ou 'Selon profil' avec estimation réaliste du marché]
**Stack & Prérequis :** `[4 à 6 technologies ou compétences clés]`

**Description sommaire :**
[2 à 3 phrases claires et percutantes décrivant le projet, la mission principale et la valeur de l'équipe]

👉 **Pour postuler :** <{job_url}>

Ne rajoute AUCUN blabla avant ou après. Renvoie uniquement le texte formaté ci-dessus.
"""
    result = await call_gemini(prompt, temperature=0.3)
    if result and "**Entreprise / Structure :**" in result:
        return {
            "thread_title": sanitize_text(f"{raw_company} - {raw_title}"[:95]),
            "content": sanitize_text(result)
        }

    clean_company = raw_company or "Entreprise Tech"
    clean_title = raw_title or "Développeur / Ingénieur"
    fallback_content = (
        f"**Entreprise / Structure :** {clean_company}\n"
        f"**Poste :** {clean_title}\n"
        f"**Type de contrat :** {job_type}\n"
        f"**Localisation :** {location}\n"
        f"**Rémunération :** Selon profil & grille de l'entreprise\n"
        f"**Stack & Prérequis :** `Tech, Cloud, Best Practices`\n\n"
        f"**Description sommaire :**\n"
        f"{raw_description[:250].strip()}...\n\n"
        f"👉 **Pour postuler :** <{job_url}>"
    )
    return {
        "thread_title": sanitize_text(f"{clean_company} - {clean_title}"[:95]),
        "content": sanitize_text(fallback_content)
    }

async def format_tech_radar_news(title: str, summary: str, url: str, domain: str = "Tech") -> str:
    prompt = f"""Tu es l'analyste de veille technologique de CTRLX.
Voici une actualité tech / dev / cyber / IA :
- Titre : {title}
- Source / Détails : {summary[:800]}
- Lien : {url}
- Domaine : {domain}

Consignes strictes :
- N'utilise JAMAIS le caractère tiret cadratin '—' (utilise '-' ou ':').
- Rédige un flash info Discord en français :
1. Une ligne avec un emoji adapté, le titre en gras et le domaine [ex: ⚡ **Titre de la news** (`#Dev` ou `#Cyber` ou `#IA` ou `#Web3` ou `#Hardware`)]
2. 2 phrases percutantes résumant l'impact technique ou l'enjeu concret.
3. Le lien propre formaté : 🔗 Source : <{url}>

Sois direct, pro et percutant. Pas de formule de politesse. Moins de 400 caractères.
"""
    result = await call_gemini(prompt, temperature=0.5, max_tokens=400)
    if result:
        return sanitize_text(result)

    emojis = {"Cyber": "🛡️", "IA": "🧠", "Dev": "💻", "Web3": "⛓️", "Hardware": "⚙️", "Cloud": "☁️"}
    emoji = emojis.get(domain, "📺")
    return sanitize_text(
        f"{emoji} **{title}** (`#{domain}`)\n"
        f"{summary[:180].strip()}...\n"
        f"🔗 Source : <{url}>"
    )

async def generate_career_tip() -> str:
    prompt = """Rédige une fiche de conseil carrière pour développeurs et profils cybersécurité francophones sur le Discord CTRLX.
Choisis un sujet parmi :
- Comment négocier son salaire en premier emploi tech ou en reconversion
- Les erreurs classiques en entretien technique (live coding, system design)
- Passer de salarié à freelance : statuts (micro vs SASU), calcul du TJM et trouver sa première mission
- Comment valoriser ses projets open source / GitHub pour décrocher des entretiens sans piston
- Savoir dire non aux mauvaises offres et détecter les red flags des ESN / entreprises

Consignes strictes :
- N'utilise JAMAIS le tiret cadratin '—' (utilise '-' ou ':').
- Termine obligatoirement par la signature : ✍️ *Généré par CTRLX AI*

Format attendu (markdown Discord) :
# 💡 CONSEIL CARRIÈRE CTRLX : [Titre accrocheur]
[Courte intro sur le problème concret]

### 🎯 3 Points clés actionnables :
• **1. ...** : explication précise
• **2. ...** : explication précise
• **3. ...** : explication précise

> 💡 **Le piège à éviter :** [Conseil bonus]

✍️ *Généré par CTRLX AI*
"""
    result = await call_gemini(prompt, temperature=0.8, max_tokens=1000)
    if result:
        return sanitize_text(result)

    return sanitize_text(
        "# 💡 CONSEIL CARRIÈRE CTRLX : Comment valoriser vos projets personnels\n\n"
        "Un recruteur technique passe moins de 45 secondes sur un CV. Montrer du code réel fait toute la différence.\n\n"
        "### 🎯 3 Points clés actionnables :\n"
        "• **1. Un README irréprochable** : Expliquez le *pourquoi*, ajoutez un GIF de démo et une commande d'installation en 1 ligne.\n"
        "• **2. Mettre en avant la robustesse** : Des tests unitaires, un pipeline CI/CD et une gestion d'erreurs propre valent mieux que 10 projets inachevés.\n"
        "• **3. Raconter les difficultés résolues** : Mentionnez dans vos entretiens les blocages rencontrés et comment vous les avez surmontés.\n\n"
        "> 💡 **Le piège à éviter :** Ne clonez pas un énième clone de Todo-app sans valeur ajoutée personnelle.\n\n"
        "✍️ *Généré par CTRLX AI*"
    )

async def generate_formation_guide() -> str:
    prompt = """Rédige un guide pratique pour le salon #études-et-formations du Discord CTRLX.
Choisis un sujet à haute valeur ajoutée parmi :
- Les certifications Cybersécurité qui valent vraiment le coup en 2026 (OSCP, CEH, Sec+, etc.)
- Autodidacte vs École d'ingé vs Université : comment compenser les manques de chaque parcours
- Les plateformes gratuites indispensables pour monter de niveau en réseau, linux et algo
- Réussir son alternance tech : organisation, montée en compétences et passage en CDI

Consignes strictes :
- N'utilise JAMAIS le tiret cadratin '—' (utilise '-' ou ':').
- Termine obligatoirement par la signature : ✍️ *Généré par CTRLX AI*

Format attendu (markdown Discord) :
# 🎓 FOCUS ÉTUDES & CERTIFICATIONS : [Titre du sujet]
[Introduction pragmatique]

### 🛠️ Ce qu'il faut savoir :
• **Ressources recommandées :** [Plateformes réelles, cours reconnus]
• **Investissement temps & budget :** [Chiffres réalistes]
• **Impact sur le CV :** [Ce que les recruteurs regardent vraiment]

> 📌 **Conseil clé CTRLX :** [Astuce concrète]

✍️ *Généré par CTRLX AI*
"""
    result = await call_gemini(prompt, temperature=0.8, max_tokens=1000)
    if result:
        return sanitize_text(result)

    return sanitize_text(
        "# 🎓 FOCUS ÉTUDES & CERTIFICATIONS : Les certifs Cyber à viser en priorité\n\n"
        "Toutes les certifications ne se valent pas sur le marché. Voici comment investir votre temps et votre énergie intelligemment.\n\n"
        "### 🛠️ Ce qu'il faut savoir :\n"
        "• **Ressources recommandées :** TryHackMe (socle), HackTheBox (pratique avancée), PortSwigger Web Security Academy (gratuit et référence web).\n"
        "• **Certifications phares :** CompTIA Security+ pour valider les fondamentaux, OSCP pour le pentest offensif réel.\n"
        "• **Impact sur le CV :** Les recruteurs recherchent des lab tests concrets plutôt que des QCM purement théoriques.\n\n"
        "> 📌 **Conseil clé CTRLX :** Documentez vos write-ups publiquement sur un blog ou GitHub pour prouver votre méthodologie.\n\n"
        "✍️ *Généré par CTRLX AI*"
    )

async def generate_tutorial_for_tech(tech_name: str, release_notes: str, url: str) -> dict:
    prompt = f"""Une nouvelle technologie ou release majeure vient de sortir :
- Nom : {tech_name}
- Détails : {release_notes[:1000]}
- Lien : {url}

Consignes strictes :
- N'utilise JAMAIS le caractère tiret cadratin '—' (utilise '-' ou ':').
- Rédige un guide de prise en main au format de publication CTRLX pour notre forum :
Titre du thread : 🚀 Découverte & Prise en main : {tech_name}

Contenu (Markdown Discord, max 1600 caractères) :
# 🚀 {tech_name.upper()} : CE QU'IL FAUT RETENIR
[Description synthétique : c'est quoi, pourquoi ça change la donne]

---
## ⚡ Principales nouveautés & Caractéristiques
• **...** : ...
• **...** : ...
• **...** : ...

---
## 💻 Exemple de code / Prise en main rapide
```[langage]
// Code concret, court et exécutable montrant la syntaxe
```

---
## 🔗 Ressources officielles
• Documentation : <{url}>

✍️ *Généré par CTRLX AI*
"""
    result = await call_gemini(prompt, temperature=0.6, max_tokens=1200)
    if result:
        return {
            "name": sanitize_text(f"🚀 Découverte : {tech_name}"[:95]),
            "content": sanitize_text(result)
        }
    return {}
