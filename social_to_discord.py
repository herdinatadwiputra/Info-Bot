#!/usr/bin/env python3
"""
Forward postingan X / IG / RSS ke BANYAK channel Discord (satu webhook per channel).
Mode GitHub Actions: RUN_ONCE=1 (cek sekali lalu selesai).
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
MAX_PER_SOURCE = int(os.environ.get("MAX_PER_SOURCE", "5"))  # cegah banjir per cek

# Jenis sumber:  ("x", "username")  ("ig", "username")  ("rss", "https://url-feed")
# Username/URL di bawah adalah CONTOH. Yang bertanda "cek" harus dipastikan dulu.
CHANNELS = {
    "newsinfo": {
        "webhook_env": "WEBHOOK_BERITA",
        "sources": [
            ("rss", "https://feeds.bbci.co.uk/news/world/rss.xml"),
            ("rss", "https://www.antaranews.com/rss/terkini.xml"),  # cek
        ],
    },
    "techinfo": {
        "webhook_env": "WEBHOOK_TECH",
        "sources": [
            ("rss", "https://www.theverge.com/rss/index.xml"),
            ("rss", "https://rss.detik.com/index.php/inet"),  # cek
        ],
    },
    "footballinfo": {
        "webhook_env": "WEBHOOK_BOLA",
        "sources": [
            ("x", "FabrizioRomano"),
            ("rss", "https://feeds.bbci.co.uk/sport/football/rss.xml"),
        ],
    },
    "animeinfo": {
        "webhook_env": "WEBHOOK_ANIME",
        "sources": [
            ("rss", "https://www.animenewsnetwork.com/all/rss.xml"),  # cek
        ],
    },
    "gameinfo": {
        "webhook_env": "WEBHOOK_GAME",
        "sources": [
            ("rss", "https://www.pcgamer.com/rss/"),  # cek
            ("rss", "https://www.gamespot.com/feeds/news/"),  # cek
        ],
    },
    "mobilelegendsinfo": {
        "webhook_env": "WEBHOOK_MLBB",
        "sources": [
            ("x", "MLBB_Official"),  # cek username resminya
        ],
    },
    "eafcinfo": {
        "webhook_env": "WEBHOOK_EAFC",
        "sources": [
            ("x", "EASPORTSFC"),
        ],
    },
    "pubgminfo": {
        "webhook_env": "WEBHOOK_PUBGM",
        "sources": [
            ("x", "PUBGMOBILE"),
        ],
    },
    "freefireinfo": {
        "webhook_env": "WEBHOOK_FREEFIRE",
        "sources": [
            ("x", "freefire_ID"),  # cek username resminya
        ],
    },
    "valorantinfo": {
        "webhook_env": "WEBHOOK_VALORANT",
        "sources": [
            ("x", "PlayVALORANT"),
            ("x", "VALORANTEsports"),
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
    return value


def embed_friendly(link):
    return (
        link.replace("https://twitter.com", "https://fxtwitter.com")
        .replace("https://x.com", "https://fxtwitter.com")
        .replace("https://www.instagram.com", "https://www.kkinstagram.com")
    )


def send(webhook, label, entry):
    link = embed_friendly(entry.link)
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
            print(f"[skip] {ch_name}: secret {ch['webhook_env']} belum diisi")
            continue

        for kind, value in ch["sources"]:
            label = f"{kind}:{value}" if kind != "rss" else "rss"
            key = f"{ch_name}|{kind}|{value}"

            try:
                feed = feedparser.parse(source_to_url(kind, value))
                if feed.bozo and not feed.entries:
                    print(f"[!] Gagal baca {key}")
                    continue
            except Exception as e:
                print(f"[!] Error {key}: {e}")
                continue

            is_new_source = key not in state  # sumber baru: tandai saja, jangan spam
            seen = set(state.get(key, []))
            fresh = [e for e in feed.entries if (e.get("id") or e.link) not in seen]

            to_send = [] if is_new_source else fresh[:MAX_PER_SOURCE]
            for entry in fresh:  # semua yang baru ditandai sudah dilihat
                seen.add(entry.get("id") or entry.link)

            for entry in reversed(to_send):  # kirim dari yang terlama
                try:
                    send(webhook, label, entry)
                    print(f"[+] #{ch_name} <- {label}: {entry.link}")
                    time.sleep(1)
                except Exception as e:
                    print(f"[!] Gagal kirim {key}: {e}")

            state[key] = list(seen)[-200:]
    STATE_FILE.write_text(json.dumps(state))


def main():
    state = load_state()
    if os.environ.get("RUN_ONCE") == "1":
        check_all(state)
        return
    while True:
        check_all(state)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
