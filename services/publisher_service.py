import asyncio
import logging
from typing import Optional, Dict, Any
import discord

logger = logging.getLogger("CTRLX.PublisherService")

class PublisherService:
    def __init__(self):
        self.queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self.worker_task: Optional[asyncio.Task] = None
        self.bot: Optional[discord.Client] = None
        self.running: bool = False

    def start_worker(self, bot: discord.Client):
        if not self.running:
            self.bot = bot
            self.running = True
            self.worker_task = asyncio.create_task(self._worker())
            logger.info("PublisherService queue worker started.")

    async def stop_worker(self):
        self.running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            self.worker_task = None
            logger.info("PublisherService queue worker stopped.")

    async def enqueue(self, channel_id: int, content: str = "", embed: Optional[discord.Embed] = None, view: Optional[discord.ui.View] = None):
        await self.queue.put({
            "channel_id": channel_id,
            "content": content,
            "embed": embed,
            "view": view
        })

    async def _worker(self):
        while self.running:
            try:
                item = await self.queue.get()
                channel_id = item.get("channel_id")
                content = item.get("content")
                embed = item.get("embed")
                view = item.get("view")

                if self.bot and channel_id:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        kwargs = {}
                        if content:
                            kwargs["content"] = content
                        if embed:
                            kwargs["embed"] = embed
                        if view:
                            kwargs["view"] = view
                        await channel.send(**kwargs)
                        await asyncio.sleep(1.0)
                    else:
                        logger.warning(f"Target channel {channel_id} not found in publisher worker.")

                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error publishing queued item: {e}")
                await asyncio.sleep(2.0)

publisher = PublisherService()
