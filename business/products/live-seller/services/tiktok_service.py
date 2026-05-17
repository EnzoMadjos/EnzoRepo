import asyncio
import logging

log = logging.getLogger("tiktok")

try:
    from TikTokLive import TikTokLiveClient
    from TikTokLive.events import ConnectEvent, CommentEvent, DisconnectEvent
    HAS_TIKTOK = True
except ImportError:
    HAS_TIKTOK = False
    log.error("TikTokLive not installed — run: pip install TikTokLive")

try:
    from TikTokLive.events import RoomPinEvent
    HAS_PIN_EVENT = True
except ImportError:
    HAS_PIN_EVENT = False
    log.warning("RoomPinEvent not available — pin auto-capture disabled, use Mine! button as fallback")


async def create_tiktok_task(unique_id: str, manager) -> "tuple | None":
    """Connect to a TikTok live and return (task, client). Returns None if library missing."""
    if not HAS_TIKTOK:
        return None

    uid = unique_id.lstrip("@")
    client = TikTokLiveClient(unique_id=f"@{uid}")

    @client.on(ConnectEvent)
    async def on_connect(event: ConnectEvent):
        log.info("Connected to @%s", uid)
        await manager.broadcast("tiktok_connected", {"username": uid})

    @client.on(CommentEvent)
    async def on_comment(event: CommentEvent):
        await manager.broadcast("comment", {
            "tiktok_uid": str(event.user.id),
            "display_name": event.user.nickname,
            "handle": event.user.unique_id,
            "text": event.comment,
        })

    @client.on(DisconnectEvent)
    async def on_disconnect(event: DisconnectEvent):
        log.info("Disconnected from @%s", uid)
        await manager.broadcast("tiktok_disconnected", {"username": uid})

    if HAS_PIN_EVENT:
        @client.on(RoomPinEvent)
        async def on_pin(event: RoomPinEvent):
            """Fires when host pins a comment. Extract the pinned user's info and broadcast."""
            try:
                # TikTokLive proto event — try multiple field names defensively
                msg = (
                    getattr(event, "comment", None)
                    or getattr(event, "chat_message", None)
                    or getattr(event, "message", None)
                )
                if msg is None:
                    log.warning("RoomPinEvent: could not extract pinned message (no comment/message field)")
                    return
                user = getattr(msg, "user", None)
                if user is None:
                    return
                text = getattr(msg, "comment", None) or getattr(msg, "text", "")
                await manager.broadcast("pin", {
                    "tiktok_uid": str(user.id),
                    "display_name": user.nickname,
                    "handle": user.unique_id,
                    "text": text,
                })
            except Exception as e:
                log.warning("Pin event parse failed: %s", e)

    task = asyncio.create_task(client.start(), name="tiktok_client")
    return task, client
