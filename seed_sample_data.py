#!/usr/bin/env python3
"""
Seed sample dummy files and verify running server
"""
import urllib.request
import urllib.parse
import json

SERVER_URL = "http://127.0.0.1:8080"

def upload_sample(filename, content_bytes, uploader, category):
    boundary = '----WebKitFormBoundarySampleSeed77'
    body = bytearray()
    body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="uploader"\r\n\r\n{uploader}\r\n'.encode('utf-8'))
    body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="category"\r\n\r\n{category}\r\n'.encode('utf-8'))
    body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode('utf-8'))
    body.extend(content_bytes)
    body.extend(f'\r\n--{boundary}--\r\n'.encode('utf-8'))

    req = urllib.request.Request(
        f"{SERVER_URL}/api/upload",
        data=bytes(body),
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def post_snippet(text, author):
    req = urllib.request.Request(
        f"{SERVER_URL}/api/text-drop",
        data=json.dumps({'text': text, 'author': author}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

if __name__ == '__main__':
    print("Seeding sample hostel resources...")
    
    # 1. Notes
    upload_sample(
        "Operating_Systems_Unit3_Notes.pdf",
        b"%PDF-1.4\n% Sample ShareBox PDF Document\n1 0 obj\n<< /Title (OS Unit 3) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF",
        "Rahul (CS-A)",
        "Notes"
    )
    
    # 2. Text / Code
    upload_sample(
        "Dijkstra_Shortest_Path.cpp",
        b"#include <iostream>\n#include <vector>\n#include <queue>\nusing namespace std;\n\nint main() {\n    cout << \"ShareBox Algorithm Archive\" << endl;\n    return 0;\n}",
        "Priya (Room 308)",
        "Software"
    )

    # 3. Quick Drop Snippet
    post_snippet("Hostel Block B Wi-Fi: SpeedFast_5GHz | Key: CampusPass@2026", "Hostel Admin")
    post_snippet("CSE 401 Assignment deadline extended to Monday 11:59 PM!", "CR Ananya")

    print("Sample data seeded successfully!")
