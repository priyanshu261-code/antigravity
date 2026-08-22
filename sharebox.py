#!/usr/bin/env python3
"""
ShareBox - Local Wi-Fi & Hotspot File-Sharing and Media Streaming Hub
High-speed zero-internet file sharing and in-browser media streaming for campuses and hostels.
"""

import os
import sys
import json
import time
import socket
import shutil
import urllib.parse
import mimetypes
import uuid
import threading
import re
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# Ensure UTF-8 output encoding in Windows terminals
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Determine base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
DEFAULT_STORAGE_DIR = os.path.join(BASE_DIR, 'shared_storage')

# Global server state
ACTIVE_CLIENTS = set()
CLIENTS_LOCK = threading.Lock()
EVENT_QUEUES = []
EVENT_QUEUES_LOCK = threading.Lock()

# ANSI Color Codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def get_local_ip_addresses():
    """Detect and return all valid local IPv4 addresses, prioritizing Wi-Fi/Hotspot."""
    ips = []
    
    # Try psutil if available
    try:
        import psutil
        interfaces = psutil.net_if_addrs()
        stats = psutil.net_if_stats() if hasattr(psutil, 'net_if_stats') else {}
        
        priority_ips = []
        regular_ips = []
        
        for iface_name, addrs in interfaces.items():
            is_up = stats.get(iface_name).isup if iface_name in stats else True
            if not is_up:
                continue
                
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    ip = addr.address
                    if ip.startswith("127.") or ip.startswith("169.254."):
                        continue
                    # Prioritize Wi-Fi, WLAN, Hotspot, Local Area
                    name_lower = iface_name.lower()
                    if any(k in name_lower for k in ['wi-fi', 'wifi', 'wlan', 'hotspot', 'wireless', 'ap']):
                        priority_ips.append((iface_name, ip))
                    else:
                        regular_ips.append((iface_name, ip))
                        
        for iface, ip in priority_ips + regular_ips:
            if ip not in ips:
                ips.append(ip)
    except Exception:
        pass

    # Method 2: UDP Socket routing test (most accurate for active outgoing route)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        # Connect to a non-routable address to force routing table resolution
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith('127.') and not ip.startswith('169.254.') and ip not in ips:
            ips.insert(0, ip)
    except Exception:
        pass

    # Method 3: Hostname resolution fallback
    try:
        hostname = socket.gethostname()
        host_ip = socket.gethostbyname(hostname)
        if host_ip and not host_ip.startswith('127.') and not host_ip.startswith('169.254.') and host_ip not in ips:
            ips.append(host_ip)
    except Exception:
        pass

    if not ips:
        ips.append("127.0.0.1")
        
    return ips


def detect_file_category(filename):
    """Categorize file based on its extension."""
    ext = os.path.splitext(filename)[1].lower()
    
    categories = {
        'Notes': ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.txt', '.md', '.rtf', '.epub', '.csv', '.odt'],
        'Videos': ['.mp4', '.mkv', '.webm', '.mov', '.avi', '.m4v', '.3gp', '.flv', '.wmv', '.ts'],
        'Audio': ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a', '.wma', '.opus'],
        'Software': ['.exe', '.apk', '.dmg', '.pkg', '.zip', '.rar', '.7z', '.tar', '.gz', '.iso', '.py', '.js', '.html', '.css', '.cpp', '.java', '.c', '.sh', '.json', '.xml'],
        'Images': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico', '.tiff', '.heic']
    }
    
    for cat, exts in categories.items():
        if ext in exts:
            return cat
    return 'Others'


