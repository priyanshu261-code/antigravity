# ⚡ ShareBox — Local Campus & Hostel Wi-Fi Hub

> **Zero Apps • Zero Internet • Zero Data Consumption • 100% High-Speed Local Wi-Fi Sharing**

**ShareBox** turns any laptop or computer into a local, offline file-sharing server and media streaming hub. Designed specifically for college dorms, hostel rooms, study groups, and hackathons, anyone connected to the same Wi-Fi or mobile hotspot can scan a terminal QR code and immediately upload files, stream movies/audio, read PDFs/notes, and download files at full Wi-Fi speeds (up to 300+ Mbps) without downloading any apps or using mobile data.

---

## 🌟 Key Features

| Feature | Description |
| :--- | :--- |
| 📲 **Terminal Scannable QR Code** | On startup, ShareBox detects your local IP and prints a high-contrast scannable QR code directly in the terminal for fast phone camera scanning. |
| 🌐 **Zero App / Zero Internet** | Works entirely within any browser (Chrome, Safari, Firefox, Edge, Brave). No client software installation or internet required. |
| 🚀 **Max Wi-Fi Speeds & Resumable Downloads** | High-throughput transfers with HTTP Range (`206 Partial Content`) support for pausing and resuming downloads in Chrome / ADM / IDM. |
| 🎬 **In-Browser Video & Audio Streaming** | Watch MP4/MKV/WebM videos with instant seeking or listen to MP3/WAV tracks in a persistent floating audio dock without filling phone storage. |
| 📚 **Integrated Document & Photo Lightbox** | Preview lecture notes, PDFs, code files, and zoom high-res photos directly in the browser. |
| 👥 **Real-Time Active Peer Counter** | Live Server-Sent Events (SSE) show how many students/peers are currently connected in the room. |
| 📋 **Hostel Quick-Drop Clipboard** | Instant shared text clipboard for sharing Wi-Fi passwords, lecture notes, links, and code snippets across devices with 1-click copy. |
| 🏷️ **Smart Categorization & Search** | Auto-categorizes files into **Notes**, **Videos**, **Audio**, **Software**, **Images**, with instant live search and multi-criteria sorting. |
| 🎨 **Cyber Dark Glassmorphic UI** | Premium mobile-first responsive dark interface with glowing neon cyan/purple accents. |

---

## 🚀 Quick Start in 3 Seconds

### 1. Requirements
- Python 3.8+ (comes pre-installed or install from [python.org](https://www.python.org/))
- Optional: `pip install -r requirements.txt` (ShareBox also includes built-in fallbacks to run out of the box with zero external pip packages!)

### 2. Launch ShareBox

**On Windows:**
Double-click `run.bat` or run in terminal:
```bash
python app.py
```

**On Linux / macOS:**
```bash
chmod +x run.sh
./run.sh
```

### 3. Connect & Share!
1. The terminal will print the scannable **QR Code** and the local URL (e.g. `http://192.168.1.5:8080` or `http://10.27.53.38:8080`).
2. Have friends in your hostel room scan the QR code with their phone camera or open the link in any browser.
3. Start sharing files, streaming media, and posting quick notes!

---

## 📡 Wi-Fi & Hotspot Setup Guide

### Option A: Mobile Hotspot (Easiest - Anywhere)
1. Turn on **Mobile Hotspot** on your phone or laptop.
2. Connect your laptops and friends' phones to this hotspot. *(Note: You do NOT need active mobile data enabled!)*
3. Run `python app.py` on the host computer.
4. Scan the QR code or visit the link printed in the terminal.

### Option B: Hostel / College Wi-Fi / Router
1. Ensure all devices are connected to the same hostel or campus Wi-Fi network.
2. Run `python app.py`.
3. Open the printed IP link on any device.

---

## ⚙️ Command Line Options

```text
usage: sharebox.py [-h] [--port PORT] [--host HOST] [--dir DIR] [--no-qr]

ShareBox - Local Wi-Fi & Hotspot File Sharing Hub

options:
  -h, --help            Show this help message and exit
  --port PORT, -p PORT  Port to bind server (default: 8080)
  --host HOST, -H HOST  Host address to bind (default: 0.0.0.0)
  --dir DIR, -d DIR     Directory for shared files (default: ./shared_storage)
  --no-qr               Disable terminal QR code rendering
```

---

## 🏗️ Project Architecture

```text
antigravity/
├── app.py                  # Convenient entry point
├── sharebox.py             # Multithreaded Python server & storage engine
├── requirements.txt        # Optional pip dependencies
├── run.bat                 # 1-Click Windows batch launcher
├── run.sh                  # 1-Click Linux/macOS shell launcher
├── README.md               # Documentation & manual
├── shared_storage/         # Local folder where shared files are stored
│   ├── .sharebox_meta.json # JSON database storing file metadata & download counts
│   └── .sharebox_snippets.json # Shared quick-drop clipboard notes
└── static/                 # Embedded Frontend Web Application
    ├── index.html          # Semantic HTML5 layout & media modals
    ├── css/
    │   └── style.css       # Cyber Dark glassmorphic design system
    └── js/
        └── app.js          # SSE live sync, chunked upload, media stream engine
```

---

## 🛡️ Privacy & Performance

- **100% Local**: No telemetry, no external cloud dependencies, no third-party tracking.
- **Low Memory Footprint**: Streaming chunked upload and streaming HTTP range downloads keep host RAM usage under 25MB even when multiple students upload/download 10GB+ video files simultaneously.
- **Zero Internet Required**: All assets (CSS, JS, fonts, icons) are embedded and self-contained with offline fallbacks.

---
⚡ *Built for seamless student collaboration and hostel file sharing.*
