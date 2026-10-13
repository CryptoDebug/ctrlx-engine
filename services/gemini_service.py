import aiohttp
import re
import html
import logging
from config import GEMINI_API_KEY

logger = logging.getLogger("CTRLX.Gemini")

GEMINI_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash"
]

def strip_html(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = html.unescape(clean)
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()

def sanitize_text(text: str, max_len: int = 1900) -> str:
    if not text:
        return ""
    clean = text.replace("—", "-").replace("–", "-")
    clean = re.sub(r'^[ \t]*---[ \t]*$', '', clean, flags=re.MULTILINE)
    clean = clean.replace("---", "")
    clean = re.sub(r'<(?:p|span|div|a|b|i|strong|em|br|ul|ol|li|h[1-6]|table|tr|td|th)[^>]*>', ' ', clean, flags=re.IGNORECASE)
    clean = re.sub(r'</(?:p|span|div|a|b|i|strong|em|br|ul|ol|li|h[1-6]|table|tr|td|th)>', ' ', clean, flags=re.IGNORECASE)
    clean = html.unescape(clean)
    clean = re.sub(r'\n{3,}', '\n\n', clean).strip()

    if len(clean) > max_len:
        truncated = clean[:max_len]
        last_nl = truncated.rfind("\n")
        if last_nl > max_len - 300:
            clean = truncated[:last_nl].strip()
        else:
            clean = truncated.strip()
        if "✍️ *Généré par CTRLX AI*" not in clean:
            clean += "\n\n✍️ *Généré par CTRLX AI*"

    return clean.strip()

async def call_gemini(prompt: str, temperature: float = 0.7, max_tokens: int = 1400) -> str:
    if not GEMINI_API_KEY:
        return ""

    async with aiohttp.ClientSession() as session:
        for model in GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            gen_config = {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
            if any(k in model for k in ["3.5-flash", "3.6-flash", "3.7-flash", "3.8-flash"]):
                gen_config["thinkingConfig"] = {"thinkingBudget": 0}

            payload = {
                "contents": [
                    {
                        "parts": [{"text": prompt}]
                    }
                ],
                "generationConfig": gen_config
            }

            try:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        candidates = data.get("candidates", [])
                        if candidates and "content" in candidates[0]:
                            parts = candidates[0]["content"].get("parts", [])
                            if parts:
                                text = parts[0].get("text", "").strip()
                                if text and candidates[0].get("finishReason") != "MAX_TOKENS":
                                    return sanitize_text(text)
                                elif text and len(text) > 400:
                                    return sanitize_text(text)
                    elif resp.status in (429, 503, 404, 400):
                        continue
            except Exception as e:
                logger.debug(f"Gemini call exception on {model}: {e}")

    return ""

async def format_job_offer(raw_title: str, raw_company: str, raw_description: str, job_url: str, job_type: str = "CDI / CDD", location: str = "Paris / Télétravail") -> dict:
    clean_desc = strip_html(raw_description)

    prompt = f"""Tu es le bot officiel de CTRLX, communauté tech & cybersécurité francophone.
Voici les informations d'une offre d'emploi :
- Titre : {raw_title}
- Entreprise : {raw_company}
- Type de contrat supposé : {job_type}
- Localisation : {location}
- Description brute : {clean_desc[:1000]}
- Lien : {job_url}

Consignes strictes :
- N'utilise JAMAIS de balises HTML.
- N'utilise JAMAIS de tiret cadratin '—' ni de séparateur '---'. Aère simplement avec des sauts de ligne.
- Reformate cette offre en respectant STRICTEMENT le format markdown suivant, en français soigné :

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
    result = await call_gemini(prompt, temperature=0.3, max_tokens=500)
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
        f"{clean_desc[:250].strip()}...\n\n"
        f"👉 **Pour postuler :** <{job_url}>"
    )
    return {
        "thread_title": sanitize_text(f"{clean_company} - {clean_title}"[:95]),
        "content": sanitize_text(fallback_content)
    }

async def format_tech_radar_news(title: str, summary: str, url: str, domain: str = "Tech") -> str:
    clean_summary = strip_html(summary)

    prompt = f"""Tu es l'analyste de veille technologique de CTRLX.
Voici une actualité tech / dev / cyber / IA :
- Titre : {title}
- Source / Détails : {clean_summary[:800]}
- Lien : {url}
- Domaine : {domain}

Consignes strictes :
- N'utilise JAMAIS de balises HTML.
- N'utilise JAMAIS le tiret cadratin '—' ni de séparateur '---'.
- Rédige un flash info Discord en français :
1. Une ligne avec un emoji adapté, le titre en gras et le domaine [ex: ⚡ **Titre de la news** (`#Dev` ou `#Cyber` ou `#IA` ou `#Web3` ou `#Hardware`)]
2. 2 phrases percutantes résumant l'impact technique ou l'enjeu concret.
3. Le lien propre formaté : 🔗 Source : <{url}>

Sois direct, pro et percutant. Moins de 350 caractères.
"""
    result = await call_gemini(prompt, temperature=0.5, max_tokens=300)
    if result:
        return sanitize_text(result)

    emojis = {"Cyber": "🛡️", "IA": "🧠", "Dev": "💻", "Web3": "⛓️", "Hardware": "⚙️", "Cloud": "☁️"}
    emoji = emojis.get(domain, "📺")
    return sanitize_text(
        f"{emoji} **{title}** (`#{domain}`)\n"
        f"{clean_summary[:180].strip()}...\n"
        f"🔗 Source : <{url}>"
    )

async def generate_career_tip(exclude_topics: list = None) -> str:
    exclusions_text = ""
    if exclude_topics:
        exclusions_text = f"\nAttention, les sujets suivants ont DÉJÀ été traités récemment et sont strictement interdits : {', '.join(exclude_topics)}.\nPropose un sujet totalement inédit et novateur."

    prompt = f"""Rédige une fiche de conseil carrière pour développeurs et profils cybersécurité francophones sur le Discord CTRLX.{exclusions_text}

Consignes strictes :
- Longueur : STRICTEMENT moins de 1500 caractères au total pour respecter les limites Discord.
- N'utilise JAMAIS de balises HTML.
- N'utilise JAMAIS le tiret cadratin '—' ni de séparateur '---'.
- Aère simplement avec des paragraphes et sauts de ligne clairs.
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
    result = await call_gemini(prompt, temperature=0.85, max_tokens=600)
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

async def generate_formation_guide(exclude_topics: list = None) -> str:
    exclusions_text = ""
    if exclude_topics:
        exclusions_text = f"\nAttention, les sujets suivants ont DÉJÀ été traités récemment et sont strictement interdits : {', '.join(exclude_topics)}.\nPropose un sujet totalement inédit et novateur."

    prompt = f"""Rédige un guide pratique pour le salon #études-et-formations du Discord CTRLX.{exclusions_text}

Consignes strictes :
- Longueur : STRICTEMENT moins de 1500 caractères au total pour respecter les limites Discord.
- N'utilise JAMAIS de balises HTML.
- N'utilise JAMAIS le tiret cadratin '—' ni de séparateur '---'.
- Aère simplement avec des paragraphes et sauts de ligne clairs.
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
    result = await call_gemini(prompt, temperature=0.85, max_tokens=600)
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
    clean_notes = strip_html(release_notes)

    prompt = f"""Une nouvelle technologie ou release majeure vient de sortir :
- Nom : {tech_name}
- Détails : {clean_notes[:800]}
- Lien : {url}

Consignes strictes :
- Longueur : STRICTEMENT moins de 1500 caractères.
- N'utilise JAMAIS de balises HTML.
- N'utilise JAMAIS le tiret cadratin '—' ni de séparateur '---'. Aère simplement avec des sauts de ligne.
- Rédige un guide de prise en main au format de publication CTRLX pour notre forum :
Titre du thread : 🚀 Découverte & Prise en main : {tech_name}

Contenu (Markdown Discord, max 1500 caractères) :
# 🚀 {tech_name.upper()} : CE QU'IL FAUT RETENIR
[Description synthétique : c'est quoi, pourquoi ça change la donne]

## ⚡ Principales nouveautés & Caractéristiques
• **...** : ...
• **...** : ...
• **...** : ...

## 💻 Exemple de code / Prise en main rapide
```[langage]
// Code concret, court et exécutable montrant la syntaxe
```

## 🔗 Ressources officielles
• Documentation : <{url}>

✍️ *Généré par CTRLX AI*
"""
    result = await call_gemini(prompt, temperature=0.6, max_tokens=650)
    if result:
        return {
            "name": sanitize_text(f"🚀 Découverte : {tech_name}"[:95]),
            "content": sanitize_text(result)
        }
    return {}

async def analyze_architecture_or_code(target_text: str, context_info: str = "", focus: str = "Architecture globale") -> str:
    clean_target = strip_html(target_text)
    clean_context = strip_html(context_info)

    prompt = f"""Tu es l'architecte logiciel principal de la communauté CTRLX. Réalise un audit technique et architectural percutant, rigoureux et constructif.
Axe prioritaire demandé : {focus}

Contenu ou projet à auditer :
{clean_target[:1500]}

Contexte technique additionnel :
{clean_context[:1000]}

Directives strictes :
- Rédige en français direct, professionnel et sans verbiage.
- Longueur totale : STRICTEMENT moins de 1700 caractères pour ne pas dépasser la limite de message Discord.
- N'utilise JAMAIS de balises HTML.
- N'utilise JAMAIS le tiret cadratin '—' ni de séparateur '---'. Aère avec des listes à puces et des paragraphes clairs.
- Structure attendue (Markdown Discord) :
# 🔍 AUDIT TECHNIQUE CTRLX : [Nom ou Sujet]
[Synthèse globale en 2 phrases sur la proposition de valeur et la cohérence de la stack]

### 🧱 Architecture & Conception
• **Point fort :** ...
• **Point d'attention :** ...

### 🛡️ Sécurité & Résilience
• **Recommandation :** ...

### ⚡ Performance & Scalabilité
• **Optimisation clé :** ...

> 🎯 **Priorité d'implémentation :** [Conseil direct pour la prochaine étape]

✍️ *Généré par CTRLX AI*
"""
    result = await call_gemini(prompt, temperature=0.7, max_tokens=1400)
    if result:
        return sanitize_text(result)

    return sanitize_text(
        f"# 🔍 AUDIT TECHNIQUE CTRLX : {clean_target[:50]}\n\n"
        f"L'analyse automatisée n'a pas pu contacter le modèle d'IA actuellement.\n\n"
        f"• **Cible soumise :** {clean_target[:200]}\n"
        f"• **Focus demandé :** {focus}\n\n"
        f"> 💡 **Recommandation standard :** Vérifiez la modularité, la gestion des erreurs asynchrones et l'isolation des secrets d'environnement.\n\n"
        f"✍️ *Généré par CTRLX AI*"
    )
