import os
import sys
import time
import re
import urllib.parse
import logging
from playwright.sync_api import sync_playwright

logger = logging.getLogger("CTRLX.Social.Browser")

SESSION_DIR = os.path.join(os.path.dirname(__file__), "sessions")
os.makedirs(SESSION_DIR, exist_ok=True)

def get_session_path(platform: str) -> str:
    return os.path.join(SESSION_DIR, f"{platform.lower()}_state.json")

def has_valid_session(platform: str) -> bool:
    session_file = get_session_path(platform)
    return os.path.exists(session_file) and os.path.getsize(session_file) > 50

def is_display_available() -> bool:
    if sys.platform == "win32":
        return True
    return bool(os.environ.get("DISPLAY"))

def get_browser_executable() -> str | None:
    if sys.platform.startswith("linux"):
        for path in ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/firefox"]:
            if os.path.exists(path):
                return path
    return None

def get_launch_kwargs(headless: bool = True) -> dict:
    kwargs = {"headless": headless}
    exec_path = get_browser_executable()
    if exec_path:
        kwargs["executable_path"] = exec_path
    if sys.platform.startswith("linux"):
        kwargs["args"] = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu"
        ]
    return kwargs

def interactive_login(platform: str) -> bool:
    platform = platform.lower()
    target_urls = {
        "twitter": "https://x.com/login",
        "reddit": "https://www.reddit.com/login",
        "facebook": "https://www.facebook.com/login"
    }

    if platform not in target_urls:
        print(f"Plateforme inconnue : {platform}")
        return False

    if not is_display_available():
        print(f"Affichage graphique indisponible pour connexion interactive à {platform.upper()}.")
        print(f"Sur Raspberry Pi headless, copiez le fichier {get_session_path(platform)} depuis votre ordinateur principal.")
        return False

    url = target_urls[platform]
    session_file = get_session_path(platform)

    print(f"\nOuverture du navigateur pour connexion à {platform.upper()}...")
    print("Veuillez vous authentifier sur la fenêtre qui vient de s'ouvrir.")

    with sync_playwright() as p:
        launch_kwargs = get_launch_kwargs(headless=False)
        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context()

        page = context.new_page()
        page.goto(url)

        input(f"\nAppuyez sur [Entrée] dans ce terminal une fois connecté à {platform.upper()}...")

        context.storage_state(path=session_file)
        print(f"Session {platform.upper()} sauvegardée avec succès dans {session_file}")
        browser.close()

    return True

def ensure_session(platform: str) -> bool:
    if has_valid_session(platform):
        return True
    if is_display_available():
        logger.info(f"Session manquante pour {platform}. Lancement de l'authentification interactive...")
        return interactive_login(platform)
    logger.warning(f"Session manquante pour {platform} en mode headless sans écran.")
    return False

def ensure_all_sessions():
    for p in ["twitter", "facebook"]:
        if not has_valid_session(p):
            ensure_session(p)

def post_tweet_browser(text: str) -> bool:
    session_file = get_session_path("twitter")
    if not os.path.exists(session_file):
        logger.warning("Session Twitter introuvable. Authentifiez-vous d'abord.")
        return False

    with sync_playwright() as p:
        launch_kwargs = get_launch_kwargs(headless=True)
        browser = p.chromium.launch(**launch_kwargs)
        try:
            context = browser.new_context(storage_state=session_file)
            page = context.new_page()
            page.goto("https://x.com/compose/post", timeout=30000)

            box = page.wait_for_selector("div[role='textbox']", timeout=20000)
            if not box:
                logger.error("Impossible de trouver la zone de saisie Twitter.")
                return False

            box.click(force=True)
            box.fill(text)
            page.wait_for_timeout(1500)

            btn = page.wait_for_selector("button[data-testid='tweetButton']", timeout=10000)
            if not btn:
                logger.error("Bouton de publication Twitter introuvable.")
                return False

            btn.click(force=True)
            page.wait_for_timeout(5000)

            context.storage_state(path=session_file)
            return True
        except Exception as e:
            logger.error(f"Erreur de publication du tweet via navigateur : {e}")
            return False
        finally:
            browser.close()

