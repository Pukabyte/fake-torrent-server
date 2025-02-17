from fastapi import FastAPI, Response, HTTPException
import uvicorn
import bencodepy
import hashlib
from datetime import datetime
from loguru import logger
import logging
import os
from settings import settings
import sys

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Remove default logger
logger.remove()

# Suppress uvicorn logs
logging.getLogger("uvicorn.access").handlers = []
logging.getLogger("uvicorn.error").handlers = []

# Custom log levels
logger.level("REQUEST", no=15, color="<cyan>", icon="📥")
logger.level("GENERATE", no=15, color="<yellow>", icon="🔄")

# Log format with emojis
LOG_FORMAT = "<level>{level: <8}</level> | {extra[emoji]} {message}"

# Console logger
logger.add(
    sys.stderr,
    format=LOG_FORMAT,
    level=settings.LOG_LEVEL,
    colorize=True,
    enqueue=True
)

# File logger
logger.add(
    "logs/server.log",
    format="{level: <8} | {message}",
    level=settings.LOG_LEVEL,
    rotation="500 MB",
    retention="10 days",
    enqueue=True
)

app = FastAPI()
def log_with_emoji(level: str, message: str, emoji: str):
    logger.bind(emoji=emoji).log(level, message)

def log_request(file_name: str, file_type: str):
    log_with_emoji("REQUEST", f"New request: {file_name}.{file_type}", "📥")

def log_generate(name: str):
    log_with_emoji("GENERATE", f"Generating: {name}", "🔄")

app = FastAPI()

@app.get("/{file_name}.{file_type}")
async def get_file(file_name: str, file_type: str):
    log_request(file_name, file_type)
    
    if file_type.lower() not in ["torrent", "nzb"]:
        logger.warning(f"Invalid file type: {file_type}")
        raise HTTPException(status_code=400, detail="Unsupported file type")
    
    try:
        if file_type.lower() == "torrent":
            return generate_torrent(file_name)
        else:
            return generate_nzb(file_name)
            
    except Exception as e:
        logger.error(f"Error generating file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating file: {str(e)}")

def generate_torrent(torrent_name: str):
    log_generate(torrent_name)
    
    infohash = "41e6cd50ccec55cd5704c5e3d176e7b59317a3fb"
    piece_length = 262144  # 256 KB per piece
    fake_file_size = 1073741824  # 1 GB
    num_pieces = (fake_file_size + piece_length - 1) // piece_length
    
    # Generate pieces using infohash as seed
    all_pieces = b''.join([hashlib.sha1(infohash.encode() + str(i).encode()).digest() for i in range(num_pieces)])
    
    torrent_data = {
        b"announce": b"udp://tracker.opentrackr.org:1337/announce",
        b"announce-list": [[b"udp://tracker.opentrackr.org:1337/announce"]],
        b"comment": b"Created by Simple Torrent Server",
        b"created by": b"Simple Torrent Server",
        b"creation date": int(datetime.now().timestamp()),
        b"info": {
            b"name": torrent_name.encode(),
            b"piece length": piece_length,
            b"pieces": all_pieces,
            b"private": 1,
            b"length": fake_file_size
        }
    }

    torrent_content = bencodepy.encode(torrent_data)

    headers = {
        "Content-Type": "application/x-bittorrent",
        "Content-Disposition": f'attachment; filename="{torrent_name}.torrent"'
    }

    return Response(
        content=torrent_content,
        headers=headers,
        media_type="application/x-bittorrent"
    )

def generate_nzb(file_name: str):
    current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    nzb_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nzb PUBLIC "-//newzBin//DTD NZB 1.1//EN" "http://www.newzbin.com/DTD/nzb/nzb-1.1.dtd">
<nzb xmlns="http://www.newzbin.com/DTD/2003/nzb">
    <head>
        <meta type="title">{file_name}</meta>
        <meta type="date">{current_time}</meta>
    </head>
    <file poster="anonymous@example.com" date="1234567890" subject="{file_name} (1/1)">
        <groups>
            <group>alt.binaries.test</group>
        </groups>
        <segments>
            <segment bytes="512000" number="1">fake-segment-id-1</segment>
            <segment bytes="512000" number="2">fake-segment-id-2</segment>
        </segments>
    </file>
</nzb>"""

    headers = {
        "Content-Type": "application/x-nzb",
        "Content-Disposition": f'attachment; filename="{file_name}.nzb"'
    }

    return Response(
        content=nzb_content,
        headers=headers,
        media_type="application/x-nzb"
    )

if __name__ == "__main__":
    logger.info("🚀 Starting Simple Torrent Server")
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8000,
        log_config=None,
        log_level="critical",
    )
    server = uvicorn.Server(config)
    logger.info("🌐 Server running on http://0.0.0.0:8000")
    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("👋 Shutting down server")
