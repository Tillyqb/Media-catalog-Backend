# Media Catalog Backend

A Python backend service for managing and cataloging media files.

## Getting Started

### Prerequisites
- Python 3.8+
- A running MySQL server (8.0+)

### Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create your local environment file:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and set your real credentials and `OMDB_API_KEY`.

### Running the Application

```bash
python main.py
```

At startup, the application will:
- connect to MySQL,
- create the configured database if it does not exist,
- create a `media_items` table if it does not exist,
- verify OMDb API key configuration.

### Frontend Movie Search API

Endpoint:
- `GET /movies/search?title=<movie-title>&page=1`
- `GET /movies/by-imdb/<imdb-id>`

Behavior:
- Receives the movie title from the frontend.
- Calls OMDb search by title.
- Fetches detailed fields per result by IMDb id.
- Returns a list of detailed movie objects.

Example request:

```bash
curl "http://localhost:8000/movies/search?title=batman&page=1"
```

Example response shape:

```json
{
   "query": "batman",
   "count": 10,
   "results": [
      {
         "Title": "Batman Begins",
         "Year": "2005",
         "Rated": "PG-13",
         "Released": "15 Jun 2005",
         "Runtime": "140 min",
         "Genre": "Action, Crime, Drama",
         "Director": "Christopher Nolan",
         "Actors": "Christian Bale, Michael Caine, Ken Watanabe",
         "Plot": "After training with his mentor...",
         "Poster": "https://...",
         "imdbRating": "8.2",
         "imdbID": "tt0372784"
      }
   ]
}
```

Example IMDb lookup request:

```bash
curl "http://localhost:8000/movies/by-imdb/tt0372784"
```

### Media Catalog CRUD API (Flask)

Endpoints:
- `GET /media-items?limit=100&offset=0&media_type=image`
- `GET /media-items/<id>`
- `POST /media-items`
- `PUT /media-items/<id>` (or `PATCH /media-items/<id>`)
- `DELETE /media-items/<id>`

Example create request:

```bash
curl -X POST "http://localhost:8000/media-items" \
   -H "Content-Type: application/json" \
   -d '{
      "title": "Batman Begins",
      "file_path": "/mnt/media/movies/batman-begins.mp4",
      "media_type": "movie"
   }'
```

## Data Access Layer

The project now includes a MySQL repository in `access_layer.py`:
- `initialize_schema()`
- `create_media_item(title, file_path, media_type=None)`
- `get_media_item(item_id)`
- `list_media_items(limit=100, offset=0, media_type=None)`
- `update_media_item(item_id, title=None, file_path=None, media_type=None)`
- `delete_media_item(item_id)`

Example usage:

```python
from access_layer import DatabaseConfig, MySQLMediaAccessLayer

cfg = DatabaseConfig.from_env()
repo = MySQLMediaAccessLayer(cfg)
repo.initialize_schema()

new_id = repo.create_media_item(
   title="Summer Trip",
   file_path="/mnt/media/photos/summer-trip.jpg",
   media_type="image",
)

item = repo.get_media_item(new_id)
items = repo.list_media_items(limit=20)
repo.update_media_item(new_id, title="Summer Trip 2026")
repo.delete_media_item(new_id)
```

## Raspberry Pi Deployment

This backend is suitable for Raspberry Pi (Linux ARM). The steps below assume Raspberry Pi OS Bookworm.

### 1. System packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip mysql-server
sudo systemctl enable mysql
sudo systemctl start mysql
```

Create database user and grant privileges:

```bash
sudo mysql -e "CREATE USER IF NOT EXISTS 'media_user'@'localhost' IDENTIFIED BY 'change_me';"
sudo mysql -e "GRANT ALL PRIVILEGES ON media_catalog.* TO 'media_user'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"
```

### 2. Clone and install

```bash
git clone <your-repo-url>
cd media-catalog-backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Run manually for validation

```bash
python main.py
```

### 4. Run as a service (recommended)

Create `/etc/systemd/system/media-catalog-backend.service`:

```ini
[Unit]
Description=Media Catalog Backend
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/media-catalog-backend
ExecStart=/home/pi/media-catalog-backend/.venv/bin/python /home/pi/media-catalog-backend/main.py
Environment=DB_HOST=127.0.0.1
Environment=DB_PORT=3306
Environment=DB_USER=media_user
Environment=DB_PASSWORD=change_me
Environment=DB_NAME=media_catalog
Environment=OMDB_API_KEY=your_omdb_api_key_here
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable media-catalog-backend
sudo systemctl start media-catalog-backend
sudo systemctl status media-catalog-backend
```

View logs:

```bash
journalctl -u media-catalog-backend -f
```

### Raspberry Pi operational notes

- Prefer lightweight dependencies and avoid x86-only wheels.
- MySQL credentials should be changed from defaults before production use.
- Use a powered SSD or high-quality SD card for reliability.
- Keep swap enabled if you build native Python packages on-device.

## Project Structure

```
media-catalog-backend/
├── main.py              # Application entry point
├── requirements.txt     # Python dependencies
├── README.md           # This file
└── .gitignore          # Git ignore rules
```

## Contributing

Add your code and update dependencies as needed.
