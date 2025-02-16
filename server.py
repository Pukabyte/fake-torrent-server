from fastapi import FastAPI, Response, HTTPException
import uvicorn
import bencodepy
import hashlib
import os
import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import quote
from typing import Optional, Dict, Any
from settings import settings
from loguru import logger
from difflib import SequenceMatcher
import logging

# Suppress uvicorn access logs
logging.getLogger("uvicorn.access").handlers = []
logging.getLogger("uvicorn.error").handlers = []

# Configure logger
logger.remove()  # Remove default handler

# After logger.remove() and before the LOG_FORMAT definition, add:
logger.level("REQUEST", no=15, color="<cyan>")
logger.level("SEARCH", no=15, color="<blue>")
logger.level("MATCH", no=25, color="<green>")
logger.level("GENERATE", no=15, color="<yellow>")

LOG_FORMAT = "{level: <8} | {message}"

# File logger
logger.add(
    "logs/server.log",
    rotation="500 MB",
    retention="10 days",
    level=settings.LOG_LEVEL,
    format=LOG_FORMAT
)

# Console logger with emojis
EMOJI_LOG_FORMAT = (
    "<level>{level: <8}</level> | "
    "{message}"
)

LEVEL_EMOJIS = {
    "INFO": "📄 ",
    "WARNING": "⚠️ ",
    "ERROR": "❌ ",
    "DEBUG": "🕷️ ",
    "CRITICAL": "🚨 ",
    "SEARCH": "🔍 ",
    "MATCH": "✅ ",
    "GENERATE": "🔄 ",
    "REQUEST": "📥 "
}

def emoji_format(record):
    record["message"] = f"{LEVEL_EMOJIS.get(record['level'].name, '')} {record['message']}"
    return EMOJI_LOG_FORMAT

logger.add(
    lambda msg: print(msg, flush=True),
    level=settings.LOG_LEVEL,
    format=emoji_format
)

app = FastAPI()

def log_request(file_name: str, file_type: str):
    logger.log("REQUEST", f"New request: {file_name}.{file_type}")

def log_search(title: str, year: str = ""):
    message = title
    if year:
        message += f" ({year})"
    logger.log("SEARCH", f"Searching: {message}")

def log_match(title: str):
    logger.log("MATCH", f"Match found: {title}")

def log_generate(name: str):
    logger.log("GENERATE", f"Generating: {name}")

