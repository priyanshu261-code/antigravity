#!/usr/bin/env python3
"""
ShareBox — Vercel Pre-Flight Build Verification & DevOps Quality Control
Simulates Vercel's cloud build environment and tests serverless contracts locally.
"""

import os
import sys
import json
import io
import tempfile
import urllib.parse
from datetime import datetime

# Configure UTF-8 encoding for Windows terminals
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Formatting helpers
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

PASS_BADGE = f"[{GREEN}PASS{RESET}]"
FAIL_BADGE = f"[{RED}FAIL{RESET}]"
WARN_BADGE = f"[{YELLOW}WARN{RESET}]"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class BuildVerifier:
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def log_check(self, name, status, message=""):
        if status == "PASS":
            self.passed += 1
            print(f"  {PASS_BADGE} {name}", flush=True)
        elif status == "FAIL":
            self.failed += 1
            print(f"  {FAIL_BADGE} {name}: {RED}{message}{RESET}", flush=True)
        elif status == "WARN":
            self.warnings += 1
            print(f"  {WARN_BADGE} {name}: {YELLOW}{message}{RESET}", flush=True)
        self.results.append({'name': name, 'status': status, 'message': message})

    def run_all_checks(self):
        print("\n" + "=" * 68, flush=True)
        print(f"{CYAN}{BOLD}  [CHECK] ShareBox -- Vercel Pre-Flight Deployment Verification{RESET}", flush=True)
        print(f"{DIM}  Local DevOps Quality Control & Serverless Contract Testing{RESET}", flush=True)
        print("=" * 68 + "\n", flush=True)

        self.check_vercel_json()
        self.check_vercel_ignore()
        self.check_static_assets()
        self.check_python_dependencies()
        self.check_serverless_entrypoint()
        self.check_simulated_serverless_requests()
        self.check_environment_variables()
        self.print_summary()

    def check_vercel_json(self):
        print(f"{BOLD}Stage 1: Vercel Configuration & Routing Integrity{RESET}")
        vpath = os.path.join(BASE_DIR, 'vercel.json')
        if not os.path.exists(vpath):
            self.log_check("vercel.json existence", "FAIL", "vercel.json not found in repository root")
            return

        try:
            with open(vpath, 'r', encoding='utf-8') as f:
                vconfig = json.load(f)
            self.log_check("vercel.json JSON syntax", "PASS")

            # Check builds & routes
            builds = vconfig.get('builds', [])
            has_py_build = any(b.get('use') == '@vercel/python' and b.get('src') == 'api/index.py' for b in builds)
            if has_py_build:
                self.log_check("Python builder declaration (@vercel/python -> api/index.py)", "PASS")
            else:
                self.log_check("Python builder declaration", "FAIL", "Missing @vercel/python builder for api/index.py")

            routes = vconfig.get('routes', [])
            has_api_route = any(r.get('dest') == '/api/index.py' for r in routes)
            has_static_route = any('static' in r.get('src', '') for r in routes)
            
            if has_api_route and has_static_route:
                self.log_check("Edge routing rules (/static/* and /api/*)", "PASS")
            else:
                self.log_check("Edge routing rules", "WARN", "Review routes for /static and /api in vercel.json")

        except Exception as e:
            self.log_check("vercel.json validation", "FAIL", str(e))
        print()

    def check_vercel_ignore(self):
        print(f"{BOLD}Stage 2: Deployment Bundle Optimization (.vercelignore){RESET}")
        vign_path = os.path.join(BASE_DIR, '.vercelignore')
        if os.path.exists(vign_path):
            with open(vign_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if 'shared_storage' in content and 'test_' in content:
                self.log_check(".vercelignore filters test & local storage files", "PASS")
            else:
                self.log_check(".vercelignore contents", "WARN", "Consider adding shared_storage/ and tests to .vercelignore")
        else:
            self.log_check(".vercelignore existence", "WARN", ".vercelignore not present (bundle may include local test files)")
        print()

    def check_static_assets(self):
        print(f"{BOLD}Stage 3: Static Asset Tree & Reference Integrity{RESET}")
        static_dir = os.path.join(BASE_DIR, 'static')
        required_files = ['index.html', os.path.join('css', 'style.css'), os.path.join('js', 'app.js')]
        
        all_found = True
        for rf in required_files:
            fp = os.path.join(static_dir, rf)
            if os.path.exists(fp):
                self.log_check(f"Static file: static/{rf.replace(os.sep, '/')}", "PASS")
            else:
                self.log_check(f"Static file: static/{rf.replace(os.sep, '/')}", "FAIL", "File missing")
                all_found = False

        if all_found:
            # Check for stylesheet and script references in index.html
            with open(os.path.join(static_dir, 'index.html'), 'r', encoding='utf-8') as f:
                html = f.read()
            if '/static/css/style.css' in html and '/static/js/app.js' in html:
                self.log_check("index.html static asset links (/static/css, /static/js)", "PASS")
            else:
                self.log_check("index.html asset links", "WARN", "Check path casing or relative links in index.html")
        print()

    def check_python_dependencies(self):
        print(f"{BOLD}Stage 4: Python Dependency & Runtime Compatibility{RESET}")
        req_path = os.path.join(BASE_DIR, 'requirements.txt')
        if os.path.exists(req_path):
            with open(req_path, 'r', encoding='utf-8') as f:
                reqs = [r.strip() for r in f.readlines() if r.strip() and not r.strip().startswith('#')]
            self.log_check(f"requirements.txt parsed ({len(reqs)} packages declared)", "PASS")
        else:
            self.log_check("requirements.txt", "FAIL", "requirements.txt not found")

        # Test runtime imports
        try:
            import qrcode
            self.log_check("qrcode library importable", "PASS")
        except ImportError:
            self.log_check("qrcode library", "WARN", "qrcode not installed locally (fallback pure-python QR active)")

        try:
            import colorama
            self.log_check("colorama library importable", "PASS")
        except ImportError:
            self.log_check("colorama library", "WARN", "colorama not installed locally")
        print()

    def check_serverless_entrypoint(self):
        print(f"{BOLD}Stage 5: Serverless Function Contract (api/index.py){RESET}")
        api_path = os.path.join(BASE_DIR, 'api', 'index.py')
        if not os.path.exists(api_path):
            self.log_check("api/index.py existence", "FAIL", "Serverless entrypoint api/index.py not found")
            return

        try:
            # Import api.index
            sys.path.insert(0, BASE_DIR)
            import api.index as serverless_module
            self.log_check("api.index module import", "PASS")

            # Check callable interfaces
            if hasattr(serverless_module, 'handler'):
                self.log_check("BaseHTTPRequestHandler 'handler' exported", "PASS")
            else:
                self.log_check("handler export", "FAIL", "Missing 'handler' in api/index.py")

            if hasattr(serverless_module, 'app') and callable(serverless_module.app):
                self.log_check("WSGI callable 'app' exported", "PASS")
            else:
                self.log_check("app export", "WARN", "Missing WSGI 'app' in api/index.py")

        except Exception as e:
            self.log_check("api/index.py validation", "FAIL", str(e))
        print()

    def check_simulated_serverless_requests(self):
        print(f"{BOLD}Stage 6: Synthetic Serverless Request Execution (Mock Lambda/WSGI){RESET}")
        try:
            import api.index as serverless_module
            
            def run_mock_wsgi(path, method='GET', body_bytes=b'', headers=None):
                status_code = None
                resp_headers = []
                
                def start_response(status, response_headers):
                    nonlocal status_code, resp_headers
                    status_code = int(status.split()[0])
                    resp_headers = response_headers

                environ = {
                    'REQUEST_METHOD': method,
                    'PATH_INFO': path,
                    'QUERY_STRING': '',
                    'SERVER_NAME': 'sharebox.vercel.app',
                    'SERVER_PORT': '443',
                    'wsgi.version': (1, 0),
                    'wsgi.url_scheme': 'https',
                    'wsgi.input': io.BytesIO(body_bytes),
                    'wsgi.errors': sys.stderr,
                    'wsgi.multithread': False,
                    'wsgi.multiprocess': False,
                    'wsgi.run_once': False,
                    'HTTP_HOST': 'sharebox.vercel.app',
                    'CONTENT_LENGTH': str(len(body_bytes))
                }
                if headers:
                    for k, v in headers.items():
                        environ[f"HTTP_{k.upper().replace('-', '_')}"] = v

                result = serverless_module.app(environ, start_response)
                full_body = b"".join(result)
                return status_code, resp_headers, full_body

            # Test 1: GET /api/info
            code, h, body = run_mock_wsgi('/api/info')
            if code == 200:
                data = json.loads(body.decode('utf-8'))
                if 'url' in data and 'stats' in data:
                    self.log_check("Synthetic Serverless: GET /api/info", "PASS")
                else:
                    self.log_check("Synthetic Serverless: GET /api/info", "WARN", "Incomplete info payload")
            else:
                self.log_check("Synthetic Serverless: GET /api/info", "FAIL", f"Returned status {code}")

            # Test 2: GET /api/files
            code, h, body = run_mock_wsgi('/api/files')
            if code == 200:
                data = json.loads(body.decode('utf-8'))
                if 'files' in data:
                    self.log_check("Synthetic Serverless: GET /api/files", "PASS")
                else:
                    self.log_check("Synthetic Serverless: GET /api/files", "FAIL", "Invalid files response")
            else:
                self.log_check("Synthetic Serverless: GET /api/files", "FAIL", f"Returned status {code}")

            # Test 3: POST /api/text-drop
            post_payload = json.dumps({'text': 'Vercel Deployment Verification Test Note', 'author': 'DevOps CI'}).encode('utf-8')
            code, h, body = run_mock_wsgi('/api/text-drop', method='POST', body_bytes=post_payload)
            if code == 200:
                self.log_check("Synthetic Serverless: POST /api/text-drop", "PASS")
            else:
                self.log_check("Synthetic Serverless: POST /api/text-drop", "FAIL", f"Returned status {code}")

            # Test 4: GET /api/qr
            code, h, body = run_mock_wsgi('/api/qr')
            if code == 200:
                self.log_check("Synthetic Serverless: GET /api/qr", "PASS")
            else:
                self.log_check("Synthetic Serverless: GET /api/qr", "FAIL", f"Returned status {code}")

        except Exception as e:
            self.log_check("Synthetic Serverless Testing", "FAIL", str(e))
        print()

    def check_environment_variables(self):
        print(f"{BOLD}Stage 7: Cloud Environment & Storage Fallback Audit{RESET}")
        # Test serverless storage path detection
        temp_dir = tempfile.gettempdir()
        if os.path.exists(temp_dir) and os.access(temp_dir, os.W_OK):
            self.log_check(f"Serverless ephemeral storage (/tmp directory: {temp_dir})", "PASS")
        else:
            self.log_check("Serverless storage", "FAIL", "Temp directory not writable")
        print()

    def print_summary(self):
        print("=" * 68, flush=True)
        total_checks = self.passed + self.failed + self.warnings
        score = int((self.passed / max(1, self.passed + self.failed)) * 100)
        
        print(f"{BOLD}DEPLOYMENT READINESS SUMMARY:{RESET}", flush=True)
        print(f"  * Total Checks: {total_checks}", flush=True)
        print(f"  * Passed:       {GREEN}{self.passed}{RESET}", flush=True)
        print(f"  * Failed:       {RED}{self.failed}{RESET}", flush=True)
        print(f"  * Warnings:     {YELLOW}{self.warnings}{RESET}", flush=True)
        print(f"  * Score:        {GREEN if score >= 90 else YELLOW}{score}%{RESET}\n", flush=True)

        if self.failed == 0:
            print(f"{GREEN}{BOLD}[SUCCESS] READY FOR VERCEL DEPLOYMENT!{RESET}", flush=True)
            print(f"{DIM}You can now push to GitHub and import to Vercel or run 'vercel deploy'.{RESET}", flush=True)
        else:
            print(f"{RED}{BOLD}[ERROR] BUILD VERIFICATION FAILED!{RESET}", flush=True)
            print(f"{DIM}Please resolve the failed checks above before deploying to Vercel.{RESET}", flush=True)
        print("=" * 68 + "\n", flush=True)


if __name__ == '__main__':
    verifier = BuildVerifier()
    verifier.run_all_checks()
    sys.exit(0 if verifier.failed == 0 else 1)
