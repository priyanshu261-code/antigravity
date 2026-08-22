# ShareBox: Local Wi-Fi & Hotspot File-Sharing & Media Streaming Hub

ShareBox is a zero-internet, zero-app, high-speed local file-sharing and media streaming system engineered for college campuses, dorms, and hostel rooms. When launched on a host computer, it auto-detects the active Wi-Fi / Hotspot IP address, renders a scannable ASCII/ANSI QR code directly in the terminal, and serves a modern, dark-mode glassmorphic web application accessible from any smartphone, tablet, or laptop browser.

## User Review Required

> [!NOTE]
> ShareBox is built using Python 3 with a high-performance multithreaded backend supporting HTTP Range streaming (`206 Partial Content`) for video/audio seeking and resumable downloads, chunked streaming uploads for multi-gigabyte files, Server-Sent Events (SSE) for real-time peer count and instant file sync, and an embedded pure Python fallback for terminal QR code rendering.

> [!TIP]
> No apps, accounts, or active internet connection are required. All transfers and streaming operate 100% locally at the maximum throughput of the local Wi-Fi or mobile hotspot.

---

## Key Features & Architecture

1. **Auto Network & IP Detection**:
   - Enumerates network interfaces to detect active Wi-Fi / Hotspot IPv4 addresses.
   - Formulates the exact access URL (e.g. `http://192.168.1.5:8080` or `http://10.27.53.38:8080`).

2. **Scannable Terminal QR Code**:
   - Renders a 1:1 square ratio ANSI/Unicode QR code in the terminal using half-block characters (`▀`, `▄`, `█`, ` `) with UTF-8 encoding support on Windows and Unix terminals.
   - Scannable in sub-second time by any iOS Camera, Google Lens, Samsung Camera, or QR scanner.

3. **High-Speed Resumable Downloads & Chunked Uploads**:
   - HTTP Range header support (`Range: bytes=start-end`, `Accept-Ranges: bytes`) enabling download managers and browsers to pause and resume downloads at full Wi-Fi speed.
   - Chunked streaming upload pipeline that writes directly to disk, keeping memory consumption negligible (< 20MB) even when uploading 10GB+ video files.

4. **In-Browser Zero-App Media Streaming & Viewers**:
   - **Video Player**: HTML5 video streaming with instant scrubbing/seeking, playback speed controls (0.5x to 2x), Picture-in-Picture, and fullscreen.
   - **Audio Player**: Dedicated sticky bottom audio dock with live scrubber, background playback, and waveform animation.
   - **Document / PDF Viewer**: Clean in-browser modal viewer with zoom and page navigation.
   - **Image Lightbox**: High-res viewer with zoom and gallery navigation.
   - **Code & Text Reader**: In-browser text/code reader with copy capability.

5. **Real-time Connected Peers Counter & Live Updates**:
   - Server-Sent Events (SSE) channel (`/api/events`) broadcasting live active peer counts and instant file notifications without refreshing the page.

6. **Hostel Quick-Drop Clipboard / Text Snippets**:
   - Shared instant text clipboard for sharing Wi-Fi passwords, lecture notes, links, and code snippets across devices with 1-click copy.

7. **Aesthetics & UI**:
   - Modern Cyber Dark theme with glassmorphism, glowing cyan/indigo accents, smooth micro-interactions, responsive mobile/tablet/desktop layouts, search by name/uploader, category filtering, and multiple sort modes.

---

## Proposed Changes

### Backend Components

#### [NEW] [sharebox.py](file:///d:/priyanshu/antigravity/sharebox.py)
- Main entry point with CLI argument parsing (`--port`, `--host`, `--dir`, `--no-qr`).
- IP detection module for Wi-Fi, Hotspot, and LAN interfaces.
- ANSI terminal dashboard and scannable QR code generator (with `qrcode` library and self-contained pure Python fallback).
- Multithreaded HTTP Server with:
  - Streaming file upload handler.
  - Byte-Range streaming media and resumable download handler.
  - JSON metadata database manager (`shared_storage/.sharebox_meta.json`).
  - Server-Sent Events (SSE) broadcaster for peer tracking and file events.
  - REST endpoints for files, categories, downloads, streams, text snippets, and stats.