def reply_tweet_browser(tweet_id: str, text: str) -> bool:
    session_file = get_session_path("twitter")
    if not os.path.exists(session_file):
        return False

    with sync_playwright() as p:
        launch_kwargs = get_launch_kwargs(headless=True)
        browser = p.chromium.launch(**launch_kwargs)
        try:
            context = browser.new_context(storage_state=session_file)
            page = context.new_page()
            url = f"https://x.com/i/status/{tweet_id}"
            page.goto(url, timeout=30000)
            page.wait_for_timeout(2500)

            box = page.wait_for_selector("div[role='textbox']", timeout=15000)
            if not box:
                return False

            box.click(force=True)
            box.fill(text)
            page.wait_for_timeout(1500)

            btn = page.wait_for_selector("button[data-testid='tweetButtonInline']", timeout=8000) or \
                  page.wait_for_selector("button[data-testid='tweetButton']", timeout=5000)
            if not btn:
                return False

            btn.click(force=True)
            page.wait_for_timeout(4000)
            context.storage_state(path=session_file)
            return True
        except Exception as e:
            logger.error(f"Erreur réponse tweet {tweet_id} via navigateur : {e}")
            return False
        finally:
            browser.close()

def check_twitter_mentions_browser() -> list:
    session_file = get_session_path("twitter")
    if not os.path.exists(session_file):
        return []

    with sync_playwright() as p:
        launch_kwargs = get_launch_kwargs(headless=True)
        browser = p.chromium.launch(**launch_kwargs)
        mentions = []
        try:
            context = browser.new_context(storage_state=session_file)
            page = context.new_page()
            page.goto("https://x.com/notifications/mentions", timeout=30000)
            page.wait_for_timeout(4000)

            articles = page.query_selector_all("article[data-testid='tweet']")
            for art in articles[:6]:
                try:
                    text_elem = art.query_selector("div[data-testid='tweetText']")
                    tweet_text = text_elem.inner_text() if text_elem else ""

                    time_link = art.query_selector("time")
                    parent_link = time_link.evaluate("el => el.closest('a')?.getAttribute('href')") if time_link else None
                    if parent_link and "/status/" in parent_link:
                        t_id = parent_link.split("/status/")[1].split("?")[0]
                        mentions.append({
                            "id": t_id,
                            "text": tweet_text,
                            "url": f"https://x.com{parent_link}"
                        })
                except Exception:
                    continue
            return mentions
        except Exception as e:
            logger.warning(f"Erreur vérification mentions Twitter : {e}")
            return []
        finally:
            browser.close()

def post_facebook_browser(text: str) -> bool:
    session_file = get_session_path("facebook")
    if not os.path.exists(session_file):
        logger.warning("Session Facebook introuvable. Authentifiez-vous d'abord.")
        return False

    with sync_playwright() as p:
        launch_kwargs = get_launch_kwargs(headless=True)
        browser = p.chromium.launch(**launch_kwargs)
        try:
            context = browser.new_context(storage_state=session_file)
            page = context.new_page()
            page.goto("https://www.facebook.com", timeout=30000)
            page.wait_for_timeout(3500)

            composer_loc = page.locator("div[role='button']").filter(
                has_text=re.compile(r"Quoi de neuf|Que voulez-vous|What's on your mind|Exprimer|Créer une publication", re.I)
            ).first

            if composer_loc.count() == 0:
                logger.error("Zone de composition Facebook introuvable sur la page d'accueil.")
                return False

            composer_loc.click(force=True)
            page.wait_for_timeout(2500)

            textbox = page.locator("div[role='textbox']").first
            if textbox.count() == 0:
                logger.error("Zone de saisie de texte Facebook introuvable après ouverture.")
                return False

            textbox.click(force=True)
            page.wait_for_timeout(500)
            textbox.fill(text)
            page.wait_for_timeout(2000)

            post_btn = page.locator(
                "div[aria-label='Publier'][role='button'], div[aria-label='Post'][role='button'], div[role='button']:has-text('Publier')"
            ).first

            if post_btn.count() == 0:
                logger.error("Bouton de publication Facebook introuvable.")
                return False

            post_btn.click(force=True)
            page.wait_for_timeout(5000)
            context.storage_state(path=session_file)
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la publication Facebook : {e}")
            return False
        finally:
            browser.close()