def get_preview_type(mime_type, filename):
    """Determine if and how a file can be previewed directly in the browser."""
    ext = os.path.splitext(filename)[1].lower()
    if mime_type:
        if mime_type.startswith('video/'):
            return 'video'
        if mime_type.startswith('audio/'):
            return 'audio'
        if mime_type.startswith('image/'):
            return 'image'
        if mime_type == 'application/pdf' or ext == '.pdf':
            return 'pdf'
        if mime_type.startswith('text/') or ext in ['.txt', '.md', '.py', '.js', '.json', '.html', '.css', '.cpp', '.java', '.c', '.sh', '.csv', '.log', '.xml']:
            return 'text'
            
    if ext in ['.mp4', '.webm', '.mov', '.mkv']:
        return 'video'
    if ext in ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac']:
        return 'audio'
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']:
        return 'image'
    if ext == '.pdf':
        return 'pdf'
    if ext in ['.txt', '.md', '.py', '.js', '.json', '.html', '.css', '.cpp', '.java', '.c', '.sh', '.csv', '.log', '.xml']:
        return 'text'
        
    return 'download'


def format_size(bytes_val):
    """Format bytes into a readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}" if unit != 'B' else f"{int(bytes_val)} B"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"


class StorageManager:
    """Manages file storage, disk I/O, metadata, and text snippets."""
    def __init__(self, storage_dir=DEFAULT_STORAGE_DIR):
        self.storage_dir = os.path.abspath(storage_dir)
        os.makedirs(self.storage_dir, exist_ok=True)
        self.meta_path = os.path.join(self.storage_dir, '.sharebox_meta.json')
        self.snippets_path = os.path.join(self.storage_dir, '.sharebox_snippets.json')
        self.lock = threading.Lock()
        self.files_meta = {}
        self.snippets = []
        self._load_metadata()
        self._load_snippets()
        self._sync_disk_files()

    def _load_metadata(self):
        if os.path.exists(self.meta_path):
            try:
                with open(self.meta_path, 'r', encoding='utf-8') as f:
                    self.files_meta = json.load(f)
            except Exception:
                self.files_meta = {}

    def _save_metadata(self):
        try:
            temp_path = self.meta_path + '.tmp'
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.files_meta, f, indent=2)
            os.replace(temp_path, self.meta_path)
        except Exception as e:
            print(f"Error saving metadata: {e}")

    def _load_snippets(self):
        if os.path.exists(self.snippets_path):
            try:
                with open(self.snippets_path, 'r', encoding='utf-8') as f:
                    self.snippets = json.load(f)
            except Exception:
                self.snippets = []

    def _save_snippets(self):
        try:
            temp_path = self.snippets_path + '.tmp'
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.snippets, f, indent=2)
            os.replace(temp_path, self.snippets_path)
        except Exception as e:
            print(f"Error saving snippets: {e}")

    def _sync_disk_files(self):
        """Sync files present in folder that may not be in metadata."""
        with self.lock:
            changed = False
            for item in os.listdir(self.storage_dir):
                if item.startswith('.'):
                    continue
                file_path = os.path.join(self.storage_dir, item)
                if not os.path.isfile(file_path):
                    continue
                # Check if this stored_name is already in meta
                found = any(m.get('stored_name') == item for m in self.files_meta.values())
                if not found:
                    file_id = str(uuid.uuid4())[:8]
                    size = os.path.getsize(file_path)
                    mime_type, _ = mimetypes.guess_type(item)
                    category = detect_file_category(item)
                    preview_type = get_preview_type(mime_type, item)
                    mtime = os.path.getmtime(file_path)
                    
                    self.files_meta[file_id] = {
                        'id': file_id,
                        'filename': item,
                        'stored_name': item,
                        'size': size,
                        'formatted_size': format_size(size),
                        'category': category,
                        'uploader': 'Host',
                        'upload_time': datetime.fromtimestamp(mtime).isoformat(),
                        'timestamp': int(mtime),
                        'download_count': 0,
                        'mime_type': mime_type or 'application/octet-stream',
                        'preview_type': preview_type
                    }
                    changed = True
            
            # Clean up deleted files
            deleted_ids = []
            for fid, meta in self.files_meta.items():
                stored_path = os.path.join(self.storage_dir, meta.get('stored_name', ''))
                if not os.path.exists(stored_path):
                    deleted_ids.append(fid)
            for fid in deleted_ids:
                del self.files_meta[fid]
                changed = True

            if changed:
                self._save_metadata()

    def add_file(self, filename, temp_file_path, uploader="Anonymous", category=None):
        """Add a newly uploaded file to storage and metadata."""
        with self.lock:
            file_id = str(uuid.uuid4())[:8]
            # Sanitize filename
            clean_name = os.path.basename(filename).strip()
            if not clean_name:
                clean_name = f"file_{file_id}"
            
            name_parts = os.path.splitext(clean_name)
            stored_name = f"{file_id}_{clean_name}"
            dest_path = os.path.join(self.storage_dir, stored_name)
            
            # Move temp file to final destination
            shutil.move(temp_file_path, dest_path)
            
            size = os.path.getsize(dest_path)
            mime_type, _ = mimetypes.guess_type(clean_name)
            if not category or category == 'Auto':
                category = detect_file_category(clean_name)
            preview_type = get_preview_type(mime_type, clean_name)
            
            meta = {
                'id': file_id,
                'filename': clean_name,
                'stored_name': stored_name,
                'size': size,
                'formatted_size': format_size(size),
                'category': category,
                'uploader': uploader.strip() or "Anonymous",
                'upload_time': datetime.now().isoformat(),
                'timestamp': int(time.time()),
                'download_count': 0,
                'mime_type': mime_type or 'application/octet-stream',
                'preview_type': preview_type
            }
            self.files_meta[file_id] = meta
            self._save_metadata()
            return meta

    def get_file_meta(self, file_id):
        with self.lock:
            return self.files_meta.get(file_id)

    def get_file_path(self, file_id):
        with self.lock:
            meta = self.files_meta.get(file_id)
            if meta:
                path = os.path.join(self.storage_dir, meta['stored_name'])
                if os.path.exists(path):
                    return path
            return None

    def increment_download(self, file_id):
        with self.lock:
            if file_id in self.files_meta:
                self.files_meta[file_id]['download_count'] += 1
                self._save_metadata()

    def delete_file(self, file_id):
        with self.lock:
            if file_id in self.files_meta:
                meta = self.files_meta.pop(file_id)
                path = os.path.join(self.storage_dir, meta['stored_name'])
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass
                self._save_metadata()
                return True
            return False

    def list_files(self, category=None, search=None, sort_by='newest'):
        with self.lock:
            file_list = list(self.files_meta.values())
            
        if category and category != 'All':
            file_list = [f for f in file_list if f.get('category') == category]
            
        if search:
            query = search.lower().strip()
            file_list = [f for f in file_list if query in f.get('filename', '').lower() or query in f.get('uploader', '').lower() or query in f.get('category', '').lower()]
            
        if sort_by == 'newest':
            file_list.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        elif sort_by == 'oldest':
            file_list.sort(key=lambda x: x.get('timestamp', 0))
        elif sort_by == 'largest':
            file_list.sort(key=lambda x: x.get('size', 0), reverse=True)
        elif sort_by == 'smallest':
            file_list.sort(key=lambda x: x.get('size', 0))
        elif sort_by == 'name':
            file_list.sort(key=lambda x: x.get('filename', '').lower())
        elif sort_by == 'downloads':
            file_list.sort(key=lambda x: x.get('download_count', 0), reverse=True)
            
        return file_list

    def add_snippet(self, text, author="Anonymous"):
        with self.lock:
            snippet_id = str(uuid.uuid4())[:8]
            snippet = {
                'id': snippet_id,
                'text': text.strip(),
                'author': author.strip() or "Anonymous",
                'timestamp': int(time.time()),
                'created_at': datetime.now().strftime("%I:%M %p")
            }
            self.snippets.insert(0, snippet)
            # Keep maximum 50 recent snippets
            if len(self.snippets) > 50:
                self.snippets = self.snippets[:50]
            self._save_snippets()
            return snippet

    def list_snippets(self):
        with self.lock:
            return list(self.snippets)

    def delete_snippet(self, snippet_id):
        with self.lock:
            self.snippets = [s for s in self.snippets if s.get('id') != snippet_id]
            self._save_snippets()
            return True

    def get_storage_stats(self):
        try:
            total, used, free = shutil.disk_usage(self.storage_dir)
            files_count = len(self.files_meta)
            total_shared_bytes = sum(f.get('size', 0) for f in self.files_meta.values())
            return {
                'disk_total': total,
                'disk_free': free,
                'disk_used': used,
                'formatted_disk_free': format_size(free),
                'files_count': files_count,
                'total_shared_bytes': total_shared_bytes,
                'formatted_shared_size': format_size(total_shared_bytes)
            }
        except Exception:
            return {
                'disk_total': 0, 'disk_free': 0, 'disk_used': 0,
                'formatted_disk_free': 'N/A', 'files_count': 0,
                'total_shared_bytes': 0, 'formatted_shared_size': '0 B'
            }


def broadcast_event(event_type, data):
    """Broadcast an SSE event to all connected browsers."""
    message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    with EVENT_QUEUES_LOCK:
        dead_queues = []
        for q in EVENT_QUEUES:
            try:
                q.put_nowait(message)
            except Exception:
                dead_queues.append(q)
        for q in dead_queues:
            if q in EVENT_QUEUES:
                EVENT_QUEUES.remove(q)


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """High-concurrency multithreaded HTTP Server."""
    daemon_threads = True
    allow_reuse_address = True


class ShareBoxHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for ShareBox with streaming support and REST API."""

    def log_message(self, format, *args):
        # Clean formatted logging for terminal
        client_ip = self.client_address[0]
        status_code = args[1] if len(args) > 1 else ''
        # Avoid spamming log with frequent SSE polling or static asset requests
        if '/api/events' not in self.path and not self.path.startswith('/static/'):
            print(f"{DIM}[{datetime.now().strftime('%H:%M:%S')}]{RESET} {CYAN}{client_ip}{RESET} {self.command} {self.path} {GREEN}{status_code}{RESET}")

    def send_json(self, data, status=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Range')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Track active client peer
        client_ip = self.client_address[0]
        with CLIENTS_LOCK:
            if client_ip not in ACTIVE_CLIENTS:
                ACTIVE_CLIENTS.add(client_ip)
                broadcast_event('peer_count', {'count': len(ACTIVE_CLIENTS)})

        # Route: Home
        if path == '/' or path == '/index.html':
            self.serve_static_file('index.html', 'text/html; charset=utf-8')
            return

        # Route: Static Assets
        if path.startswith('/static/'):
            rel_path = path[8:] # Strip /static/
            self.serve_static_file(rel_path)
            return

        # Route: API - Server & Network Info
        if path == '/api/info':
            stats = self.server.storage.get_storage_stats()
            with CLIENTS_LOCK:
                active_count = len(ACTIVE_CLIENTS)
            data = {
                'hostname': socket.gethostname(),
                'primary_ip': self.server.primary_ip,
                'all_ips': self.server.all_ips,
                'port': self.server.server_port,
                'url': f"http://{self.server.primary_ip}:{self.server.server_port}",
                'active_peers': active_count,
                'stats': stats
            }
            self.send_json(data)
            return

        # Route: API - List Files
        if path == '/api/files':
            category = query.get('category', [None])[0]
            search = query.get('search', [None])[0]
            sort_by = query.get('sort', ['newest'])[0]
            files = self.server.storage.list_files(category=category, search=search, sort_by=sort_by)
            self.send_json({'files': files, 'count': len(files)})
            return

        # Route: API - Download File (Resumable Range & Attachment)
        if path.startswith('/api/download/'):
            file_id = path[14:]
            self.handle_file_stream(file_id, as_attachment=True)
            return

        # Route: API - Stream / Preview Media (HTTP Byte Range)
        if path.startswith('/api/stream/'):
            file_id = path[12:]
            self.handle_file_stream(file_id, as_attachment=False)
            return

        # Route: API - List Text Snippets
        if path == '/api/text-drop':
            snippets = self.server.storage.list_snippets()
            self.send_json({'snippets': snippets})
            return

        # Route: API - QR Code Image / SVG
        if path == '/api/qr':
            self.handle_qr_request()
            return

        # Route: API - Server-Sent Events (Live real-time sync & peer counter)
        if path == '/api/events':
            self.handle_sse()
            return

        # Fallback 404
        self.send_error(404, "File Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Route: File Upload (Streaming chunked multipart to disk)
        if path == '/api/upload':
            self.handle_file_upload()
            return

        # Route: Text Drop / Snippet Post
        if path == '/api/text-drop':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(body) if body else {}
                text = data.get('text', '').strip()
                author = data.get('author', 'Anonymous').strip()
                if not text:
                    self.send_json({'error': 'Text cannot be empty'}, status=400)
                    return
                snippet = self.server.storage.add_snippet(text, author)
                broadcast_event('snippet_added', snippet)
                self.send_json({'success': True, 'snippet': snippet})
            except Exception as e:
                self.send_json({'error': str(e)}, status=500)
            return

        self.send_error(404, "Endpoint Not Found")

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Route: Delete File
        if path.startswith('/api/files/'):
            file_id = path[11:]
            success = self.server.storage.delete_file(file_id)
            if success:
                broadcast_event('file_deleted', {'id': file_id})
                self.send_json({'success': True, 'id': file_id})
            else:
                self.send_json({'error': 'File not found'}, status=404)
            return

        # Route: Delete Snippet
        if path.startswith('/api/text-drop/'):
            snippet_id = path[15:]
            self.server.storage.delete_snippet(snippet_id)
            broadcast_event('snippet_deleted', {'id': snippet_id})
            self.send_json({'success': True, 'id': snippet_id})
            return

        self.send_error(404, "Endpoint Not Found")

    def serve_static_file(self, rel_path, explicit_mime=None):
        """Serve a static file from static/ directory with proper MIME types."""
        # Sanitize rel_path to prevent directory traversal
        norm_path = os.path.normpath(rel_path).lstrip(r'\/')
        file_path = os.path.join(STATIC_DIR, norm_path)
        
        if not os.path.isfile(file_path):
            self.send_error(404, f"Static File Not Found: {rel_path}")
            return
            
        mime_type = explicit_mime
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                if file_path.endswith('.css'):
                    mime_type = 'text/css; charset=utf-8'
                elif file_path.endswith('.js'):
                    mime_type = 'application/javascript; charset=utf-8'
                elif file_path.endswith('.svg'):
                    mime_type = 'image/svg+xml'
                else:
                    mime_type = 'application/octet-stream'

        try:
            file_size = os.path.getsize(file_path)
            with open(file_path, 'rb') as f:
                self.send_response(200)
                self.send_header('Content-Type', mime_type)
                self.send_header('Content-Length', str(file_size))
                self.send_header('Cache-Control', 'public, max-age=3600')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                shutil.copyfileobj(f, self.wfile, length=64 * 1024)
        except Exception as e:
            if not self.wfile.closed:
                self.send_error(500, f"Error reading static file: {e}")

    def handle_file_stream(self, file_id, as_attachment=False):
        """Serve files with full HTTP Byte Range support (206 Partial Content)."""
        meta = self.server.storage.get_file_meta(file_id)
        if not meta:
            self.send_error(404, "File Not Found")
            return

        file_path = self.server.storage.get_file_path(file_id)
        if not file_path or not os.path.exists(file_path):
            self.send_error(404, "File On Disk Not Found")
            return

        if as_attachment:
            self.server.storage.increment_download(file_id)
            broadcast_event('file_downloaded', {'id': file_id, 'downloads': meta['download_count'] + 1})

        file_size = os.path.getsize(file_path)
        mime_type = meta.get('mime_type', 'application/octet-stream')
        filename = meta.get('filename', 'download')

        # Check for Range header
        range_header = self.headers.get('Range')
        
        if range_header:
            # Parse Range: bytes=start-end
            range_match = re.match(r'bytes=(\d*)-(\d*)', range_header)
            if range_match:
                start_str, end_str = range_match.groups()
                start = int(start_str) if start_str else 0
                end = int(end_str) if end_str else file_size - 1
                
                if start >= file_size or end >= file_size or start > end:
                    self.send_response(416)
                    self.send_header('Content-Range', f'bytes */{file_size}')
                    self.end_headers()
                    return
                
                content_length = end - start + 1
                
                self.send_response(206) # Partial Content
                self.send_header('Content-Type', mime_type)
                self.send_header('Content-Length', str(content_length))
                self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Access-Control-Allow-Origin', '*')
                
                if as_attachment:
                    encoded_filename = urllib.parse.quote(filename)
                    self.send_header('Content-Disposition', f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}')
                else:
                    self.send_header('Content-Disposition', 'inline')
                    
                self.end_headers()
                
                # Stream partial chunk
                try:
                    with open(file_path, 'rb') as f:
                        f.seek(start)
                        remaining = content_length
                        chunk_size = 64 * 1024
                        while remaining > 0:
                            read_size = min(chunk_size, remaining)
                            chunk = f.read(read_size)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            remaining -= len(chunk)
                except (ConnectionResetError, BrokenPipeError):
                    pass
                return

        # Full content response
        self.send_response(200)
        self.send_header('Content-Type', mime_type)
        self.send_header('Content-Length', str(file_size))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Access-Control-Allow-Origin', '*')
        
        if as_attachment:
            encoded_filename = urllib.parse.quote(filename)
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}')
        else:
            self.send_header('Content-Disposition', 'inline')
            
        self.end_headers()
        
        try:
            with open(file_path, 'rb') as f:
                shutil.copyfileobj(f, self.wfile, length=64 * 1024)
        except (ConnectionResetError, BrokenPipeError):
            pass

    def handle_file_upload(self):
        """Stream multipart/form-data upload directly to a temporary file on disk."""
        content_type = self.headers.get('Content-Type', '')
        if not content_type.startswith('multipart/form-data'):
            self.send_json({'error': 'Invalid Content-Type; multipart/form-data required'}, status=400)
            return

        boundary_match = re.search(r'boundary=([^;]+)', content_type)
        if not boundary_match:
            self.send_json({'error': 'Missing multipart boundary'}, status=400)
            return
            
        boundary = boundary_match.group(1).strip('"').encode('utf-8')
        boundary_delimiter = b'--' + boundary
        boundary_end = boundary_delimiter + b'--'
        
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length <= 0:
            self.send_json({'error': 'Empty upload payload'}, status=400)
            return

        # Parse form fields and stream file payload
        uploader = "Anonymous"
        category = "Auto"
        filename = "uploaded_file"
        temp_file_path = os.path.join(self.server.storage.storage_dir, f".temp_up_{uuid.uuid4().hex}")
        
        try:
            reader = self.rfile
            bytes_read = 0
            
            # Simple streaming multipart reader
            # Helper to read until delimiter
            def readline_crlf():
                nonlocal bytes_read
                line = reader.readline()
                bytes_read += len(line)
                return line

            # Find first boundary
            line = readline_crlf()
            while line and boundary_delimiter not in line:
                line = readline_crlf()
                if bytes_read >= content_length:
                    break

            uploaded_files_meta = []

            while bytes_read < content_length:
                # Read part headers
                headers = {}
                while True:
                    header_line = readline_crlf()
                    if header_line in (b'\r\n', b'\n', b''):
                        break
                    decoded_header = header_line.decode('utf-8', errors='replace').strip()
                    if ':' in decoded_header:
                        k, v = decoded_header.split(':', 1)
                        headers[k.strip().lower()] = v.strip()

                content_disp = headers.get('content-disposition', '')
                name_match = re.search(r'name="([^"]+)"', content_disp)
                field_name = name_match.group(1) if name_match else None
                filename_match = re.search(r'filename="([^"]+)"', content_disp)
                is_file = bool(filename_match)

                if is_file:
                    raw_filename = filename_match.group(1)
                    filename = os.path.basename(raw_filename)
                    # Stream file data directly to temp file
                    with open(temp_file_path, 'wb') as temp_out:
                        prev_chunk = b''
                        buffer_size = 64 * 1024
                        
                        while bytes_read < content_length:
                            chunk = reader.read(min(buffer_size, content_length - bytes_read))
                            bytes_read += len(chunk)
                            if not chunk:
                                break
                                
                            combined = prev_chunk + chunk
                            boundary_pos = combined.find(boundary_delimiter)
                            
                            if boundary_pos != -1:
                                # Found the end boundary
                                file_chunk = combined[:boundary_pos]
                                if file_chunk.endswith(b'\r\n'):
                                    file_chunk = file_chunk[:-2]
                                elif file_chunk.endswith(b'\n'):
                                    file_chunk = file_chunk[:-1]
                                temp_out.write(file_chunk)
                                
                                # Move to next part
                                break
                            else:
                                # Write safe portion of combined buffer
                                safe_len = max(0, len(combined) - len(boundary_delimiter) - 10)
                                temp_out.write(combined[:safe_len])
                                prev_chunk = combined[safe_len:]
                    
                    if os.path.exists(temp_file_path) and os.path.getsize(temp_file_path) >= 0:
                        meta = self.server.storage.add_file(filename, temp_file_path, uploader=uploader, category=category)
                        uploaded_files_meta.append(meta)
                        broadcast_event('file_added', meta)

                else:
                    # Form field (uploader, category, etc.)
                    field_val_bytes = bytearray()
                    while bytes_read < content_length:
                        line = readline_crlf()
                        if boundary_delimiter in line:
                            break
                        field_val_bytes.extend(line)
                        
                    val = field_val_bytes.decode('utf-8', errors='replace').strip()
                    if field_name == 'uploader' and val:
                        uploader = val
                    elif field_name == 'category' and val:
                        category = val

            self.send_json({
                'success': True,
                'uploaded': uploaded_files_meta,
                'count': len(uploaded_files_meta)
            })

        except Exception as e:
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception:
                    pass
            self.send_json({'error': f"Upload failed: {str(e)}"}, status=500)

    def handle_sse(self):
        """Handle Server-Sent Events for real-time peer count and live file sync."""
        import queue
        event_queue = queue.Queue(maxsize=50)
        
        with EVENT_QUEUES_LOCK:
            EVENT_QUEUES.append(event_queue)

        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        # Send initial state
        with CLIENTS_LOCK:
            active_count = len(ACTIVE_CLIENTS)
        initial_msg = f"event: peer_count\ndata: {json.dumps({'count': active_count})}\n\n"
        try:
            self.wfile.write(initial_msg.encode('utf-8'))
            self.wfile.flush()
        except Exception:
            pass

        try:
            while True:
                try:
                    msg = event_queue.get(timeout=15.0)
                    self.wfile.write(msg.encode('utf-8'))
                    self.wfile.flush()
                except queue.Empty:
                    # Heartbeat comment to keep connection alive
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
        except (ConnectionResetError, BrokenPipeError, Exception):
            pass
        finally:
            with EVENT_QUEUES_LOCK:
                if event_queue in EVENT_QUEUES:
                    EVENT_QUEUES.remove(event_queue)

    def handle_qr_request(self):
        """Generate SVG or Data URL for QR code of the access URL."""
        access_url = f"http://{self.server.primary_ip}:{self.server.server_port}"
        try:
            import qrcode
            import qrcode.image.svg
            factory = qrcode.image.svg.SvgPathImage
            img = qrcode.make(access_url, image_factory=factory, box_size=10, border=2)
            svg_bytes = img.to_string()
            self.send_response(200)
            self.send_header('Content-Type', 'image/svg+xml')
            self.send_header('Content-Length', str(len(svg_bytes)))
            self.send_header('Cache-Control', 'public, max-age=3600')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(svg_bytes)
        except Exception:
            # Fallback simple text or error
            self.send_json({'url': access_url, 'error': 'SVG QR generation fallback'})


def generate_terminal_qr(data_url):
    """Generate a high-contrast 1:1 square ASCII/Unicode QR code for terminal scanning."""
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(data_url)
        qr.make(fit=True)
        
        # Render using half-block Unicode characters for a true 1:1 aspect ratio
        matrix = qr.get_matrix()
        height = len(matrix)
        width = len(matrix[0])
        
        lines = []
        # Top quiet zone
        lines.append("█" * (width + 2))
        
        for y in range(0, height, 2):
            line = ["█"]
            for x in range(width):
                top = matrix[y][x]
                bot = matrix[y + 1][x] if y + 1 < height else False
                
                # Inverted color scheme for black terminals (white QR modules):
                # top=True (black module), top=False (white space)
                if top and bot:
                    line.append(" ") # both black
                elif top and not bot:
                    line.append("▄") # top black, bot white
                elif not top and bot:
                    line.append("▀") # top white, bot black
                else:
                    line.append("█") # both white
            line.append("█")
            lines.append("".join(line))
            
        # Bottom quiet zone
        lines.append("█" * (width + 2))
        return "\n".join(lines)
    except Exception:
        # Fallback pure-python basic QR representation
        return f"[QR Code for {data_url}]"


def print_banner(primary_ip, all_ips, port, storage_dir):
    """Display a stylish terminal banner with scannable QR Code and connection links."""
    access_url = f"http://{primary_ip}:{port}"
    qr_art = generate_terminal_qr(access_url)
    
    print("\n" + "=" * 64, flush=True)
    print(f"{CYAN}{BOLD}  ⚡ SHAREBOX — Local Campus & Hostel Wi-Fi Hub ⚡{RESET}", flush=True)
    print(f"{DIM}  High-Speed Zero-App File Sharing & Media Streaming{RESET}", flush=True)
    print("=" * 64 + "\n", flush=True)
    
    print(f"{YELLOW}{BOLD}📲 SCAN THIS QR CODE ON YOUR PHONE TO CONNECT:{RESET}\n", flush=True)
    for line in qr_art.split('\n'):
        print(f"   {line}", flush=True)
    print(flush=True)
    
    print(f"{GREEN}{BOLD}🌐 WEBSITE URL:{RESET} {CYAN}{BOLD}{access_url}{RESET}", flush=True)
    
    if len(all_ips) > 1:
        print(f"\n{DIM}Alternate Network Links:{RESET}", flush=True)
        for ip in all_ips:
            if ip != primary_ip:
                print(f"   • http://{ip}:{port}", flush=True)
                
    print(f"\n{BLUE}📂 Storage Folder:{RESET} {storage_dir}", flush=True)
    print(f"{MAGENTA}🚀 Status:{RESET} Server active and listening for local connections...", flush=True)
    print(f"{DIM}Press Ctrl+C anytime to stop ShareBox.{RESET}\n", flush=True)
    print("-" * 64 + "\n", flush=True)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ShareBox - Local Wi-Fi & Hotspot File Sharing Hub")
    parser.add_argument('--port', '-p', type=int, default=8080, help="Port to bind server (default: 8080)")
    parser.add_argument('--host', '-H', type=str, default='0.0.0.0', help="Host address to bind (default: 0.0.0.0)")
    parser.add_argument('--dir', '-d', type=str, default=DEFAULT_STORAGE_DIR, help="Directory for shared files")
    parser.add_argument('--no-qr', action='store_true', help="Disable terminal QR code")
    args = parser.parse_args()

    # Detect network IPs
    ips = get_local_ip_addresses()
    primary_ip = ips[0] if ips else "127.0.0.1"

    # Initialize storage manager
    storage = StorageManager(args.dir)

    # Initialize multithreaded HTTP Server
    server_address = (args.host, args.port)
    try:
        httpd = ThreadingHTTPServer(server_address, ShareBoxHandler)
    except OSError as e:
        if e.errno in (98, 10048): # Address already in use
            alt_port = args.port + 1
            print(f"{YELLOW}Port {args.port} is in use. Trying port {alt_port}...{RESET}")
            httpd = ThreadingHTTPServer((args.host, alt_port), ShareBoxHandler)
            args.port = alt_port
        else:
            raise e

    httpd.primary_ip = primary_ip
    httpd.all_ips = ips
    httpd.server_port = args.port
    httpd.storage = storage

    # Display terminal banner
    if not args.no_qr:
        print_banner(primary_ip, ips, args.port, storage.storage_dir)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}🛑 Stopping ShareBox... Goodbye!{RESET}\n")
        httpd.shutdown()
        httpd.server_close()


if __name__ == '__main__':
    main()