#### [NEW] [app.py](file:///d:/priyanshu/antigravity/app.py)
- Friendly alias entrypoint redirecting to `sharebox.py`.

#### [NEW] [requirements.txt](file:///d:/priyanshu/antigravity/requirements.txt)
- Dependency specifications (`qrcode>=8.0`, `colorama>=0.4.6`, `psutil>=5.9.0`).

---

### Frontend Components

#### [NEW] [static/index.html](file:///d:/priyanshu/antigravity/static/index.html)
- Modern HTML5 structure:
  - Header: Logo, Live Connected Peer Pill (with pulse animation), Storage capacity, Hotspot Wi-Fi badge, QR Code modal trigger, Text Drop tab trigger.
  - Hero Section: Drag-and-drop file upload zone with alias input and category dropdown.
  - Active Uploads Tray: Real-time progress bars, upload speed, ETA, and cancellation.
  - Content Dashboard: Search bar, category pill filters (All, Notes, Videos, Audio, Software, Images, Others), sort selector, Grid/List view toggle.
  - File Grid / List: Dynamic file cards with thumbnail/icon, size, uploader, timestamp, download count, preview button, and download button.
  - In-Browser Media Modals:
    - Custom Video Player modal with seek bar, playback speed, PiP, fullscreen.
    - Floating Audio Player dock.
    - PDF & Document viewer modal.
    - Image Lightbox modal with zoom & pan.
    - Code & Text viewer modal.
    - Host QR Code modal for peer-to-peer scanning.
    - Text Snippet / Clipboard sharing modal.

#### [NEW] [static/css/style.css](file:///d:/priyanshu/antigravity/static/css/style.css)
- Deep dark cyber palette (`#0a0d14`, `#101726`, `#182238`, `#00f2fe`, `#4facfe`, `#7f00ff`, `#00e676`).
- Glassmorphism effects with backdrop blur.
- Mobile-first responsive layout (optimized for phones in portrait/landscape and laptops/desktops).
- Micro-animations: glowing pulse badges, upload progress gradients, hover lifts, modal transitions.

#### [NEW] [static/js/app.js](file:///d:/priyanshu/antigravity/static/js/app.js)
- Vanilla JavaScript client:
  - SSE listener for live peer count and file list auto-refresh.
  - Chunked file upload queue with `XMLHttpRequest` progress reporting, upload speed calculation (MB/s), and ETA computation.
  - Alias persistence via `localStorage`.
  - Category filtering and real-time instant search.
  - In-browser media preview management (Video, Audio, PDF, Image, Code).
  - High-speed download trigger.
  - Text Drop copy & share functionality.
  - Toast notification system for user feedback.

---

### Launch Scripts & Documentation

#### [NEW] [run.bat](file:///d:/priyanshu/antigravity/run.bat)
- 1-click Windows batch launcher that activates Python, checks dependencies, and launches ShareBox.

#### [NEW] [run.sh](file:///d:/priyanshu/antigravity/run.sh)
- 1-click Unix/macOS launcher.

#### [NEW] [README.md](file:///d:/priyanshu/antigravity/README.md)
- Complete user manual with visual architecture diagram, step-by-step hotspot setup guide for Windows/Mac/Linux/Android/iOS, and feature matrix.

---

## Verification Plan

### Automated Tests
- Test server startup and IP detection using Python CLI.
- Test terminal QR code generation with UTF-8 character encoding.
- Test REST API endpoints (`/api/info`, `/api/files`, `/api/upload`, `/api/download`, `/api/stream`, `/api/events`, `/api/text-drop`).
- Test HTTP Byte-Range requests (`Range: bytes=0-1024`, `Range: bytes=1024-`) returning `206 Partial Content` and accurate `Content-Range`.
- Test multi-part file upload with metadata and category assignment.

### Manual / Browser Verification
- Launch the server locally on port 8080.
- Verify the terminal prints the scannable QR code and clickable URLs.
- Open the web interface in the browser.
- Verify UI aesthetics: dark mode, glassmorphism, responsive mobile layout, glowing peer badge.
- Test uploading various file types (PDF, MP4, MP3, PNG, ZIP, TXT).
- Test in-browser video streaming and audio playback.
- Test search, category filtering, and sorting.
- Test live active peer counter updates.
- Test Text Drop / Clipboard sharing.
