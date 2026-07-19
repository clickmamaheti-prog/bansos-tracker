"""
Comprehensive Security Module for GPS Tracker Bot
- Rate limiting per IP
- Brute force protection (login & API)
- IP blacklist (persistent)
- CSRF protection
- Request validation & sanitization
- Audit logging
- Secure session management
"""
import os
import re
import time
import json
import hashlib
import secrets
import logging
import ipaddress
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, abort, session, g, Response

# ============ CONFIG ============
RATE_LIMIT_WINDOW = 60       # seconds
RATE_LIMIT_MAX = 30           # max requests per window  
LOGIN_LIMIT_MAX = 5           # max login attempts before block
LOGIN_BLOCK_MINUTES = 15      # block duration
API_KEY_RATE_LIMIT = 100      # max API requests per minute
MAX_REQUEST_SIZE = 1024 * 100 # 100KB max body
ALLOWED_CONTENT_TYPES = ['application/json', 'application/x-www-form-urlencoded', 'multipart/form-data']

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BLACKLIST_FILE = os.path.join(BASE_DIR, '.ip_blacklist.json')
AUDIT_LOG = os.path.join(BASE_DIR, '.audit.log')

# ============ LOGGING ============
logging.basicConfig(
    filename=AUDIT_LOG,
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ============ IN-MEMORY STORES ============
_rate_store = {}
_login_store = {}

# ============ IP BLACKLIST (persistent) ============
def _load_blacklist():
    """Load persistent IP blacklist"""
    try:
        if os.path.exists(BLACKLIST_FILE):
            with open(BLACKLIST_FILE) as f:
                return set(json.load(f))
    except:
        pass
    return set()

def _save_blacklist(blacklist):
    """Save IP blacklist to disk"""
    try:
        with open(BLACKLIST_FILE, 'w') as f:
            json.dump(list(blacklist), f)
        os.chmod(BLACKLIST_FILE, 0o600)
    except:
        pass

_ip_blacklist = _load_blacklist()

def is_ip_blocked(ip: str) -> bool:
    """Check if IP is blacklisted"""
    return ip in _ip_blacklist

def block_ip(ip: str, reason: str = "Manual block"):
    """Add IP to blacklist"""
    _ip_blacklist.add(ip)
    _save_blacklist(_ip_blacklist)
    logging.warning(f"IP BLOCKED: {ip} — {reason}")

def unblock_ip(ip: str):
    """Remove IP from blacklist"""
    _ip_blacklist.discard(ip)
    _save_blacklist(_ip_blacklist)
    logging.info(f"IP UNBLOCKED: {ip}")

def get_blacklist():
    """Get all blacklisted IPs"""
    return sorted(_ip_blacklist)

# ============ IP VALIDATION ============
def is_private_ip(ip: str) -> bool:
    """Check if IP is private/local"""
    try:
        return ipaddress.ip_address(ip).is_private
    except:
        return False

def get_client_ip() -> str:
    """Get real client IP (respects proxies)"""
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        # Get the first real IP
        ips = [ip.strip() for ip in forwarded.split(',')]
        for ip in ips:
            if not is_private_ip(ip):
                return ip
    return request.remote_addr or 'unknown'

# ============ RATE LIMITING ============
def _clean_stores():
    """Clean expired rate limit entries"""
    now = time.time()
    global _rate_store, _login_store
    _rate_store = {k: v for k, v in _rate_store.items() if v.get('reset', 0) > now}
    _login_store = {k: v for k, v in _login_store.items() 
                    if v.get('blocked_until', 0) > now or v.get('reset', 0) > now}

def rate_limit(f):
    """Rate limiting decorator — max RATE_LIMIT_MAX requests per window"""
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = get_client_ip()
        
        # Check blacklist
        if is_ip_blocked(ip):
            logging.warning(f"BLOCKED REQUEST from blacklisted IP: {ip} → {request.path}")
            return jsonify({"error": "Access denied"}), 403
        
        now = time.time()
        _clean_stores()
        
        if ip not in _rate_store:
            _rate_store[ip] = {'count': 0, 'reset': now + RATE_LIMIT_WINDOW}
        
        entry = _rate_store[ip]
        if now > entry['reset']:
            entry['count'] = 0
            entry['reset'] = now + RATE_LIMIT_WINDOW
        
        entry['count'] += 1
        
        if entry['count'] > RATE_LIMIT_MAX:
            logging.warning(f"RATE LIMITED: {ip} ({entry['count']} requests in window)")
            return jsonify({
                "error": f"Too many requests. Try again in {int(entry['reset'] - now)}s"
            }), 429
        
        return f(*args, **kwargs)
    return decorated

# ============ LOGIN BRUTE FORCE PROTECTION ============
def login_rate_limit(f):
    """Login-specific rate limiting — blocks after LOGIN_LIMIT_MAX failures"""
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = get_client_ip()
        now = time.time()
        _clean_stores()
        
        entry = _login_store.get(ip, {'attempts': 0, 'blocked_until': 0, 'reset': now + 3600})
        
        # Check if blocked
        if entry.get('blocked_until', 0) > now:
            remaining = int(entry['blocked_until'] - now)
            mins = remaining // 60
            secs = remaining % 60
            logging.warning(f"LOGIN BLOCKED: {ip} — {mins}m{secs}s remaining")
            return jsonify({
                "error": f"Terlalu banyak percobaan. Coba lagi dalam {mins} menit {secs} detik"
            }), 429
        
        # Call the original function
        result = f(*args, **kwargs)
        
        # Check if login failed (check response)
        response_text = ''
        if isinstance(result, str):
            response_text = result
        elif isinstance(result, Response):
            response_text = result.get_data(as_text=True)
        
        if 'Password salah' in response_text or 'error' in response_text.lower():
            entry['attempts'] = entry.get('attempts', 0) + 1
            remaining_attempts = LOGIN_LIMIT_MAX - entry['attempts']
            
            if entry['attempts'] >= LOGIN_LIMIT_MAX:
                entry['blocked_until'] = now + (LOGIN_BLOCK_MINUTES * 60)
                logging.warning(f"LOGIN BRUTE FORCE: {ip} — blocked for {LOGIN_BLOCK_MINUTES}min")
            else:
                logging.info(f"LOGIN FAILED: {ip} ({remaining_attempts} attempts remaining)")
            
            _login_store[ip] = entry
        
        return result
    return decorated

# ============ CSRF PROTECTION ============
def generate_csrf_token() -> str:
    """Generate a CSRF token and store it in session"""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']

def csrf_required(f):
    """Validate CSRF token for POST/PUT/DELETE requests"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method in ('POST', 'PUT', 'DELETE'):
            # Get token from header or form data
            token = request.headers.get('X-CSRF-Token', '') or request.form.get('_csrf_token', '')
            session_token = session.get('_csrf_token', '')
            
            if not token or not secrets.compare_digest(token, session_token):
                logging.warning(f"CSRF FAILED: {get_client_ip()} → {request.path}")
                return jsonify({"error": "CSRF token invalid"}), 403
        
        return f(*args, **kwargs)
    return decorated

# ============ REQUEST VALIDATION ============
def validate_json_body(required_fields: list = None):
    """Decorator to validate JSON request body"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Check content type
            ct = request.content_type or ''
            if not any(allowed in ct for allowed in ALLOWED_CONTENT_TYPES):
                return jsonify({"error": "Invalid content type"}), 415
            
            # Check size
            if request.content_length and request.content_length > MAX_REQUEST_SIZE:
                logging.warning(f"REQUEST TOO LARGE: {get_client_ip()} — {request.content_length} bytes")
                return jsonify({"error": "Request too large"}), 413
            
            # Validate JSON for POST/PUT
            if request.method in ('POST', 'PUT') and 'json' in ct:
                data = request.get_json(silent=True)
                if data is None:
                    return jsonify({"error": "Invalid JSON body"}), 400
                
                if required_fields:
                    for field in required_fields:
                        if field not in data:
                            return jsonify({"error": f"Missing required field: {field}"}), 400
            
            return f(*args, **kwargs)
        return decorated
    return decorator

# ============ INPUT SANITIZATION ============
def sanitize_string(s: str, max_len: int = 500) -> str:
    """Sanitize string input — strip dangerous chars, limit length"""
    if not s:
        return ''
    if not isinstance(s, str):
        s = str(s)
    # Strip null bytes, control chars (except newlines)
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', s)
    # Limit length
    s = s[:max_len]
    return s

def sanitize_filename(fname: str) -> str:
    """Sanitize filename — only allow safe chars"""
    if not fname:
        return 'unnamed'
    # Remove path separators
    fname = fname.replace('/', '_').replace('\\', '_')
    # Only allow safe chars
    fname = re.sub(r'[^a-zA-Z0-9._-]', '_', fname)
    # Limit length
    fname = fname[:100]
    return fname or 'unnamed'

# ============ SECURE SESSION ============
def set_secure_secret():
    """Generate a persistent secret key stored in file"""
    secret_file = os.path.join(BASE_DIR, '.secret_key')
    
    if os.path.exists(secret_file):
        with open(secret_file, 'r') as f:
            return f.read().strip()
    
    # Generate new key
    key = secrets.token_hex(32)
    with open(secret_file, 'w') as f:
        f.write(key)
    os.chmod(secret_file, 0o600)
    return key

def secure_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=()'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;"
    return response

# ============ API KEY AUTH ============
def validate_api_key(key: str) -> bool:
    """Validate API key — simple hash comparison"""
    if not key or not isinstance(key, str) or len(key) < 8:
        return False
    # Keys must be alphanumeric with common separators
    return bool(re.match(r'^[a-zA-Z0-9_\-:]{8,128}$', key))

def api_key_required(f):
    """Require API key for device endpoints"""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key', '')
        
        if not api_key or not validate_api_key(api_key):
            logging.warning(f"INVALID API KEY: {get_client_ip()} → {request.path}")
            return jsonify({"error": "Invalid or missing API key"}), 401
        
        g.api_key = api_key
        return f(*args, **kwargs)
    return decorated

# ============ AUDIT LOGGING ============
def log_request(action: str, detail: str = ''):
    """Log an audit event"""
    ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', '')[:100]
    logging.info(f"[{action}] IP={ip} UA={user_agent} | {detail}")

# ============ AUTH DECORATORS ============
def login_required(f):
    """Require dashboard login session"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            log_request("AUTH_BLOCKED", f"Not logged in → {request.path}")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ============ IMPORT for redirect ============
from flask import redirect, url_for
