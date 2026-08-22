#!/usr/bin/env python3
"""
ShareBox Automated Test Suite
Validates server startup, API endpoints, streaming chunked upload, HTTP Range requests, and data persistence.
"""

import os
import sys
import time
import json
import urllib.request
import urllib.parse
import http.client
import socket
import threading
import unittest

from sharebox import ThreadingHTTPServer, ShareBoxHandler, StorageManager, get_local_ip_addresses

TEST_PORT = 8999
TEST_HOST = '127.0.0.1'
TEST_STORAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_storage')


class TestShareBox(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create test storage
        os.makedirs(TEST_STORAGE, exist_ok=True)
        cls.storage = StorageManager(TEST_STORAGE)
        
        # Start server in background thread
        cls.server = ThreadingHTTPServer((TEST_HOST, TEST_PORT), ShareBoxHandler)
        cls.server.primary_ip = TEST_HOST
        cls.server.all_ips = [TEST_HOST]
        cls.server.server_port = TEST_PORT
        cls.server.storage = cls.storage
        
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        # Clean up test storage
        import shutil
        if os.path.exists(TEST_STORAGE):
            shutil.rmtree(TEST_STORAGE, ignore_errors=True)

    def test_01_index_and_static_files(self):
        """Test serving HTML, CSS, and JS static assets."""
        url = f"http://{TEST_HOST}:{TEST_PORT}/"
        with urllib.request.urlopen(url) as response:
            self.assertEqual(response.status, 200)
            content = response.read().decode('utf-8')
            self.assertIn('ShareBox', content)
            self.assertIn('dropZone', content)

        css_url = f"http://{TEST_HOST}:{TEST_PORT}/static/css/style.css"
        with urllib.request.urlopen(css_url) as response:
            self.assertEqual(response.status, 200)
            content = response.read().decode('utf-8')
            self.assertIn('dark-theme', content)

        js_url = f"http://{TEST_HOST}:{TEST_PORT}/static/js/app.js"
        with urllib.request.urlopen(js_url) as response:
            self.assertEqual(response.status, 200)
            content = response.read().decode('utf-8')
            self.assertIn('openMediaPreview', content)

    def test_02_server_info_api(self):
        """Test GET /api/info."""
        url = f"http://{TEST_HOST}:{TEST_PORT}/api/info"
        with urllib.request.urlopen(url) as response:
            self.assertEqual(response.status, 200)
            data = json.loads(response.read().decode('utf-8'))
            self.assertIn('primary_ip', data)
            self.assertIn('port', data)
            self.assertIn('stats', data)

    def test_03_file_upload_and_list(self):
        """Test multipart file upload and listing."""
        boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
        body = bytearray()
        
        # Add uploader field
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="uploader"\r\n\r\nRahul\r\n'.encode('utf-8'))
        # Add category field
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="category"\r\n\r\nNotes\r\n'.encode('utf-8'))
        # Add file content
        file_content = b"Lecture Notes on Distributed Systems - Module 1\nLine 2: High speed Wi-Fi sharing"
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="notes_module1.txt"\r\nContent-Type: text/plain\r\n\r\n'.encode('utf-8'))
        body.extend(file_content)
        body.extend(f'\r\n--{boundary}--\r\n'.encode('utf-8'))

        req = urllib.request.Request(
            f"http://{TEST_HOST}:{TEST_PORT}/api/upload",
            data=bytes(body),
            headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
        )
        
        with urllib.request.urlopen(req) as response:
            self.assertEqual(response.status, 200)
            data = json.loads(response.read().decode('utf-8'))
            self.assertTrue(data.get('success'))
            self.assertEqual(data.get('count'), 1)
            uploaded_file = data['uploaded'][0]
            self.assertEqual(uploaded_file['filename'], 'notes_module1.txt')
            self.assertEqual(uploaded_file['uploader'], 'Rahul')
            self.assertEqual(uploaded_file['category'], 'Notes')
            self.__class__.test_file_id = uploaded_file['id']

        # Verify in /api/files
        list_url = f"http://{TEST_HOST}:{TEST_PORT}/api/files"
        with urllib.request.urlopen(list_url) as response:
            self.assertEqual(response.status, 200)
            data = json.loads(response.read().decode('utf-8'))
            files = data.get('files', [])
            self.assertTrue(any(f['id'] == self.__class__.test_file_id for f in files))

    def test_04_http_range_streaming(self):
        """Test HTTP Byte-Range requests for video/audio seek and resumable downloads."""
        file_id = self.__class__.test_file_id
        url = f"http://{TEST_HOST}:{TEST_PORT}/api/stream/{file_id}"

        # Request bytes 0 to 10
        req = urllib.request.Request(url, headers={'Range': 'bytes=0-10'})
        with urllib.request.urlopen(req) as response:
            self.assertEqual(response.status, 206) # 206 Partial Content
            self.assertEqual(response.headers.get('Accept-Ranges'), 'bytes')
            self.assertIn('bytes 0-10/', response.headers.get('Content-Range'))
            content = response.read()
            self.assertEqual(len(content), 11)
            self.assertEqual(content, b"Lecture Not")

    def test_05_download_counter(self):
        """Test download endpoint and counter increment."""
        file_id = self.__class__.test_file_id
        url = f"http://{TEST_HOST}:{TEST_PORT}/api/download/{file_id}"

        with urllib.request.urlopen(url) as response:
            self.assertEqual(response.status, 200)
            self.assertIn('attachment', response.headers.get('Content-Disposition'))
            data = response.read()
            self.assertIn(b"Lecture Notes", data)

        meta = self.storage.get_file_meta(file_id)
        self.assertGreaterEqual(meta['download_count'], 1)

    def test_06_text_snippets_clipboard(self):
        """Test hostel quick-drop clipboard sharing."""
        post_url = f"http://{TEST_HOST}:{TEST_PORT}/api/text-drop"
        payload = json.dumps({'text': 'Hostel Room Wi-Fi: HostelPass123', 'author': 'Aman (Room 102)'}).encode('utf-8')
        req = urllib.request.Request(post_url, data=payload, headers={'Content-Type': 'application/json'})
        
        with urllib.request.urlopen(req) as response:
            self.assertEqual(response.status, 200)
            data = json.loads(response.read().decode('utf-8'))
            self.assertTrue(data.get('success'))
            snippet_id = data['snippet']['id']

        # Verify listing
        with urllib.request.urlopen(post_url) as response:
            self.assertEqual(response.status, 200)
            data = json.loads(response.read().decode('utf-8'))
            snippets = data.get('snippets', [])
            self.assertTrue(any(s['id'] == snippet_id for s in snippets))

    def test_07_qr_code_endpoint(self):
        """Test QR code generation endpoint."""
        url = f"http://{TEST_HOST}:{TEST_PORT}/api/qr"
        with urllib.request.urlopen(url) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get('Content-Type'), 'image/svg+xml')
            data = response.read()
            self.assertIn(b'<svg', data)

    def test_08_delete_file(self):
        """Test file deletion."""
        file_id = self.__class__.test_file_id
        req = urllib.request.Request(
            f"http://{TEST_HOST}:{TEST_PORT}/api/files/{file_id}",
            method='DELETE'
        )
        with urllib.request.urlopen(req) as response:
            self.assertEqual(response.status, 200)
            data = json.loads(response.read().decode('utf-8'))
            self.assertTrue(data.get('success'))

        # Verify it's gone
        meta = self.storage.get_file_meta(file_id)
        self.assertIsNone(meta)


if __name__ == '__main__':
    unittest.main()
