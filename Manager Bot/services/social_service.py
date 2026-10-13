import logging
from services.gemini_service import call_gemini, sanitize_text

logger = logging.getLogger("CTRLX.Social")

async def generate_social_pack(topic: str = "la veille cybersécurité et l'entraide entre builders") -> dict:
    prompt = f"""Tu es un expert en Growth et Social Media pour la communauté tech & cybersécurité francophone CTRLX.
Rédige un kit de 3 posts distincts pour promouvoir CTRLX autour du sujet : '{topic}'.
N'utilise JAMAIS le tiret cadratin '—' (utilise uniquement un tiret normal '-' ou ':').

1. FORMAT LINKEDIN :
- Style : Storytelling sincère, accroche courte percutante en première ligne, saut de ligne, 3 puces de valeur concrète, appel à rejoindre la commu, 4 hashtags pertinents. Pas de blabla corporatiste vide.

2. FORMAT X (TWITTER) :
- Style : Punchy, moins de 250 caractères, axé veille / ressource concrète ou réflexion tech, mention du Discord.

3. FORMAT REDDIT (Adapté à r/developpeurs ou r/france) :
- Style : Zéro marketing, zéro commercial. Présente ça comme un retour d'expérience ou un partage de ressources gratuites créées collectivement.

Sépare bien chaque section avec les marqueurs :
[LINKEDIN]
...
[TWITTER]
...
[REDDIT]
...
"""
    result = await call_gemini(prompt, temperature=0.7, max_tokens=1400)
    
    if "[LINKEDIN]" in result and "[TWITTER]" in result and "[REDDIT]" in result:
        try:
            part_li = sanitize_text(result.split("[LINKEDIN]")[1].split("[TWITTER]")[0].strip())
            part_tw = sanitize_text(result.split("[TWITTER]")[1].split("[REDDIT]")[0].strip())
            part_rd = sanitize_text(result.split("[REDDIT]")[1].strip())
            return {
                "linkedin": part_li,
                "twitter": part_tw,
                "reddit": part_rd
            }
        except Exception:
            pass

    return {
        "linkedin": sanitize_text(
            "Pourquoi tant de serveurs tech finissent par mourir ?\n\n"
            "Trop de bruit, zéro structure, et des salons d'offres fantômes.\n\n"
            "Sur CTRLX, on a fait le choix inverse :\n"
            "• Des cours concrets avec du code réel (C, Rust, Go, Python, ASM)\n"
            "• Un radar de veille continue sur la cyber et les failles en temps réel\n"
            "• Des opportunités d'emploi filtrées et des créateurs qui buildent ensemble\n\n"
            "Si tu cherches un endroit propre pour échanger entre passionnés : le lien est en premier commentaire.\n\n"
            "#Tech #Cybersecurite #Developpeurs #OpenSource"
        ),
        "twitter": sanitize_text(
            "Marre des serveurs Discord tech déserts ou remplis de spam ?\n\n"
            "Rejoins CTRLX : veille cyber quotidienne, guides techniques réels (Rust, C, ASM, OSINT) et entraide entre builders francophones. 🚀\n\n"
            "👉 https://discord.gg/ctrlx"
        ),
        "reddit": sanitize_text(
            "Titre : On a centralisé des fiches techniques et de veille cyber/dev gratuites sur Discord\n\n"
            "Salut la commu ! Petit retour d'expérience : on a remarqué que beaucoup de débutants et passionnés peinaient à trouver des cours bien structurés sur le reverse engineering, l'OSINT et les langages bas-niveau sans tomber sur des tutos payants bidons.\n\n"
            "On a donc créé un espace d'entraide (CTRLX) avec des guides condensés, des exemples de code et une veille active. Pas de formation payante à vendre, juste du partage entre builders et devs. Si vous voulez jeter un œil ou contribuer, vous êtes les bienvenus."
        )
    }