def normalize_title(title: str) -> str:
    # Remove common words and characters that might differ between releases
    title = title.lower()
    title = re.sub(r'[.\-_–]', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    return title.strip()

def is_tv_show(title: str) -> bool:
    return bool(re.search(r"(?i)\b([Ss]?\d+[xXeE]\d+)\b", title))

def parse_media_info(file_name: str) -> Dict[str, Any]:
    base_url = settings.SONARR_URL if is_tv_show(file_name) else settings.RADARR_URL
    api_key = settings.SONARR_API_KEY if is_tv_show(file_name) else settings.RADARR_API_KEY
    
    response = requests.get(
        f"{base_url}/api/v3/parse",
        params={"title": file_name, "apikey": api_key}
    )
    response.raise_for_status()
    return response.json()

def similarity_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

def get_resolution(parsed_info: Dict[str, Any]) -> Optional[str]:
    if "parsedMovieInfo" in parsed_info:
        quality = parsed_info["parsedMovieInfo"].get("quality", {}).get("quality", {})
        resolution = quality.get("resolution")
        if resolution:
            return f"{resolution}p"
    elif "parsedEpisodeInfo" in parsed_info:
        quality = parsed_info["parsedEpisodeInfo"].get("quality", {}).get("quality", {})
        resolution = quality.get("resolution")
        if resolution:
            return f"{resolution}p"
    return None

def search_zilean(parsed_info: Dict[str, Any]) -> Optional[str]:
    if "parsedMovieInfo" in parsed_info:
        title = parsed_info["parsedMovieInfo"]["movieTitle"]
        year = parsed_info["parsedMovieInfo"]["year"]
        resolution = get_resolution(parsed_info)
        
        search_url = f"{settings.ZILEAN_URL}/dmm/filtered?query={quote(title)}&year={year}"
        if resolution:
            search_url += f"&resolution={resolution}"
            
        log_search(title, str(year))
    else:
        # TV show search
        parsed_ep = parsed_info.get("parsedEpisodeInfo", {})
        title = parsed_ep.get("seriesTitle", "")
        season = parsed_ep.get("seasonNumber")
        episodes = parsed_ep.get("episodeNumbers", [])
        resolution = get_resolution(parsed_info)
        
        if not title or season is None:
            logger.warning("Invalid TV show parse result")
            return None
            
        search_url = f"{settings.ZILEAN_URL}/dmm/filtered?query={quote(title)}&season={season}"
        if episodes:
            search_url += f"&episode={episodes[0]}"
        if resolution:
            search_url += f"&resolution={resolution}"
            
        log_search(f"{title} S{season:02d}" + (f"E{episodes[0]:02d}" if episodes else ""))
    
    try:
        response = requests.get(search_url)
        response.raise_for_status()
        
        results = response.json()
        if not results:
            logger.warning("No results found, using fallback infohash")
            return "magnet:?xt=urn:btih:91426fbc17ad836b5a3525aeccbd3360097aeb24"
            
        file_name_normalized = normalize_title(parsed_info["title"])
        best_match = None
        best_ratio = 0.0
        
        logger.debug(f"Looking for match: {file_name_normalized}")
        
        for result in results:
            raw_title = result.get("raw_title")
            info_hash = result.get("info_hash")
            
            if raw_title and info_hash:
                ratio = similarity_ratio(file_name_normalized, normalize_title(raw_title))
                
                logger.debug(f"Comparing with: {raw_title}")
                logger.debug(f"Normalized: {normalize_title(raw_title)}")
                logger.debug(f"Match ratio: {ratio:.2%}")
                
                if ratio > best_ratio:
                    best_ratio = ratio
                    magnet_link = f"magnet:?xt=urn:btih:{info_hash}"
                    best_match = (magnet_link, raw_title)
                    logger.debug(f"New best match: {raw_title} ({ratio:.2%})")
        
        if best_ratio >= settings.MATCH_THRESHOLD:
            logger.info(f"Using best match: {best_match[1]} ({best_ratio:.2%}) [threshold: {settings.MATCH_THRESHOLD:.2%}]")
            return best_match[0]
        else:
            logger.warning("No good matches found, using fallback infohash")
            return "magnet:?xt=urn:btih:91426fbc17ad836b5a3525aeccbd3360097aeb24"
            
    except requests.RequestException as e:
        logger.error(f"Zilean search error: {str(e)}")
        raise

@app.get("/{file_name}.{file_type}")
async def get_file(file_name: str, file_type: str):
    log_request(file_name, file_type)
    
    if file_type.lower() not in ["torrent", "nzb"]:
        logger.warning(f"Invalid file type: {file_type}")
        raise HTTPException(status_code=400, detail="Unsupported file type")
    
    try:
        parsed_name = file_name.replace(".", " ")
        logger.debug(f"Parsed: {parsed_name}")
        
        parsed_info = parse_media_info(parsed_name)
        
        magnet_link = search_zilean(parsed_info)
        if magnet_link:
            if file_type.lower() == "torrent":
                return generate_torrent(file_name, magnet_link)
            else:
                return generate_nzb(file_name)
        else:
            logger.warning(f"No match found: {file_name}")
            raise HTTPException(status_code=404, detail="No matching release found")
            
    except requests.RequestException as e:
        logger.error(f"External service error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error communicating with external services: {str(e)}")

def generate_torrent(torrent_name: str, magnet_link: str):
    log_generate(torrent_name)
    logger.debug(f"Using magnet link: {magnet_link[:60]}...")
    
    # Extract infohash from magnet link
    infohash_match = re.search(r"btih:([a-fA-F0-9]{40})", magnet_link)
    if not infohash_match:
        raise HTTPException(status_code=400, detail="Invalid magnet link format")
    
    infohash = infohash_match.group(1)
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
    # Configure uvicorn logging
    import logging.config
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": True,
        "loggers": {
            "uvicorn": {"handlers": [], "level": "WARNING"},
            "uvicorn.error": {"handlers": [], "propagate": False},
            "uvicorn.access": {"handlers": [], "propagate": False},
        },
    })

    logger.info("🚀 Starting Fake Torrent Server")
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8000,
        log_config=None,
        log_level="critical",  # Suppress all uvicorn logs
    )
    server = uvicorn.Server(config)
    logger.info("🌐 Server running on http://0.0.0.0:8000")
    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("👋 Shutting down server")
