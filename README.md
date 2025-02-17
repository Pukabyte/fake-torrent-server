# Simple Torrent Server

A FastAPI server that generates .torrent files with a predefined infohash. Designed for use with DebriDav's Easynews Implementation.

## Features

- Generates .torrent files with a consistent infohash
- Simple and lightweight implementation
- Detailed logging with emoji indicators
- Docker support

## Installation

1. Clone the repository:

```bash
git clone https://github.com/pukabyte/fake-torrent-server.git
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

4. Edit the `.env` file (optional):

```bash
# Application Settings
LOG_LEVEL=INFO
```

## Usage

### Python

```bash
python server.py
```

### Docker

```bash
docker compose up -d
```

The server will listen on `http://0.0.0.0:8000`

### Request a torrent file:

```bash
GET /{filename}.torrent
```

Example:
```bash
http://localhost:8000/Movie.Title.2024.2160p.BluRay.x265-GROUP.torrent
```

## Configuration

- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `INFOHASH`: Infohash to use for generated torrents (40 character hex string)

## Logging

The server uses custom log levels with emoji indicators:
- 📥 REQUEST: New file requests
- 🔄 GENERATE: File generation
- 📄 INFO: General information
- ⚠️ WARNING: Warnings
- ❌ ERROR: Errors
- 🚨 CRITICAL: Critical errors

Logs are written to both console and `logs/server.log` with automatic rotation.