def search_and_discover_facebook_groups(query: str, limit: int = 5) -> list:
    session_file = get_session_path("facebook")
    if not os.path.exists(session_file):
        return []

    with sync_playwright() as p:
        launch_kwargs = get_launch_kwargs(headless=True)
        browser = p.chromium.launch(**launch_kwargs)
        discovered = []
        try:
            context = browser.new_context(storage_state=session_file)
            page = context.new_page()
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://www.facebook.com/search/groups/?q={encoded_query}"
            page.goto(search_url, timeout=30000)
            page.wait_for_timeout(4000)

            anchors = page.query_selector_all("a[href*='/groups/']")
            system_tokens = ["feed", "discover", "joins", "create", "notifications", "search", "category"]

            for a in anchors:
                href = a.get_attribute("href") or ""
                match = re.search(r"facebook\.com/groups/([^/?]+)", href)
                if not match:
                    match = re.search(r"/groups/([^/?]+)", href)
                if not match:
                    continue

                gid = match.group(1)
                if any(tok in gid.lower() for tok in system_tokens):
                    continue

                name = a.inner_text().strip()
                if not name or len(name) < 3:
                    continue

                clean_url = f"https://www.facebook.com/groups/{gid}/"
                if not any(d["group_id"] == gid for d in discovered):
                    discovered.append({
                        "group_id": gid,
                        "group_name": name.split("\n")[0].strip(),
                        "group_url": clean_url
                    })
                if len(discovered) >= limit:
                    break
            return discovered
        except Exception as e:
            logger.warning(f"Erreur lors de la recherche de groupes Facebook ({query}) : {e}")
            return []
        finally:
            browser.close()

def post_facebook_group_browser(group_url: str, text: str) -> bool:
    session_file = get_session_path("facebook")
    if not os.path.exists(session_file):
        return False

    with sync_playwright() as p:
        launch_kwargs = get_launch_kwargs(headless=True)
        browser = p.chromium.launch(**launch_kwargs)
        try:
            context = browser.new_context(storage_state=session_file)
            page = context.new_page()
            page.goto(group_url, timeout=30000)
            page.wait_for_timeout(4000)

            composer_loc = page.locator("div[role='button']").filter(
                has_text=re.compile(r"Exprimez-vous|Écrivez quelque chose|Ecrivez quelque chose|Quoi de neuf|Que voulez-vous|Write something|Créer une publication", re.I)
            ).first

            if composer_loc.count() == 0:
                logger.warning(f"Impossible de trouver le bouton de composition dans le groupe {group_url}")
                return False

            composer_loc.click(force=True)
            page.wait_for_timeout(2500)

            textbox = page.locator("div[role='textbox']").first
            if textbox.count() == 0:
                logger.warning(f"Impossible d'ouvrir le champ de saisie dans le groupe {group_url}")
                return False

            textbox.click(force=True)
            page.wait_for_timeout(500)
            textbox.fill(text)
            page.wait_for_timeout(2000)

            post_btn = page.locator(
                "div[aria-label='Publier'][role='button'], div[aria-label='Post'][role='button'], div[role='button']:has-text('Publier')"
            ).first

            if post_btn.count() == 0:
                logger.warning(f"Bouton de publication introuvable dans le groupe {group_url}")
                return False

            post_btn.click(force=True)
            page.wait_for_timeout(5000)
            context.storage_state(path=session_file)
            return True
        except Exception as e:
            logger.error(f"Erreur publication dans le groupe {group_url} : {e}")
            return False
        finally:
            browser.close()
