# Fake Torrent Server

A FastAPI server that generates fake .torrent files based on media information from Radarr/Sonarr and Zilean for use with DebriDav's Easynews Implementation.

## Features

- Parses media filenames using Radarr/Sonarr APIs
- Searches for matching releases using Zilean's filtered API
- Generates fake .torrent files with real infohashes
- Supports both movies and TV shows
- Configurable match threshold for title comparison
- Detailed logging with customizable log levels

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/fake-torrent-server.git
cd fake-torrent-server
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```
3. Create a `.env` file:

```bash
cp .env.example .env
```

4. Edit the `.env` file with your Radarr/Sonarr API keys and Zilean URL:

```bash
env
RADARR_URL=http://radarr:7878
SONARR_URL=http://sonarr:8989
RADARR_API_KEY=your_radarr_api_key
SONARR_API_KEY=your_sonarr_api_key
ZILEAN_URL=http://zilean:8181/
MATCH_THRESHOLD=0.8
LOG_LEVEL=INFO
```

## Usage
1. Run the server:

### python

```bash
python server.py
```

### docker

```bash
docker compose up -d
```
2. The server will listen on `http://0.0.0.0:8000`

3. Request a torrent file:

```bash
GET /{filename}.torrent
```

Example:

```bash
http://localhost:8000/Movie.Title.2024.2160p.BluRay.x265-GROUP.torrent
```

## Configuration

- `RADARR_URL`: URL of your Radarr instance
- `SONARR_URL`: URL of your Sonarr instance
- `RADARR_API_KEY`: Your Radarr API key
- `SONARR_API_KEY`: Your Sonarr API key
- `ZILEAN_URL`: Base URL for Zilean API
- `MATCH_THRESHOLD`: Minimum similarity ratio for title matching (0.0-1.0)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Logging

The server uses custom log levels with emoji indicators:
- 📥 REQUEST: New file requests
- 🔍 SEARCH: Search operations
- ✅ MATCH: Successful matches
- 🔄 GENERATE: File generation
- 🕷️ DEBUG: Debug information
- 📄 INFO: General information
- ⚠️ WARNING: Warnings
- ❌ ERROR: Errors
- 🚨 CRITICAL: Critical errors

Logs are written to both console and `logs/server.log` with automatic rotation.