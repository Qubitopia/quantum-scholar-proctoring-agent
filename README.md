# Quantum Scholar Proctoring Agent

A lightweight PySide6 desktop client for a proctored exam flow:

- Login with email and birthdate
- View available tests
- Read instructions in fullscreen, then start the test

## Requirements

- Python 3.12+
- Windows/macOS/Linux

## Setup

```pwsh
py -3.12 -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Optionally configure the backend base URL:

```pwsh
$env:QS_API_BASE_URL = "http://localhost:8000"
```

## Run

```pwsh
python main.py
```

## Configuration

Set `QS_API_BASE_URL` to point to your API server. Endpoints are defined in `config.py`.

## Notes

- Access token is written to `~/.quantum_scholar_token`.
- App icon and logo assets are under `assets/`.
