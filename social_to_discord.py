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
IG_MIN_INTERVAL = int(os.environ.get("IG_MIN_INTERVAL", "30"))  # menit; IG dicek jarang supaya akun aman

# Jenis sumber:  ("x", "username")  ("ig", "username")  ("rss", "https://url-feed")
# Username/URL di bawah adalah CONTOH. Yang bertanda "cek" harus dipastikan dulu.
CHANNELS = {
    "newsinfo": {
        "webhook_env": "WEBHOOK_BERITA",
        "sources": [
            ("rss", "https://feeds.bbci.co.uk/news/world/rss.xml"),
            ("rss", "https://www.aljazeera.com/xml/rss/all.xml"),
            ("rss", "https://www.antaranews.com/rss/terkini.xml"),  # cek
            ("rss", "https://www.cnnindonesia.com/nasional/rss"),  # cek
        ],
    },
    "techinfo": {
        "webhook_env": "WEBHOOK_TECH",
        "sources": [
            ("rss", "https://feeds.arstechnica.com/arstechnica/index"),
            ("rss", "https://www.theverge.com/rss/index.xml"),
            ("rss", "https://techcrunch.com/feed/"),
        ],
    },
    "footballinfo": {
        "webhook_env": "WEBHOOK_BOLA",
        "sources": [
            ("x", "FabrizioRomano"),
            ("x", "David_Ornstein"),
            ("rss", "https://feeds.bbci.co.uk/sport/football/rss.xml"),
            ("rss", "https://www.theguardian.com/football/rss"),
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
            ("rss", "https://www.eurogamer.net/feed"),
            ("rss", "https://www.gamespot.com/feeds/news/"),  # cek
            ("rss", "https://www.pcgamer.com/rss/"),  # cek
            ("rss", "https://dotesports.com/feed"),  # cek, esports
        ],
    },
    "mobilelegendsinfo": {
        "webhook_env": "WEBHOOK_MLBB",
        "sources": [
            ("x", "mplidofficial"),   # MPL Indonesia (resmi)
            ("x", "mlbbesports_en"),  # MLBB Esports global (resmi)
            ("x", "real_mlbbid"),     # MLBB Indonesia (cek masih aktif)
            ("ig", "mpl.id.official"),  # MPL Indonesia (cek: handle sama dengan FB/TikTok resminya)
            # YouTube resmi (lebih stabil dari X), ganti CHANNEL_ID:
            # ("rss", "https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID"),
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
            ("x", "PUBGMOBILE"),        # global (resmi)
            ("x", "pubgmesportsid"),    # PUBG Mobile Esports Indonesia (resmi)
            ("ig", "pubgmobile.esports.id"),  # IG resmi PUBG Mobile Esports Indonesia
            ("rss", "https://www.youtube.com/feeds/videos.xml?channel_id=UCkB_AwGXxPAKdahxGHpeC4Q"),  # YouTube PUBG MOBILE Indonesia
        ],
    },
    "freefireinfo": {
        "webhook_env": "WEBHOOK_FREEFIRE",
        "sources": [
            # Akun X Free Fire Indonesia hampir tidak aktif, jadi pakai Instagram resmi.
            ("ig", "freefirebgid"),
            # YouTube resmi Garena Free Fire Indonesia (opsional), isi CHANNEL_ID:
            # ("rss", "https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID"),
        ],
    },
    "valorantinfo": {
        "webhook_env": "WEBHOOK_VALORANT",
        "sources": [
            ("x", "PlayVALORANT"),
            ("x", "VALORANTEsports"),
            ("x", "vctpacific"),  # VCT Pacific (resmi, region Indonesia)
            ("ig", "vctpacific"),
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

            if kind == "ig":  # batasi frekuensi IG
                last = state.setdefault("_last", {})
                if time.time() - last.get(key, 0) < IG_MIN_INTERVAL * 60:
                    continue
                last[key] = time.time()

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
