import random
import logging
from config import MAX_FACEBOOK_ACTIONS_PER_DAY, DRY_RUN
from database import (
    record_action, get_action_count_today, has_acted_on,
    add_facebook_group, get_available_facebook_groups,
    mark_facebook_group_posted, count_facebook_groups
)
from content_engine import generate_facebook_post
from browser_manager import (
    has_valid_session, post_facebook_browser,
    search_and_discover_facebook_groups, post_facebook_group_browser
)

logger = logging.getLogger("CTRLX.Social.Facebook")

FRENCH_TECH_SEARCH_QUERIES = [
    "développeurs web france",
    "entraide informatique france",
    "développeurs python france",
    "communauté tech france",
    "freelance tech france",
    "react javascript développeurs france",
    "side projects développeurs france"
]

class FacebookBot:
    def __init__(self):
        pass

    def is_configured(self) -> bool:
        return has_valid_session("facebook")

    def discover_groups(self, limit_per_query: int = 4) -> int:
        if DRY_RUN or not self.is_configured():
            logger.info("[SIMULATION] Découverte de groupes Facebook français")
            simulated_groups = [
                ("101928374", "Développeurs Web France", "https://www.facebook.com/groups/101928374/"),
                ("203948576", "Entraide Informatique & Dév", "https://www.facebook.com/groups/203948576/"),
                ("304958677", "Python & Freelance France", "https://www.facebook.com/groups/304958677/")
            ]
            added = 0
            for gid, name, url in simulated_groups:
                if add_facebook_group(gid, name, url):
                    added += 1
            return added

        query = random.choice(FRENCH_TECH_SEARCH_QUERIES)
        logger.info(f"Recherche de groupes Facebook français avec la requête : '{query}'...")
        groups = search_and_discover_facebook_groups(query, limit=limit_per_query)
        added_count = 0
        for g in groups:
            if add_facebook_group(g["group_id"], g["group_name"], g["group_url"]):
                logger.info(f"Nouveau groupe découvert : {g['group_name']} ({g['group_url']})")
                added_count += 1
        return added_count

    def publish_original_post(self) -> bool:
        daily_actions = get_action_count_today("facebook")
        if daily_actions >= MAX_FACEBOOK_ACTIONS_PER_DAY:
            logger.info(f"Limite quotidienne Facebook atteinte ({daily_actions}/{MAX_FACEBOOK_ACTIONS_PER_DAY})")
            return False

        content = generate_facebook_post()

        if DRY_RUN or not self.is_configured():
            logger.info(f"[DRY RUN] Publication simulée sur le profil Facebook :\n{content}")
            record_action(
                platform="facebook",
                action_type="original_post",
                target_id="self",
                target_url="https://facebook.com",
                content=content,
                status="simulated"
            )
            return True

        success = post_facebook_browser(content)
        status = "success" if success else "failed"

        record_action(
            platform="facebook",
            action_type="original_post",
            target_id="self",
            target_url="https://facebook.com",
            content=content,
            status=status
        )
        return success

    def publish_group_post(self) -> bool:
        daily_actions = get_action_count_today("facebook")
        if daily_actions >= MAX_FACEBOOK_ACTIONS_PER_DAY:
            return False

        available_groups = get_available_facebook_groups(limit=5)
        if not available_groups:
            self.discover_groups()
            available_groups = get_available_facebook_groups(limit=5)

        if not available_groups:
            logger.info("Aucun groupe Facebook disponible pour publication.")
            return False

        target_group = random.choice(available_groups)
        gid = target_group["group_id"]
        gname = target_group["group_name"]
        gurl = target_group["group_url"]

        content = generate_facebook_post()

        if DRY_RUN or not self.is_configured():
            logger.info(f"[DRY RUN] Publication simulée dans le groupe {gname} ({gurl}) :\n{content}")
            record_action(
                platform="facebook",
                action_type="group_post",
                target_id=gid,
                target_url=gurl,
                content=content,
                status="simulated"
            )
            mark_facebook_group_posted(gid)
            return True

        logger.info(f"Publication dans le groupe {gname} ({gurl})...")
        success = post_facebook_group_browser(gurl, content)
        status = "success" if success else "failed"

        record_action(
            platform="facebook",
            action_type="group_post",
            target_id=gid,
            target_url=gurl,
            content=content,
            status=status
        )
        if success:
            mark_facebook_group_posted(gid)
        return success

    def scan_and_post_cycle(self) -> int:
        daily_actions = get_action_count_today("facebook")
        if daily_actions >= MAX_FACEBOOK_ACTIONS_PER_DAY:
            return 0

        if count_facebook_groups() < 5 or random.random() < 0.2:
            self.discover_groups()

        decision = random.choice(["profile", "group"])
        if decision == "group" and count_facebook_groups() > 0:
            success = self.publish_group_post()
        else:
            success = self.publish_original_post()

        return 1 if success else 0
