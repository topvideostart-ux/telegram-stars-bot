import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "8580771359:AAH_OjbUC10J59htA43yt5DH2qS3c3Kf7F8")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_ID", "5495453929").split(",")]
