#!/usr/bin/env python3
"""
Forward postingan X / IG / RSS ke BEBERAPA channel Discord (satu webhook per channel).

Install:   pip install feedparser requests
Jalankan:  python social_to_discord.py
Webhook diisi lewat environment variable (lihat CHANNELS di bawah), contoh:
  export WEBHOOK_BOLA="https://discord.com/api/webhooks/..."
"""

import json
import os
import time
from pathlib import Path

import feedparser
import requests

# ================= KONFIGURASI =================
RSSHUB = os.environ.get("RSSHUB_URL", "http://localhost:1200")
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "180"))

# Tiap channel: nama env var untuk webhook + daftar sumber.
# Jenis sumber:  ("x", "username")  ("ig", "username")  ("rss", "https://url-feed")
# Username/URL di bawah hanya CONTOH, cek dan ganti sesuai kebutuhan.
CHANNELS = {
    "info-bola": {
        "webhook_env": "WEBHOOK_BOLA",
        "sources": [
            ("x", "FabrizioRomano"),
        ],
    },
    "info-mlbb": {
        "webhook_env": "WEBHOOK_MLBB",
        "sources": [
            ("x", "MLBB_Official"),  # cek username resminya
        ],
    },
    "info-valorant": {
        "webhook_env": "WEBHOOK_VALORANT",
        "sources": [
            ("x", "PlayVALORANT"),
            ("x", "VALORANTEsports"),
        ],
    },
    "info-eafc": {
        "webhook_env": "WEBHOOK_EAFC",
        "sources": [
            ("x", "EASPORTSFC"),
        ],
    },
    "berita": {
        "webhook_env": "WEBHOOK_BERITA",
        "sources": [
            ("rss", "https://feeds.bbci.co.uk/sport/football/rss.xml"),
            # tambahkan RSS portal berita pilihan Anda di sini
        ],
    },
}

STATE_FILE = Path("seen.json")
# ===============================================


def source_to_url(kind, value):
    if kind == "x":
        return f"{RSSHUB}/twitter/user/{value}"
    if kind == "ig":
        return f"{RSSHUB}/instagram/user/{value}"
    return value  # rss


def embed_friendly(link):
    return (
        link.replace("https://twitter.com", "https://fxtwitter.com")
        .replace("https://x.com", "https://fxtwitter.com")
        .replace("https://www.instagram.com", "https://www.kkinstagram.com")
    )


def send(webhook, label, entry):
    link = embed_friendly(entry.link)
    # Link X/IG/YouTube di-embed otomatis oleh Discord; RSS berita ditambah judul
    if label.startswith(("x:", "ig:")):
        content = f"**{label}**\n{link}"
    else:
        content = f"**{entry.get('title', '')}**\n{link}"
    r = requests.post(webhook, json={"content": content[:1900]}, timeout=15)
    if r.status_code == 429:
        time.sleep(float(r.json().get("retry_after", 2)))
        return send(webhook, label, entry)
    r.raise_for_status()


def load_state():
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}


def check_all(state):
    for ch_name, ch in CHANNELS.items():
        webhook = os.environ.get(ch["webhook_env"], "")
        if not webhook:
            print(f"[skip] {ch_name}: env {ch['webhook_env']} belum diisi")
            continue

        for kind, value in ch["sources"]:
            label = f"{kind}:{value}" if kind != "rss" else "rss"
            key = f"{ch_name}|{kind}|{value}"
            url = source_to_url(kind, value)

            try:
                feed = feedparser.parse(url)
                if feed.bozo and not feed.entries:
                    print(f"[!] Gagal baca {key}")
                    continue
            except Exception as e:
                print(f"[!] Error {key}: {e}")
                continue

            is_new_source = key not in state  # sumber baru: tandai saja, jangan spam
            seen = set(state.get(key, []))
            fresh = [e for e in feed.entries if (e.get("id") or e.link) not in seen]

            for entry in reversed(fresh):
                uid = entry.get("id") or entry.link
                if not is_new_source:
                    try:
                        send(webhook, label, entry)
                        print(f"[+] #{ch_name} <- {label}: {entry.link}")
                        time.sleep(1)
                    except Exception as e:
                        print(f"[!] Gagal kirim {key}: {e}")
                        continue
                seen.add(uid)

            state[key] = list(seen)[-200:]
    STATE_FILE.write_text(json.dumps(state))


def main():
    state = load_state()
    if os.environ.get("RUN_ONCE") == "1":  # mode GitHub Actions: cek sekali lalu selesai
        check_all(state)
        return
    while True:
        check_all(state)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
