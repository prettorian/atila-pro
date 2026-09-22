#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ATILA PRO 7.7 - SUPREME EDITION
(Motor completo 7.5 validado + Historial y Estadísticas [21])
SOLO PARA USO ÉTICO Y AUTORIZADO
"""

import os
import sys
import socket
import shutil
import subprocess
import json
import glob
import csv
import logging
import requests
import re
import time
import textwrap
import ipaddress
import base64
import hashlib
import hmac
import datetime
from collections import Counter
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

G = '\033[92m'
Y = '\033[93m'
B = '\033[94m'
M = '\033[95m'
C = '\033[96m'
R = '\033[91m'
W = '\033[97m'
E = '\033[0m'
D = '\033[2m'

ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')

# ============================================================
# Licencia / keys (insertado por upgrade_77.py)
# ============================================================
LICENSE_SECRET = "mis perros se llaman toti y pili"

LICENSE_FILE = os.path.join(os.path.expanduser('~'), '.atila', 'license.json')

FUNDADORES = [
    # "alias_fundador_1",
]

def _lic_sign(payload):
    return hmac.new(LICENSE_SECRET.encode(), payload.encode(),
                    hashlib.sha256).hexdigest()[:16]

def verify_license_key(key):
    partes = key.split('.')
    if len(partes) != 5 or partes[0] != 'ATILA' or partes[1] != 'PRO':
        return None
    tier = partes[2]
    token = partes[3]
    sig = partes[4]
    try:
        payload = base64.urlsafe_b64decode(token.encode()).decode()
    except Exception:
        return None
    if not hmac.compare_digest(_lic_sign(payload), sig):
        return None
    try:
        data = json.loads(payload)
    except Exception:
        return None
    exp = data.get('exp', '')
    try:
        expirada = datetime.date.fromisoformat(exp) < datetime.date.today()
    except Exception:
        expirada = True
    return {'alias': data.get('alias', ''), 'tier': tier,
            'exp': exp, 'expirada': expirada}

def load_license_state():
    try:
        with open(LICENSE_FILE) as f:
            lic = json.load(f)
        key = lic.get('key', '')
    except Exception:
        return {'estado': 'LIBRE'}
    info = verify_license_key(key)
    if info is None:
        return {'estado': 'LIBRE'}
    if info['expirada']:
        out = dict(info)
        out['estado'] = 'EXPIRADA'
        return out
    out = dict(info)
    out['estado'] = 'FUNDADOR' if info['tier'] == 'FOUNDER' else 'PRO'
    return out

def activate_license(key):
    info = verify_license_key(key)
    if info is None:
        return False, 'Key invalida (la firma no coincide).'
    if info['expirada']:
        return False, 'Key expirada el ' + info['exp'] + '.'
    os.makedirs(os.path.dirname(LICENSE_FILE), exist_ok=True)
    with open(LICENSE_FILE, 'w') as f:
        json.dump({'key': key}, f)
    tier_txt = 'Socio Fundador' if info['tier'] == 'FOUNDER' else 'PRO'
    return True, ('Activada para ' + info['alias'] + ' (' + tier_txt +
                  ') hasta ' + info['exp'])

CONFIG_DEFAULTS = {
    'workers_e1': 120,
    'workers_e2': 20,
    'tcp_timeout': 0.3,
    'tijera_default': 16,
    'modo_default': '1',
    'asn_favorito': '',
    'ruta_favorita': '',
    'export_auto': False,
}

def config_path():
    return os.path.join(os.path.expanduser('~'), '.atila', 'config.json')

def load_config():
    cfg = dict(CONFIG_DEFAULTS)
    try:
        with open(config_path()) as f:
            data = json.load(f)
        for k in CONFIG_DEFAULTS:
            if k in data:
                cfg[k] = data[k]
    except Exception:
        pass
    return cfg

def save_config(cfg):
    os.makedirs(os.path.dirname(config_path()), exist_ok=True)
    with open(config_path(), 'w') as f:
        json.dump(cfg, f, indent=2)

def term_cols():
    try:
        return max(40, shutil.get_terminal_size((80, 24)).columns)
    except Exception:
        return 80

def vlen(s):
    return len(ANSI_RE.sub('', s))

def fit(text, width):
    if width <= 0:
        return ''
    if len(text) <= width:
        return text
    if width == 1:
        return '…'
    return text[:width - 1] + '…'

def cfit(s, width):
    if vlen(s) <= width:
        return s
    out = []
    vis = 0
    i = 0
    limit = max(0, width - 1)
    while i < len(s):
        m = ANSI_RE.match(s, i)
        if m:
            out.append(m.group(0))
            i = m.end()
            continue
        if vis >= limit:
            break
        out.append(s[i])
        vis += 1
        i += 1
    out.append('…')
    return ''.join(out) + E

def cpad(s, width):
    return s + ' ' * max(0, width - vlen(s))

def pwrap(color, text, indent=0):
    cols = term_cols()
    pre = ' ' * indent
    chunks = textwrap.wrap(text, width=max(20, cols - 2 - indent)) or ['']
    for chunk in chunks:
        print(color + pre + chunk + E)

MENU_ITEMS = [
    ('01', 'Single Host', 'HTTP/HTTPS Probe'),
    ('02', 'Browse & Scan', 'Load .txt host list'),
    ('03', 'Quick Test', '10 popular sites'),
    ('04', 'CIDR Scan', 'IP range scanner'),
    ('05', 'Subdomain Enum', '3 sources search'),
    ('06', 'Reverse IP', 'Find domains on IP'),
    ('07', 'Domain Extractor', 'Extract from text/file'),
    ('08', 'Proxy Relay', 'Auto-detect proxies'),
    ('09', 'Trick Lab', 'Vulnerability checks'),
    ('10', 'H2 Detector', 'HTTP/2 capability check'),
    ('11', 'Mobile Proxy Scan', '★ Core: 2 etapas + rango x rango'),
    ('12', 'Update ATILA', '★ Auto-update from Gist'),
    ('13', 'Install Command', "★ 'atila' en $PREFIX/bin"),
    ('14', 'Carrier ASN Hunt', '★ ASN del chip + lista completa'),
    ('15', 'MacGyver Pack AR', '★ Rangos AR sin internet'),
    ('16', 'Fresh Pools AR', '★ Operadoras AR frescas'),
    ('17', 'Fresh Cloud Pack', '★ CDN/clouds del mundo'),
    ('18', 'Vivos Lab', '★ Laboratorio de hosts vivos'),
    ('19', 'Ver Bitácora', '★ Leer el log de actividad'),
    ('20', 'Configuración', '★ Preferencias persistentes'),
    ('21', 'Historial', '★ Biblioteca y estadísticas'),
    ('22', 'Licencia', '★ Estado, activar y créditos'),
    ('00', 'Exit', 'Salir de ATILA'),
]

def draw_menu():
    cols = term_cols()
    now = time.strftime('%H:%M')
    tmux_tag = ' · tmux ✓' if os.environ.get('TMUX') else ''
    print(B + '╭' + '─' * (cols - 2) + '╮' + E)
    title = G + 'MAIN MENU' + E
    left = (cols - 2 - 9) // 2
    print(B + '│' + E + ' ' * left + title + ' ' * max(1, cols - 2 - 9 - left) + B + '│' + E)
    print(B + '├' + '─' * (cols - 2) + '┤' + E)
    info = D + 'v7.7 · ' + now + ' · ' + str(cols) + ' col' + tmux_tag + ' · uso ético' + E
    print(B + '│' + E + ' ' + cfit(info, cols - 3) + ' ' * max(0, cols - 3 - vlen(info)) + B + '│' + E)
    print(B + '├' + '─' * (cols - 2) + '┤' + E)
    for key, name, desc in MENU_ITEMS:
        if key in ('11', '18', '00'):
            print(B + '├' + '─' * (cols - 2) + '┤' + E)
        tag = (R if key == '00' else G) + '[' + key + ']' + E + ' ' + (R if key == '00' else W) + name + E
        if cols >= 58:
            line = ' ' + cpad(tag, 26) + ' ' + (Y if desc.startswith('★') else C) + fit(desc, max(8, cols - 30)) + E
            vis = vlen(line)
            print(B + '│' + E + cfit(line, cols - 3) + ' ' * max(0, cols - 3 - vis) + B + '│' + E)
        else:
            print(B + '│' + E + ' ' + cfit(tag, cols - 3) + ' ' * max(0, cols - 3 - vlen(tag)) + B + '│' + E)
            dline = '     ' + D + fit(desc, cols - 7) + E
            print(B + '│' + E + cfit(dline, cols - 3) + ' ' * max(0, cols - 3 - vlen(dline)) + B + '│' + E)
    print(B + '╰' + '─' * (cols - 2) + '╯' + E)
    print(D + fit(' Ctrl+C cancela · 00 sale · config y log en ~/.atila/', cols) + E)

MARKERS = [
    ("example.com", 80, "/", ["Example Domain"]),
    ("iana.org", 80, "/", ["IANA", "Internet Assigned Numbers"]),
    ("httpbin.org", 80, "/get", ["httpbin", "origin"]),
]

CARRIERS_AR = {
    '1': {
        'name': 'PERSONAL (Telecom Argentina)',
        'slug': 'personal',
        'asns': ['7303'],
        'ranges': ['181.96.0.0/12', '181.0.0.0/12', '190.30.0.0/16', '190.55.0.0/16',
                   '181.106.0.0/16', '200.43.0.0/16', '200.45.0.0/16', '190.19.0.0/16']
    },
    '2': {
        'name': 'CLARO (AMX Argentina S.A.)',
        'slug': 'claro',
        'asns': ['19037'],
        'ranges': ['181.16.0.0/14', '181.20.0.0/14', '181.24.0.0/14', '181.94.0.0/15',
                   '181.104.0.0/16', '181.105.0.0/16', '190.18.0.0/16', '201.212.0.0/14',
                   '201.216.0.0/14', '201.220.0.0/14', '201.224.0.0/13', '152.168.0.0/16']
    },
    '3': {
        'name': 'MOVISTAR (Telefónica Argentina)',
        'slug': 'movistar',
        'asns': ['22927', '262175'],
        'ranges': ['190.244.0.0/14', '190.248.0.0/14', '201.251.0.0/16', '181.30.0.0/15',
                   '181.44.0.0/14', '181.46.0.0/15', '190.173.0.0/16', '190.187.0.0/16',
                   '190.246.0.0/16']
    },
}

PROVIDERS_WORLD = {
    '1':  {'name': 'CLOUDFLARE', 'slug': 'cloudflare', 'asns': ['13335']},
    '2':  {'name': 'DIGITALOCEAN', 'slug': 'digitalocean', 'asns': ['14061']},
    '3':  {'name': 'IMPERVA/INCAPSULA', 'slug': 'imperva', 'asns': ['19551']},
    '4':  {'name': 'G-CORE LABS', 'slug': 'gcore', 'asns': ['199524']},
    '5':  {'name': 'AMAZON AWS', 'slug': 'aws', 'asns': ['16509']},
    '6':  {'name': 'GOOGLE CLOUD', 'slug': 'google', 'asns': ['15169']},
    '7':  {'name': 'MICROSOFT AZURE', 'slug': 'azure', 'asns': ['8075']},
    '8':  {'name': 'AKAMAI', 'slug': 'akamai', 'asns': ['20940']},
    '9':  {'name': 'FASTLY', 'slug': 'fastly', 'asns': ['54113']},
    '10': {'name': 'HETZNER', 'slug': 'hetzner', 'asns': ['24940']},
    '11': {'name': 'VULTR', 'slug': 'vultr', 'asns': ['20473']},
    '12': {'name': 'OVH', 'slug': 'ovh', 'asns': ['16276']},
}

SUBS = ['www', 'mail', 'ftp', 'admin', 'webmail', 'test', 'dev', 'api', 'blog', 'shop', 'app',
        'mobile', 'beta', 'stage', 'prod', 'demo', 'cms', 'wp', 'portal', 'login', 'auth', 'vpn',
        'remote', 'git', 'jenkins', 'db', 'mysql', 'redis', 'mongo', 'elastic', 'cdn', 'static',
        'assets', 'media', 'docs', 'help', 'support', 'status', 'ns1', 'ns2', 'dns', 'mx', 'smtp',
        'backup', 'old', 'new', 'v2', 'v3', 'proxy', 'gateway', 'server', 'cache']

PATHS = ['/admin', '/login', '/wp-admin', '/wp-login.php', '/phpmyadmin', '/.env', '/config.php',
         '/.git', '/.git/config', '/api', '/api/v1', '/api/v2', '/graphql', '/swagger',
         '/swagger-ui', '/docs', '/server-status', '/phpinfo.php', '/info.php', '/wp-config.php',
         '/.htaccess', '/administrator', '/console', '/jenkins', '/actuator', '/actuator/health',
         '/metrics', '/debug', '/trace', '/backup', '/backup.sql', '/database.sql']

class ATILA:
    def __init__(self):
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self.stats = {'positive': 0, 'negative': 0, 'total': 0, 'alive': 0}
        self.lock = threading.Lock()
        self.cfg = load_config()
        self.lic = load_license_state()
        log_dir = os.path.join(os.path.expanduser('~'), '.atila')
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, 'atila.log')
        logging.basicConfig(filename=self.log_file, level=logging.INFO,
                            format='[%(asctime)s] [%(levelname)s] %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')
        self.logger = logging.getLogger('atila')
        self.logger.info("Sesión de ATILA PRO 7.7 iniciada")

    def banner(self):
        os.system('clear')
        cols = term_cols()
        if cols >= 56:
            print(C)
            print("██╗  ██╗██╗  ██╗ ██████╗██╗  ██╗███████╗██████╗")
            print("██║  ██║██║  ██║██╔════╝██║ ██╔╝██════╝██╔══██╗")
            print("███████║███████║██║     █████╔╝ █████╗  ██████╔╝")
            print("██╔══██║╚════██║██║     ██╔═██╗ ██╔══╝  ██╔══██╗")
            print("██║  ██║     ██║╚██████╗██║  ██╗███████╗██║  ██║")
            print("╚═╝  ╚═╝     ╚═╝ ═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝")
            print(E, end='')
            print(Y + "        ATILA PRO 7.7 - SUPREME EDITION")
            print(R + "  " + "=" * 39)
            print("  SOLO USO ÉTICO Y AUTORIZADO" + E)
        else:
            print(C + '┌' + '─' * (cols - 2) + '┐' + E)
            print(C + '│' + E + cpad(G + ' ATILA PRO 7.7', cols - 2) + C + '│' + E)
            print(C + '│' + E + cpad(Y + ' SUPREME EDITION', cols - 2) + C + '│' + E)
            print(C + '│' + E + cpad(R + ' SOLO USO ÉTICO Y AUTORIZADO', cols - 2) + C + '│' + E)
            print(C + '└' + '─' * (cols - 2) + '┘' + E)
        print()
        estado = self.lic.get('estado', 'LIBRE')
        if estado == 'PRO':
            print(G + "  Licencia: PRO · " + self.lic.get('alias', '') +
                  " · exp " + self.lic.get('exp', '') + E)
        elif estado == 'FUNDADOR':
            print(M + "  Licencia: SOCIO FUNDADOR · " + self.lic.get('alias', '') +
                  " · creditos permanentes" + E)
        elif estado == 'EXPIRADA':
            print(R + "  Licencia: EXPIRADA el " + self.lic.get('exp', '') +
                  " · renová tu key" + E)
        else:
            print(D + "  Licencia: LIBRE (uso personal/educativo) · key opcional [22]" + E)
        print()
        for chunk in textwrap.wrap('Scanner 2 etapas · ASN Hunt · Vivos Lab · Export · Log · Config · Historial', cols - 2):
            print(G + chunk + E)
        print()

    def licencia_menu(self):
        print(B + "\n[•] ATILA: Licencia y Creditos" + E)
        while True:
            estado = self.lic.get('estado', 'LIBRE')
            print()
            print(Y + "    Estado actual: " + E + W + estado + E)
            if estado in ('PRO', 'FUNDADOR', 'EXPIRADA'):
                print(D + "    alias=" + self.lic.get('alias', '') +
                      " · tier=" + self.lic.get('tier', '') +
                      " · exp=" + self.lic.get('exp', '') + E)
            print(G + "    [1]" + E + " Activar / ingresar una key")
            print(G + "    [2]" + E + " Ver creditos del proyecto")
            print(G + "    [0]" + E + " Volver")
            opt = input(G + "    > Opcion: " + E).strip()
            if opt == '0':
                return
            elif opt == '1':
                key = input(G + "    Pega tu key: " + E).strip()
                if not key:
                    print(Y + "[*] Sin key, no se activa nada." + E)
                    continue
                ok, msg = activate_license(key)
                if ok:
                    self.lic = load_license_state()
                    self.logger.info("Licencia activada: " + msg)
                    print(G + "[✓] " + msg + E)
                else:
                    self.logger.warning("Intento de activacion fallido: " + msg)
                    print(R + "[✗] " + msg + E)
            elif opt == '2':
                cols = term_cols()
                print()
                print(C + '═' * cols + E)
                print(G + "  🏅 CREDITOS DE ATILA PRO" + E)
                print(C + '═' * cols + E)
                print("  " + Y + "Autor y mantenimiento:" + E + " TheFlaggg (@TheFlaggg)")
                print("  " + Y + "Co-diseno y arquitectura:" + E + " McGyver-Pro (IA), desde la v2.5")
                print("  " + Y + "Socios Fundadores:" + E)
                if FUNDADORES:
                    for f in FUNDADORES:
                        print("    " + M + "★ " + f + E)
                else:
                    print("    " + D + "(aun ninguno: se el primero con una key Fundador)" + E)
                print(C + '═' * cols + E)
            else:
                print(R + "[-] Opcion invalida." + E)

    def http_json(self, url, timeout=20):
        try:
            r = requests.get(url, timeout=timeout, headers={'User-Agent': self.ua})
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        try:
            p = subprocess.run(['curl', '-s', '--max-time', str(timeout), url],
                               capture_output=True, text=True)
            if p.returncode == 0 and p.stdout.strip():
                print(D + "[i] requests no respondió; usando curl del sistema como respaldo." + E)
                return json.loads(p.stdout)
        except Exception:
            pass
        self.logger.warning("Fallo de conexión HTTP/JSON para " + url)
        return None

    def _resolve_target(self, target):
        try:
            ipaddress.ip_address(target)
            return target
        except ValueError:
            try:
                if target.startswith('http://') or target.startswith('https://'):
                    target = urlparse(target).netloc
                return socket.gethostbyname(target)
            except:
                return None

    def _check_internet_connection(self):
        for server, port in [('8.8.8.8', 53), ('1.1.1.1', 53), ('208.67.222.222', 53)]:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                result = s.connect_ex((server, port))
                s.close()
                if result == 0:
                    return True
            except:
                continue
        return False

    def fetch_prefixes(self, asn):
        data = self.http_json('https://ip.guide/AS' + asn, timeout=30)
        if data:
            v4 = data.get('routes', {}).get('v4', [])
            if v4:
                self.logger.info("Prefijos AS" + asn + " vía ip.guide: " + str(len(v4)))
                return v4, 'ip.guide'
        data = self.http_json('https://api.bgpview.io/asn/' + asn + '/prefixes')
        if data:
            v4 = [p['prefix'] for p in data.get('data', {}).get('ipv4_prefixes', []) if p.get('prefix')]
            if v4:
                self.logger.info("Prefijos AS" + asn + " vía bgpview: " + str(len(v4)))
                return v4, 'bgpview.io'
        data = self.http_json('https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS' + asn)
        if data:
            v4 = [p['prefix'] for p in data.get('data', {}).get('prefixes', [])
                  if p.get('prefix') and ':' not in p['prefix']]
            if v4:
                self.logger.info("Prefijos AS" + asn + " vía RIPEstat: " + str(len(v4)))
                return v4, 'RIPEstat'
        self.logger.error("Sin prefijos para AS" + asn)
        return [], ''

    def export_results(self, datos, filepath, tipo='proxies'):
        resultados_dir = os.path.join(os.path.dirname(os.path.abspath(filepath)), 'resultados')
        os.makedirs(resultados_dir, exist_ok=True)
        stamp = time.strftime('%Y%m%d_%H%M%S')
        base = os.path.join(resultados_dir, tipo + '_export_' + stamp)
        creados = []
        rows = []
        for d in datos:
            if isinstance(d, dict):
                rows.append({'ip': str(d.get('ip', '')), 'port': str(d.get('port', '')),
                             'detalle': str(d.get('message', ''))})
            else:
                rows.append({'ip': str(d), 'port': '', 'detalle': ''})
        try:
            with open(base + '.json', 'w') as f:
                json.dump({'herramienta': 'ATILA PRO 7.7', 'tipo': tipo,
                           'generado': time.strftime('%Y-%m-%d %H:%M:%S'),
                           'total': len(rows), 'items': rows}, f, indent=2)
            creados.append(base + '.json')
        except Exception as e:
            self.logger.error("Error exportando JSON: " + str(e))
        try:
            with open(base + '.csv', 'w', newline='') as f:
                w = csv.DictWriter(f, fieldnames=['ip', 'port', 'detalle'])
                w.writeheader()
                for r in rows:
                    w.writerow(r)
            creados.append(base + '.csv')
        except Exception as e:
            self.logger.error("Error exportando CSV: " + str(e))
        try:
            h = ['<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">',
                 '<meta name="viewport" content="width=device-width, initial-scale=1">',
                 '<title>ATILA PRO 7.7 - Reporte ' + tipo + '</title>',
                 '<style>body{font-family:monospace;background:#0d1117;color:#c9d1d9;padding:16px}',
                 'h1{color:#58a6ff}h2{color:#7ee787}table{border-collapse:collapse;width:100%}',
                 'td,th{border:1px solid #30363d;padding:6px 10px;text-align:left}',
                 'th{background:#161b22;color:#7ee787}.meta{color:#8b949e}</style></head><body>',
                 '<h1>📡 ATILA PRO 7.7</h1>',
                 '<h2>Reporte: ' + tipo + ' (' + str(len(rows)) + ' items)</h2>',
                 '<p class="meta">Generado: ' + time.strftime('%Y-%m-%d %H:%M:%S') + '</p>',
                 '<table><tr><th>#</th><th>IP</th><th>Puerto</th><th>Detalle</th></tr>']
            for i, r in enumerate(rows, 1):
                h.append('<tr><td>' + str(i) + '</td><td>' + r['ip'] + '</td><td>' + r['port'] +
                         '</td><td>' + r['detalle'] + '</td></tr>')
            h.append('</table></body></html>')
            with open(base + '.html', 'w') as f:
                f.write('\n'.join(h))
            creados.append(base + '.html')
        except Exception as e:
            self.logger.error("Error exportando HTML: " + str(e))
        if creados:
            self.logger.info("Exportación '" + tipo + "': " + str(len(creados)) + " archivos")
        return creados

    def render_bar(self, processed, total, start_time, label=''):
        cols = term_cols()
        width = max(8, min(24, (cols - 46) // 2))
        pct = int(processed * 100 / total) if total else 0
        filled = int(width * processed / total) if total else 0
        bar = G + '#' * filled + D + '-' * (width - filled) + E
        elapsed = max(time.time() - start_time, 0.001)
        speed = processed / elapsed
        eta = (total - processed) / speed if speed > 0 else 0
        eta_int = int(eta)
        eta_txt = time.strftime('%H:%M:%S', time.gmtime(eta_int)) if eta_int > 3600 else time.strftime('%M:%S', time.gmtime(eta_int))
        line = (D + label + ' ' + E + C + '[' + bar + C + '] ' + E +
                Y + str(pct).rjust(3) + '% ' + E +
                W + str(processed) + '/' + str(total) + E +
                ' | ' + G + '✓' + str(self.stats['positive']) + E +
                ' ' + C + '●' + str(self.stats['alive']) + E +
                ' ' + R + '✗' + str(self.stats['negative']) + E +
                ' | ' + C + ('%.1f' % speed) + ' ip/s' + E +
                ' | ETA ' + eta_txt + '   ')
        out = cfit(line, cols - 1)
        sys.stdout.write('\r' + out + ' ' * max(0, (cols - 1) - vlen(out)))
        sys.stdout.flush()

    def save_results(self, positive_ips, filepath, partial=False):
        resultados_dir = os.path.join(os.path.dirname(os.path.abspath(filepath)), 'resultados')
        os.makedirs(resultados_dir, exist_ok=True)
        output_file = os.path.join(resultados_dir, 'proxies_' + time.strftime('%Y%m%d_%H%M%S') + '.txt')
        with open(output_file, 'w') as f:
            f.write("# ATILA PRO 7.7 - Proxies Encontrados\n")
            f.write("# Fecha: " + time.strftime('%Y-%m-%d %H:%M:%S') + "\n")
            f.write("# Archivo fuente: " + filepath + "\n")
            f.write("# Total encontrados: " + str(len(positive_ips)) + "\n")
            if partial:
                f.write("# NOTA: Escaneo detenido antes de terminar - resultados PARCIALES\n")
            f.write("\n")
            for proxy in positive_ips:
                f.write(proxy['ip'] + ":" + str(proxy['port']) + "\n")
        self.logger.info("Proxies guardados: " + os.path.basename(output_file) +
                         " (" + str(len(positive_ips)) + ")")
        return output_file

    def single_host(self, target):
        print(B + "\n[•] ATILA: HTTP/HTTPS Probe - " + target + E)
        if not target.startswith('http://') and not target.startswith('https://'):
            target = 'https://' + target
        tried = False
        for proto in ['https', 'http']:
            try:
                url = proto + "://" + urlparse(target).netloc
                r = requests.get(url, timeout=10, verify=False, headers={'User-Agent': self.ua})
                print(G + "[+] " + url + " → " + str(r.status_code) + E)
                print("    " + Y + "Server:" + E + " " + r.headers.get('Server', 'N/A'))
                title = re.search(r'<title>(.*?)</title>', r.text, re.I)
                if title:
                    print("    " + Y + "Title:" + E + " " + fit(title.group(1), term_cols() - 12))
                tried = True
                break
            except:
                continue
        if not tried:
            print(R + "[-] No se pudo conectar al target" + E)

    def browse_scan(self, filepath):
        print(B + "\n[•] ATILA: Load host list - " + filepath + E)
        try:
            if not os.path.exists(filepath):
                print(R + "[-] Archivo no encontrado: " + filepath + E)
                return
            with open(filepath, 'r') as f:
                hosts = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            if not hosts:
                print(R + "[-] Archivo vacío o sin hosts válidos" + E)
                return
            total = len(hosts)
            print(Y + "[*] " + str(total) + " hosts cargados" + E)
            for i, host in enumerate(hosts, 1):
                print(D + "[" + str(i) + "/" + str(total) + "]" + E + " ", end='')
                self.single_host(host)
        except Exception as err:
            print(R + "[-] Error: " + str(err) + E)

    def quick_test(self):
        print(B + "\n[•] ATILA: Quick Test - 10 popular sites" + E)
        sites = ['google.com', 'facebook.com', 'youtube.com', 'twitter.com',
                 'instagram.com', 'linkedin.com', 'github.com', 'reddit.com',
                 'stackoverflow.com', 'amazon.com']
        for site in sites:
            try:
                r = requests.get("https://" + site, timeout=5, verify=False, headers={'User-Agent': self.ua})
                print(G + "[+] " + site + " → " + str(r.status_code) + E)
            except:
                print(R + "[-] " + site + " → OFFLINE" + E)

    def cidr_scan(self, cidr):
        print(B + "\n[•] ATILA: CIDR Scan - " + cidr + E)
        try:
            network = ipaddress.ip_network(cidr, strict=False)
            hosts = list(network.hosts())[:256]
            print(Y + "[*] Escaneando " + str(len(hosts)) + " IPs..." + E)
            found = []
            def check_port(ip):
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.3)
                    result = s.connect_ex((str(ip), 80))
                    s.close()
                    if result == 0:
                        print(G + "[+] " + str(ip) + ":80 OPEN" + E)
                        found.append(str(ip))
                except:
                    pass
            with ThreadPoolExecutor(max_workers=100) as executor:
                executor.map(check_port, hosts)
            print("\n" + C + "[★] Hosts activos encontrados: " + str(len(found)) + E)
        except ValueError as ve:
            print(R + "[-] CIDR inválido: " + str(ve) + E)
        except Exception as err:
            print(R + "[-] Error: " + str(err) + E)

    def subdomain_enum(self, domain):
        print(B + "\n[•] ATILA: Subdomain Enum - " + domain + E)
        print(Y + "[*] Usando wordlist + crt.sh + Wayback..." + E)
        found = set()
        print(D + "[1/3]" + E + " Wordlist local...")
        def check_sub(sub):
            try:
                full = sub + "." + domain
                socket.gethostbyname(full)
                found.add(full)
                print(G + "  + " + full + E)
            except:
                pass
        with ThreadPoolExecutor(max_workers=50) as executor:
            executor.map(check_sub, SUBS)
        count1 = len([f for f in found if any(f.startswith(s + ".") for s in SUBS)])
        print("    " + G + "✓ " + str(count1) + " encontrados" + E)
        print(D + "[2/3]" + E + " crt.sh (certificados SSL)...")
        try:
            r = requests.get("https://crt.sh/?q=%25." + domain + "&output=json", timeout=15)
            if r.status_code == 200:
                for entry in r.json():
                    for name in entry.get('name_value', '').split('\n'):
                        name = name.strip().lower()
                        if name.endswith(domain) and '*' not in name:
                            found.add(name)
                            print(G + "  + " + name + E)
                print("    " + G + "✓ Total: " + str(len(found)) + E)
        except:
            print("    " + R + "✗ Error de conexión" + E)
        print(D + "[3/3]" + E + " Wayback Machine...")
        try:
            r = requests.get("http://web.archive.org/cdx/search/cdx?url=*." + domain + "/*&output=json&fl=original", timeout=15)
            if r.status_code == 200:
                for url in [u[0] for u in r.json()[1:]]:
                    try:
                        host = urlparse(url).hostname
                        if host and host.endswith(domain):
                            found.add(host)
                            print(G + "  + " + host + E)
                    except:
                        pass
                print("    " + G + "✓ Total: " + str(len(found)) + E)
        except:
            print("    " + R + "✗ Error de conexión" + E)
        if found:
            print("\n" + C + "[★] Subdominios encontrados (" + str(len(found)) + "):" + E)
            for sub in sorted(found):
                print("  " + G + "→ " + sub + E)
        else:
            print(Y + "[!] No se encontraron subdominios" + E)
        return found

    def reverse_ip(self, target):
        print(B + "\n[•] ATILA: Reverse IP - " + target + E)
        try:
            ip = self._resolve_target(target)
            if not ip:
                print(R + "[-] No se pudo resolver: " + target + E)
                return
            print(G + "[+] IP objetivo: " + ip + E)
            found = set()
            try:
                r = requests.get("https://api.hackertarget.com/reverseiplookup/?q=" + ip, timeout=10)
                if r.status_code == 200 and 'error' not in r.text.lower():
                    for line in r.text.strip().split('\n'):
                        line = line.strip()
                        if line and '.' in line:
                            found.add(line)
                            print(G + "  + " + line + E)
            except:
                pass
            if found:
                print("\n" + C + "[★] Dominios en " + ip + " (" + str(len(found)) + "):" + E)
                for d in sorted(found):
                    print("  " + G + "→ " + d + E)
            else:
                print(Y + "[!] No se encontraron dominios compartidos" + E)
        except Exception as err:
            print(R + "[-] Error: " + str(err) + E)

    def domain_extractor(self, text_or_file):
        print(B + "\n[•] ATILA: Domain Extractor" + E)
        try:
            if os.path.exists(text_or_file):
                with open(text_or_file, 'r') as f:
                    content = f.read()
            else:
                content = text_or_file
            pattern = r'[a-zA-Z0-9]+(\.[a-zA-Z]{2,})+'
            domains = set()
            for match in re.findall(pattern, content):
                domain = (match[0] + match[1]) if isinstance(match, tuple) else match
                domain = domain.lower()
                if len(domain) > 3:
                    domains.add(domain)
            if domains:
                print("\n" + C + "[★] Dominios extraídos (" + str(len(domains)) + "):" + E)
                for d in sorted(domains):
                    print("  " + G + "→ " + d + E)
            else:
                print(Y + "[!] No se encontraron dominios válidos" + E)
            return domains
        except Exception as err:
            print(R + "[-] Error: " + str(err) + E)
            return set()

    def proxy_relay(self):
        print(B + "\n[•] ATILA: Proxy Relay - Auto Detect" + E)
        proxies = []
        sources = [("SSLProxy", "https://www.sslproxies.org/"), ("US-Proxy", "https://www.us-proxy.org/")]
        for name, url in sources:
            print(D + "[•]" + E + " " + name + "...")
            try:
                r = requests.get(url, timeout=10, headers={'User-Agent': self.ua})
                if r.status_code == 200:
                    ips = re.findall(r'<td>(\d+\.\d+\.\d+\.\d+)</td>', r.text)
                    ports = re.findall(r'</td>\s*<td>(\d+)</td>', r.text)
                    for ip_addr, port in zip(ips[:5], ports[:5]):
                        print(G + "  ✓ " + ip_addr + ":" + port + E)
                        proxies.append(ip_addr + ":" + port)
            except:
                print(R + "  ✗ Error de conexión" + E)
        if proxies:
            print("\n" + C + "[★] Proxies encontrados: " + str(len(proxies)) + E)
        else:
            print(Y + "[!] No se pudieron obtener proxies" + E)
        return proxies

    def trick_lab(self, target):
        print(B + "\n[•] ATILA: Trick Lab - Vulnerability Checks" + E)
        if not target.startswith('http://') and not target.startswith('https://'):
            target = 'https://' + target
        results = []
        tests = [("Open Redirect", self._check_redirect, target),
                 ("XSS Reflected", self._check_xss, target),
                 ("SQLi Basic", self._check_sqli, target),
                 ("Info Disclosure", self._check_info, target)]
        for name, func, url in tests:
            print(D + "[•]" + E + " Testing " + fit(name, term_cols() - 20) + "... ", end='')
            try:
                result = func(url)
                if result:
                    print(R + "[!] VULNERABLE" + E)
                    pwrap(Y, "    → " + result, 0)
                    results.append((name, result))
                else:
                    print(G + "[✓] Secure" + E)
            except:
                print(Y + "[?] Error de prueba" + E)
        print("\n" + C + "[★] Vulnerabilidades potenciales: " + str(len(results)) + "/4" + E)
        return results

    def _check_redirect(self, url):
        try:
            r = requests.get(url + "?redirect=http://evil.com&next=http://evil.com", timeout=5,
                             allow_redirects=False, headers={'User-Agent': self.ua})
            if 'evil.com' in r.headers.get('Location', '').lower():
                return "Redirige a dominio externo"
        except:
            pass
        return None

    def _check_xss(self, url):
        try:
            r = requests.get(url + "?q=<script>ATILA_TEST</script>&search=<script>ATILA_TEST</script>",
                             timeout=5, headers={'User-Agent': self.ua})
            if '<script>ATILA_TEST</script>' in r.text:
                return "Refleja payloads sin sanitizar"
        except:
            pass
        return None

    def _check_sqli(self, url):
        try:
            errors = ['sql syntax', 'mysql_fetch', 'postgresql', 'sqlite3', 'unclosed quotation']
            r = requests.get(url + "?id=1'", timeout=5, headers={'User-Agent': self.ua})
            text = r.text.lower()
            for err in errors:
                if err in text:
                    return "Posible SQLi: error detectado"
        except:
            pass
        return None

    def _check_info(self, url):
        try:
            for path in ['/phpinfo.php', '/info.php', '/server-status', '/.git/config', '/.env']:
                r = requests.get(url.rstrip('/') + path, timeout=3, headers={'User-Agent': self.ua})
                if r.status_code == 200:
                    return "Archivo sensible accesible: " + path
        except:
            pass
        return None

    def h2_detector(self, target):
        print(B + "\n[•] ATILA: H2 Detector - HTTP/2 Check" + E)
        try:
            import ssl
            host = urlparse(target).netloc if target.startswith('http') else target
            try:
                ipaddress.ip_address(host)
                ip = host
            except ValueError:
                ip = socket.gethostbyname(host)
            print(Y + "[*] Verificando HTTP/2 para " + host + " (" + ip + ")..." + E)
            context = ssl.create_default_context()
            context.set_alpn_protocols(['h2', 'http/1.1'])
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            sock = socket.create_connection((ip, 443), timeout=5)
            ssock = context.wrap_socket(sock, server_hostname=host)
            proto = ssock.selected_alpn_protocol()
            ssock.close()
            if proto == 'h2':
                print(G + "[+] " + host + " soporta HTTP/2 (h2)" + E)
            elif proto == 'http/1.1':
                print(Y + "[-] " + host + " solo soporta HTTP/1.1" + E)
            else:
                print(R + "[-] " + host + " no negocia ALPN correctamente" + E)
        except ImportError:
            print(Y + "[!] Módulo ssl no disponible" + E)
        except Exception as err:
            print(R + "[-] Error: " + str(err) + E)

    def view_history(self):
        """[21] Historial - Biblioteca y estadísticas acumuladas"""
        print(B + "\n[•] ATILA: Historial y Estadísticas" + E)
        res_dir = os.path.join(os.path.expanduser('~'), 'atila-pro', 'resultados')
        if not os.path.exists(res_dir):
            print(Y + "[!] Aún no hay carpeta de resultados. ¡A cazar primero!" + E)
            return
        proxies_files = glob.glob(os.path.join(res_dir, 'proxies_*.txt'))
        vivos_files = glob.glob(os.path.join(res_dir, 'hosts_vivos_*.txt'))
        export_files = glob.glob(os.path.join(res_dir, '*_export_*.json'))
        total_proxies = 0
        for pf in proxies_files:
            try:
                with open(pf) as f:
                    total_proxies += sum(1 for line in f if line.strip() and not line.startswith('#'))
            except Exception:
                pass
        total_vivos = 0
        for vf in vivos_files:
            try:
                with open(vf) as f:
                    total_vivos += sum(1 for line in f if line.strip() and not line.startswith('#'))
            except Exception:
                pass
        cols = term_cols()
        print(C + '═' * cols + E)
        print(G + "  📊 ESTADÍSTICAS ACUMULADAS DE TU CARRERA" + E)
        print(C + '═' * cols + E)
        print("  " + Y + "Archivos de proxies:" + E + " " + str(len(proxies_files)) +
              "  (" + G + str(total_proxies) + " proxies reales históricos" + E + ")")
        print("  " + Y + "Mapas de vivos:" + E + " " + str(len(vivos_files)) +
              "  (" + C + str(total_vivos) + " hosts mapeados" + E + ")")
        print("  " + Y + "Exportaciones JSON:" + E + " " + str(len(export_files)) + E)
        print(C + '═' * cols + E)
        all_files = proxies_files + vivos_files + export_files
        all_files.sort(key=os.path.getmtime, reverse=True)
        if not all_files:
            print(Y + "[!] La carpeta existe pero está vacía." + E)
            return
        print()
        print(Y + "  📚 Últimos 10 archivos:" + E)
        for i, fp in enumerate(all_files[:10], 1):
            name = os.path.basename(fp)
            size = os.path.getsize(fp)
            mtime = time.strftime('%d/%m %H:%M', time.localtime(os.path.getmtime(fp)))
            print("  " + G + "[" + str(i).zfill(2) + "]" + E + " " + W + fit(name, 38) + E +
                  " " + D + str(size).rjust(6) + " B · " + mtime + E)
        print()
        print(G + "  [L]" + E + " Limpiar historial (borra toda la carpeta resultados)")
        print(G + "  [0]" + E + " Volver")
        opt = input(G + "  > Opción: " + E).strip().lower()
        if opt == 'l':
            conf = input(R + "  Escribe 'SI' en mayúsculas para confirmar el borrado total: " + E).strip()
            if conf == 'SI':
                shutil.rmtree(res_dir)
                self.logger.info("Historial de resultados borrado por el usuario")
                print(G + "[✓] Historial borrado. Lienzo limpio." + E)
            else:
                print(Y + "[*] Borrado cancelado." + E)

    def configuracion(self):
        print(B + "\n[•] ATILA: Configuración persistente" + E)
        pwrap(Y, "Se guarda en ~/.atila/config.json y sobrevive reinicios de Termux.")
        while True:
            c = self.cfg
            print()
            print(G + "    [1]" + E + " Workers Etapa 1 ...... " + W + str(c['workers_e1']) + E)
            print(G + "    [2]" + E + " Workers Etapa 2 ...... " + W + str(c['workers_e2']) + E)
            print(G + "    [3]" + E + " Timeout TCP (s) ...... " + W + str(c['tcp_timeout']) + E)
            print(G + "    [4]" + E + " Tijera default ....... " + W + str(c['tijera_default']) + E)
            print(G + "    [5]" + E + " Modo default ......... " + W + str(c['modo_default']) + E)
            print(G + "    [6]" + E + " ASN favorito ......... " + W + (str(c['asn_favorito']) or '(ninguno)') + E)
            print(G + "    [7]" + E + " Ruta favorita ........ " + W + (str(c['ruta_favorita']) or '(ninguna)') + E)
            print(G + "    [8]" + E + " Export automático .... " + W + ('Sí' if c['export_auto'] else 'No') + E)
            print(G + "    [0]" + E + " Volver")
            opt = input(G + "    > Editar: " + E).strip()
            if opt == '0':
                return
            elif opt == '1':
                v = input(G + "    Nuevo valor 1-500 (Enter = dejar): " + E).strip()
                if v.isdigit() and 1 <= int(v) <= 500:
                    self.cfg['workers_e1'] = int(v)
                    save_config(self.cfg)
                    self.logger.info("Config: workers_e1=" + v)
            elif opt == '2':
                v = input(G + "    Nuevo valor 1-200 (Enter = dejar): " + E).strip()
                if v.isdigit() and 1 <= int(v) <= 200:
                    self.cfg['workers_e2'] = int(v)
                    save_config(self.cfg)
                    self.logger.info("Config: workers_e2=" + v)
            elif opt == '3':
                v = input(G + "    Nuevo valor 0.1-5 (Enter = dejar): " + E).strip()
                try:
                    fv = float(v)
                    if 0.1 <= fv <= 5:
                        self.cfg['tcp_timeout'] = fv
                        save_config(self.cfg)
                        self.logger.info("Config: tcp_timeout=" + v)
                except ValueError:
                    pass
            elif opt == '4':
                v = input(G + "    Nuevo valor 8-24 (Enter = dejar): " + E).strip()
                if v.isdigit() and 8 <= int(v) <= 24:
                    self.cfg['tijera_default'] = int(v)
                    save_config(self.cfg)
                    self.logger.info("Config: tijera_default=" + v)
            elif opt == '5':
                v = input(G + "    Nuevo valor 1 o 2 (Enter = dejar): " + E).strip()
                if v in ('1', '2'):
                    self.cfg['modo_default'] = v
                    save_config(self.cfg)
                    self.logger.info("Config: modo_default=" + v)
            elif opt == '6':
                v = input(G + "    ASN favorito o vacío (Enter = dejar): " + E).strip()
                if v == '' or v.isdigit():
                    self.cfg['asn_favorito'] = v
                    save_config(self.cfg)
                    self.logger.info("Config: asn_favorito=" + v)
            elif opt == '7':
                v = input(G + "    Ruta favorita o vacía (Enter = dejar): " + E).strip()
                self.cfg['ruta_favorita'] = os.path.expanduser(v) if v else ''
                save_config(self.cfg)
                self.logger.info("Config: ruta_favorita=" + str(self.cfg['ruta_favorita']))
            elif opt == '8':
                self.cfg['export_auto'] = not self.cfg['export_auto']
                save_config(self.cfg)
                self.logger.info("Config: export_auto=" + str(self.cfg['export_auto']))
            else:
                print(R + "[-] Opción inválida." + E)

    def view_log(self):
        print(B + "\n[•] ATILA: Bitácora de Actividad" + E)
        if not os.path.exists(self.log_file):
            print(Y + "[!] Aún no hay bitácora registrada." + E)
            return
        print(D + "    Últimas 30 líneas de: " + self.log_file + E)
        print(C + '─' * term_cols() + E)
        try:
            with open(self.log_file, 'r') as f:
                lines = f.readlines()
            for line in lines[-30:]:
                if '[ERROR]' in line:
                    print(R + line.strip() + E)
                elif '[WARNING]' in line:
                    print(Y + line.strip() + E)
                else:
                    print(D + line.strip() + E)
        except Exception as e:
            print(R + "[-] Error al leer log: " + str(e) + E)
        print(C + '─' * term_cols() + E)

    def asn_hunter(self):
        print(B + "\n[•] ATILA: Carrier ASN Hunt" + E)
        print(Y + "[*] Esta consulta necesita internet ACTIVO." + E)
        operator = ''
        if shutil.which('termux-telephony-deviceinfo'):
            try:
                p = subprocess.run(['termux-telephony-deviceinfo'],
                                   capture_output=True, text=True, timeout=10)
                info = json.loads(p.stdout)
                operator = info.get('operator_name') or info.get('sim_operator_name') or ''
                if operator:
                    print(G + "[✓] Chip detectado: " + str(operator) + E)
            except Exception:
                pass
        ip_pub = ''
        org = ''
        for name, url, extract in [
            ('ipinfo.io', 'https://ipinfo.io/json', lambda d: (d.get('ip', ''), d.get('org', ''))),
            ('ip-api.com', 'http://ip-api.com/json', lambda d: (d.get('query', ''), d.get('as', '')))]:
            d = self.http_json(url, timeout=8)
            if d:
                ip_pub, org = extract(d)
                if ip_pub and org:
                    print(G + "[✓] Vista pública vía " + name + ": " + ip_pub + E)
                    break
        asn = ''
        if org:
            m = re.match(r'AS(\d+)', org.strip(), re.I)
            if m:
                asn = m.group(1)
        if not asn:
            fav = str(self.cfg.get('asn_favorito', ''))
            prompt = "    Escribe el ASN manual (solo números"
            if fav:
                prompt += ", Enter = favorito " + fav
            prompt += "): "
            asn = input(G + prompt + E).strip() or fav
            if not asn.isdigit():
                print(R + "[-] ASN inválido." + E)
                return
        print(Y + "[*] Descargando prefijos CIDR de AS" + asn + "..." + E)
        prefixes, source = self.fetch_prefixes(asn)
        if not prefixes:
            print(R + "[-] No hubo respuesta de ninguna fuente (ni requests ni curl)." + E)
            return
        def keyfn(pre):
            try:
                net = ipaddress.ip_network(pre, strict=False)
            except ValueError:
                return (2, 0)
            grp = 1
            if ip_pub:
                try:
                    if ipaddress.ip_address(ip_pub) in net:
                        grp = 0
                except ValueError:
                    pass
            return (grp, -net.prefixlen)
        prefixes.sort(key=keyfn)
        out_dir = os.path.join(os.path.expanduser('~'), 'atila-pro')
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, 'rangos_asn_' + asn + '.txt')
        total_ips = 0
        with open(out_file, 'w') as f:
            f.write("# Rangos CIDR de AS" + asn + "\n")
            if operator:
                f.write("# Operador del chip: " + str(operator) + "\n")
            f.write("# Generado por ATILA PRO 7.7 vía " + source + "\n\n")
            for pre in prefixes:
                f.write(pre + "\n")
                try:
                    total_ips += ipaddress.ip_network(pre, strict=False).num_addresses
                except ValueError:
                    pass
        pwrap(G, "[✓] Guardado: " + out_file)
        print(C + "[★] Prefijos: " + str(len(prefixes)) + " | ~IPs totales: " + str(total_ips) + E)
        q = input(G + "\n    ¿Lanzar escaneo [11] ahora con este archivo? (s/N): " + E).strip().lower()
        if q == 's':
            self.mobile_proxy_scan(out_file)

    def macgyver_pack(self):
        print(B + "\n[•] ATILA: MacGyver Pack Argentina" + E)
        print()
        print(G + "[1]" + E + " PERSONAL   (AS7303)")
        print(G + "[2]" + E + " CLARO      (AS19037)")
        print(G + "[3]" + E + " MOVISTAR   (AS22927/262175)")
        print(G + "[4]" + E + " TODAS")
        print()
        choice = input(G + "> Elige operadora (1-4): " + E).strip()
        if choice == '4':
            selected = ['1', '2', '3']
            fname = 'pack_macgyver_todas.txt'
        elif choice in CARRIERS_AR:
            selected = [choice]
            fname = 'pack_macgyver_' + CARRIERS_AR[choice]['slug'] + '.txt'
        else:
            print(R + "[-] Opción inválida." + E)
            return
        out_dir = os.path.join(os.path.expanduser('~'), 'atila-pro')
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, fname)
        total_ips = 0
        n_ranges = 0
        with open(out_file, 'w') as f:
            f.write("# Pack MacGyver Argentina - ATILA PRO 7.7\n\n")
            for key in selected:
                info = CARRIERS_AR[key]
                f.write("# " + info['name'] + " - ASN: " + " / ".join(info['asns']) + "\n")
                for r in info['ranges']:
                    f.write(r + "\n")
                    n_ranges += 1
                    try:
                        total_ips += ipaddress.ip_network(r, strict=False).num_addresses
                    except ValueError:
                        pass
                f.write("\n")
        pwrap(G, "[✓] Guardado: " + out_file)
        print(C + "[★] Rangos: " + str(n_ranges) + " | ~IPs: " + str(total_ips) + E)
        q = input(G + "\n    ¿Lanzar escaneo [11] ahora con este archivo? (s/N): " + E).strip().lower()
        if q == 's':
            self.mobile_proxy_scan(out_file)

    def fresh_pools(self, catalog=None, title='Fresh Pools Argentina'):
        if catalog is None:
            catalog = CARRIERS_AR
        print(B + "\n[•] ATILA: " + title + E)
        print()
        keys = list(catalog.keys())
        for key in keys:
            info = catalog[key]
            print(G + "[" + key + "]" + E + " " + fit(info['name'] + " (AS" + "/AS".join(info['asns']) + ")", term_cols() - 8))
        print(G + "[0]" + E + " TODAS")
        print()
        choice = input(G + "> Elige (0-" + keys[-1] + "): " + E).strip()
        if choice == '0':
            selected = keys[:]
        elif choice in catalog:
            selected = [choice]
        else:
            print(R + "[-] Opción inválida." + E)
            return
        print()
        print(Y + "    Tijera de tamaño de bloque:" + E)
        print(D + "    [16] operadoras | [20] mixto | [24] clouds/CDN" + E)
        def_tij = int(self.cfg.get('tijera_default', 16))
        mf = input(G + "    Máximo prefijo a conservar (Enter = " + str(def_tij) + "): " + E).strip()
        maxlen = int(mf) if mf.isdigit() and 8 <= int(mf) <= 24 else def_tij
        all_nets = []
        raw_prefixes = []
        downloaded_any = False
        used_sources = set()
        for key in selected:
            info = catalog[key]
            for asn in info['asns']:
                print(Y + "[*] Consultando AS" + asn + "..." + E)
                prefixes, source = self.fetch_prefixes(asn)
                if not prefixes:
                    print(R + "  ✗ Sin respuesta de ninguna fuente (ni requests ni curl)" + E)
                    continue
                downloaded_any = True
                used_sources.add(source)
                raw_prefixes.extend(prefixes)
                kept = 0
                for p in prefixes:
                    try:
                        net = ipaddress.ip_network(p, strict=False)
                        if net.prefixlen <= maxlen:
                            all_nets.append(net)
                            kept += 1
                    except ValueError:
                        pass
                print(G + "  ✓ AS" + asn + " vía " + source + ": " + str(len(prefixes)) +
                      " prefijos → " + str(kept) + " pasan la tijera /" + str(maxlen) + E)
                if kept == 0:
                    print(Y + "  ⚠ Este ASN solo anuncia bloques chicos (/17-/24):" + E)
                    print(Y + "    con tijera /" + str(maxlen) + " no sobrevive ninguno. Prueba tijera 24." + E)
        if not all_nets and downloaded_any:
            print()
            print(Y + "[!] La descarga funcionó, pero la tijera /" + str(maxlen) + " dejó todo fuera." + E)
            q = input(G + "    ¿Re-filtrar con tijera 24 sin volver a descargar? (s/N): " + E).strip().lower()
            if q == 's':
                maxlen = 24
                for p in raw_prefixes:
                    try:
                        net = ipaddress.ip_network(p, strict=False)
                        if net.prefixlen <= maxlen:
                            all_nets.append(net)
                    except ValueError:
                        pass
                print(G + "[✓] Re-filtrado al vuelo: " + str(len(all_nets)) + " bloques recuperados." + E)
        if not all_nets:
            if downloaded_any:
                print(R + "[-] Descarga OK, pero la tijera dejó todo fuera incluso con 24." + E)
            else:
                print(R + "[-] No hubo respuesta de ninguna fuente (ni requests ni curl)." + E)
            return
        collapsed = list(ipaddress.collapse_addresses(all_nets))
        out_dir = os.path.join(os.path.expanduser('~'), 'atila-pro')
        os.makedirs(out_dir, exist_ok=True)
        slug = 'mix' if len(selected) > 1 else catalog[selected[0]]['slug']
        out_file = os.path.join(out_dir, 'fresh_' + slug + '_' + time.strftime('%Y%m%d') + '.txt')
        total_ips = 0
        with open(out_file, 'w') as f:
            f.write("# " + title + " - ATILA PRO 7.7\n")
            f.write("# Fecha: " + time.strftime('%Y-%m-%d %H:%M:%S') + "\n")
            f.write("# Fuentes BGP: " + ", ".join(sorted(used_sources)) + "\n")
            f.write("# Prefijos <= /" + str(maxlen) + ", colapsados\n\n")
            for n in collapsed:
                f.write(str(n) + "\n")
                total_ips += n.num_addresses
        pwrap(G, "[✓] Guardado: " + out_file)
        print(C + "[★] Bloques finales: " + str(len(collapsed)) + " | ~IPs: " + str(total_ips) + E)
        if total_ips > 1000000:
            pwrap(Y, "[!] Mega-lista: escanea por bloques y de noche (tmux + termux-wake-lock).")
        print(D + "[i] Tip: para clouds/CDN recuerda usar modo 1 (continuo) en el escaneo." + E)
        q = input(G + "\n    ¿Lanzar escaneo [11] ahora? (s/N): " + E).strip().lower()
        if q == 's':
            self.mobile_proxy_scan(out_file)

    def vivos_lab(self):
        print(B + "\n[•] ATILA: Vivos Lab - Laboratorio de hosts vivos" + E)
        pwrap(Y, "Trabaja sobre tus archivos hosts_vivos_*.txt: re-verificar, inspeccionar, comparar, exportar.")
        base = os.path.join(os.path.expanduser('~'), 'atila-pro')
        candidates = sorted(glob.glob(os.path.join(base, '**', 'hosts_vivos_*.txt'), recursive=True),
                            key=os.path.getmtime, reverse=True)
        if not candidates:
            print(R + "[-] No se encontraron archivos hosts_vivos_*.txt bajo ~/atila-pro" + E)
            print(D + "    Corre primero un escaneo [11] para generarlos." + E)
            return
        print()
        for i, path in enumerate(candidates[:8], 1):
            try:
                n = sum(1 for _ in open(path))
            except Exception:
                n = 0
            print(G + "[" + str(i) + "]" + E + " " + fit(os.path.relpath(path, base) + "  (" + str(n) + " IPs)", term_cols() - 8))
        print(G + "[m]" + E + " Escribir ruta manual")
        print()
        sel = input(G + "> Elige archivo (1-" + str(min(8, len(candidates))) + " o m): " + E).strip()
        if sel == 'm':
            filepath = os.path.expanduser(input(G + "    Ruta: " + E).strip())
        elif sel.isdigit() and 1 <= int(sel) <= min(8, len(candidates)):
            filepath = candidates[int(sel) - 1]
        else:
            print(R + "[-] Selección inválida." + E)
            return
        if not os.path.exists(filepath):
            print(R + "[-] Archivo no encontrado." + E)
            return
        try:
            with open(filepath) as f:
                ips = [l.strip() for l in f if l.strip() and not l.startswith('#')]
        except Exception as e:
            print(R + "[-] Error al leer: " + str(e) + E)
            return
        if not ips:
            print(R + "[-] Archivo vacío." + E)
            return
        self.logger.info("Vivos Lab cargó " + os.path.basename(filepath) + " (" + str(len(ips)) + " IPs)")
        print(C + "[★] " + str(len(ips)) + " IPs cargadas de " + os.path.basename(filepath) + E)
        while True:
            print()
            print(Y + "    VIVOS LAB sobre " + fit(os.path.basename(filepath), term_cols() - 22) + E)
            print(G + "    [1]" + E + " Re-verificar todas (pipeline E1+E2, sin internet)")
            print(G + "    [2]" + E + " Inspeccionar con curl (cara + test de proxy, con internet)")
            print(G + "    [3]" + E + " Time-lapse: comparar con otro archivo")
            print(G + "    [4]" + E + " Estadísticas del archivo")
            print(G + "    [5]" + E + " Exportar este archivo (JSON/CSV/HTML)")
            print(G + "    [0]" + E + " Volver")
            opt = input(G + "    > Opción: " + E).strip()
            if opt == '0':
                return
            elif opt == '1':
                print(Y + "[*] Re-verificando " + str(len(ips)) + " IPs (modo chip OK)..." + E)
                pos, alv, interrupted = self.run_pipeline(ips, 'LAB')
                print(G + "✓ Positivos: " + str(len(pos)) + " | Vivos confirmados: " + str(len(alv)) + E)
                if alv:
                    out_dir = os.path.dirname(os.path.abspath(filepath))
                    alive_file = os.path.join(out_dir, 'hosts_vivos_' + time.strftime('%Y%m%d_%H%M%S') + '.txt')
                    with open(alive_file, 'w') as f:
                        f.write("# Hosts con puertos abiertos (re-verificados)\n")
                        for ip in alv:
                            f.write(ip + "\n")
                    pwrap(C, "[i] Vivos confirmados guardados en: " + alive_file)
                if pos:
                    out = self.save_results(pos, filepath, partial=interrupted)
                    pwrap(Y, "[*] Proxies guardados en: " + out)
            elif opt == '2':
                if not self._check_internet_connection():
                    print(R + "[-] Esta prueba necesita internet ACTIVO (WiFi o datos)." + E)
                    continue
                q = input(G + "    ¿Cuántas inspeccionar? (Enter = 10, o 'todas'): " + E).strip().lower()
                if q == 'todas':
                    sample = ips
                elif q.isdigit() and int(q) > 0:
                    sample = ips[:int(q)]
                else:
                    sample = ips[:10]
                encontrados = []
                for i, ip in enumerate(sample, 1):
                    print()
                    print(C + "[" + str(i) + "/" + str(len(sample)) + "] " + ip + E)
                    try:
                        r = requests.get('http://' + ip, timeout=8, headers={'User-Agent': self.ua})
                        srv = r.headers.get('Server', 'N/A')
                        print(G + "    Web: HTTP " + str(r.status_code) + " | Server: " + fit(srv, term_cols() - 26) + E)
                    except Exception:
                        print(D + "    Web: sin respuesta directa" + E)
                    try:
                        rp = requests.get('http://example.com', proxies={'http': 'http://' + ip + ':80'},
                                          timeout=8, headers={'User-Agent': self.ua})
                        if 'Example Domain' in rp.text:
                            print(G + "    PROXY: ¡ACEPTA TUNELAR! (proxy real)" + E)
                            encontrados.append({'ip': ip, 'port': 80, 'status': 'positive',
                                                'message': 'Proxy real verificado vía example.com'})
                        else:
                            print(Y + "    PROXY: respondió pero no tunelea example.com" + E)
                    except Exception:
                        print(R + "    PROXY: no acepta CONNECT (no es proxy)" + E)
                if encontrados:
                    out = self.save_results(encontrados, filepath)
                    pwrap(Y, "[*] Proxies guardados en: " + out)
                else:
                    print(Y + "[!] Cero proxies reales en la muestra. Normal en nubes/CDN." + E)
            elif opt == '3':
                print()
                for i, path in enumerate(candidates[:8], 1):
                    mark = '  ← archivo actual' if path == filepath else ''
                    print(G + "[" + str(i) + "]" + E + " " + fit(os.path.relpath(path, base) + mark, term_cols() - 8))
                sel2 = input(G + "    > Comparar contra (número): " + E).strip()
                if not (sel2.isdigit() and 1 <= int(sel2) <= min(8, len(candidates))):
                    print(R + "[-] Selección inválida." + E)
                    continue
                other = candidates[int(sel2) - 1]
                try:
                    with open(other) as f:
                        ips2 = set(l.strip() for l in f if l.strip() and not l.startswith('#'))
                except Exception as e:
                    print(R + "[-] Error al leer: " + str(e) + E)
                    continue
                a, b = set(ips), ips2
                persist = a & b
                gone = a - b
                new = b - a
                print(C + "[★] Time-lapse:" + E)
                print(G + "    Persistentes (en ambos): " + str(len(persist)) + E)
                print(R + "    Desaparecidas (solo en el 1º): " + str(len(gone)) + E)
                print(Y + "    Nuevas (solo en el 2º): " + str(len(new)) + E)
                if persist:
                    out_dir = os.path.dirname(os.path.abspath(filepath))
                    pfile = os.path.join(out_dir, 'persistentes_' + time.strftime('%Y%m%d_%H%M%S') + '.txt')
                    with open(pfile, 'w') as f:
                        f.write("# IPs vivas en ambas fechas (infraestructura estable)\n")
                        for ip in sorted(persist):
                            f.write(ip + "\n")
                    pwrap(C, "[i] Persistentes guardadas en: " + pfile)
            elif opt == '4':
                c = Counter('.'.join(ip.split('.')[:2]) + '.0.0/16' for ip in ips)
                print(C + "[★] Estadísticas: " + str(len(ips)) + " IPs en " + str(len(c)) + " redes /16" + E)
                print(Y + "    Redes /16 más pobladas:" + E)
                for net, n in c.most_common(10):
                    print(G + "    " + net + " → " + str(n) + " IPs" + E)
            elif opt == '5':
                creados = self.export_results(ips, filepath, 'vivos')
                if creados:
                    for cfile in creados:
                        pwrap(C, "[✓] Exportado: " + cfile)
                    print(D + "    Tip: abre el .html con: termux-open <archivo>" + E)
                else:
                    print(R + "[-] No se pudo exportar." + E)
            else:
                print(R + "[-] Opción inválida." + E)

    def run_pipeline(self, ips, label, use_icmp=False, ping3fn=None):
        total_ips = len(ips)
        proxy_ports = [80, 8080, 3128, 8888, 1080, 9050, 8000, 8001, 3127]
        self.stats = {'positive': 0, 'negative': 0, 'total': 0, 'alive': 0}
        positive_ips = []
        alive_ips = []
        start_time = time.time()
        CHUNK = 2000
        w1 = int(self.cfg.get('workers_e1', 120))
        w2 = int(self.cfg.get('workers_e2', 20))
        tmo = float(self.cfg.get('tcp_timeout', 0.3))
        self.logger.info("Pipeline '" + label + "' iniciado: " + str(total_ips) + " IPs (w1=" + str(w1) + ")")

        def tcp_ping(ip, timeout=None):
            timeout = timeout or tmo
            for port in (80, 8080, 3128):
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout)
                try:
                    if s.connect_ex((ip, port)) == 0:
                        return True
                except Exception:
                    pass
                finally:
                    try:
                        s.close()
                    except Exception:
                        pass
            return False

        def recv_status(s, timeout=2.0):
            s.settimeout(timeout)
            try:
                data = s.recv(2048)
            except Exception:
                return ""
            text = data.decode('utf-8', errors='ignore')
            return text.split("\r\n")[0] if text else ""

        def recv_markers(s, markers, timeout=3.0):
            s.settimeout(timeout)
            data = b""
            try:
                while len(data) < 65536:
                    chunk = s.recv(8192)
                    if not chunk:
                        break
                    data += chunk
                    low = data.lower()
                    for m in markers:
                        if m.lower().encode() in low:
                            return True
            except Exception:
                pass
            return False

        def try_port(ip, port):
            for host, mport, path, markers in MARKERS:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.0)
                try:
                    if s.connect_ex((ip, port)) != 0:
                        return False, ''
                    s.sendall(("CONNECT " + host + ":" + str(mport) + " HTTP/1.1\r\n"
                               "Host: " + host + ":" + str(mport) + "\r\n"
                               "Proxy-Connection: keep-alive\r\n\r\n").encode())
                    parts = recv_status(s).split(" ")
                    if len(parts) < 2 or not parts[0].startswith("HTTP/") or parts[1] != "200":
                        return False, ''
                    s.sendall(("GET " + path + " HTTP/1.1\r\nHost: " + host + "\r\n"
                               "Connection: close\r\n\r\n").encode())
                    if recv_markers(s, markers):
                        return True, host
                except Exception:
                    pass
                finally:
                    try:
                        s.close()
                    except Exception:
                        pass
            return False, ''

        def verify_ip(ip):
            result = {'ip': ip, 'status': 'negative', 'port': None, 'message': ''}
            for port in proxy_ports:
                ok, host = try_port(ip, port)
                if ok:
                    result['status'] = 'positive'
                    result['port'] = port
                    result['message'] = 'Proxy real verificado vía ' + host
                    break
            return result

        if use_icmp and ping3fn:
            print(Y + "[*] Paso informativo ICMP (capa 3, no filtra)..." + E)
            icmp_alive = 0
            def icmp_check(ip):
                try:
                    return ping3fn(str(ip), timeout=0.3) is not None
                except Exception:
                    return False
            with ThreadPoolExecutor(max_workers=50) as ex2:
                for ok in ex2.map(icmp_check, ips):
                    if ok:
                        icmp_alive += 1
            print(C + "[i] Hosts que responden ICMP: " + str(icmp_alive) + "/" + str(total_ips) + E)
            print()

        print(Y + "[*] Etapa 1/2 (" + label + "): TCP-ping por lotes..." + E)
        print()
        processed = 0
        interrupted1 = False
        executor = ThreadPoolExecutor(max_workers=w1)
        try:
            for start in range(0, total_ips, CHUNK):
                chunk = ips[start:start + CHUNK]
                futs = {executor.submit(tcp_ping, ip): ip for ip in chunk}
                for fut in as_completed(futs):
                    processed += 1
                    ip = futs[fut]
                    try:
                        ok = fut.result()
                    except Exception:
                        ok = False
                    with self.lock:
                        self.stats['total'] = processed
                        if ok:
                            self.stats['alive'] += 1
                            alive_ips.append(ip)
                        else:
                            self.stats['negative'] += 1
                        self.render_bar(processed, total_ips, start_time, label + '/E1')
        except KeyboardInterrupt:
            interrupted1 = True
            print("\n" + Y + "[•] Ctrl+C en etapa 1." + E)
            try:
                executor.shutdown(wait=False, cancel_futures=True)
            except TypeError:
                executor.shutdown(wait=False)
        else:
            executor.shutdown(wait=True)
            sys.stdout.write("\r" + " " * (term_cols() - 1) + "\r")
            sys.stdout.flush()
        self.logger.info("Pipeline '" + label + "' E1: " + str(len(alive_ips)) + " vivos de " + str(total_ips))

        run_stage2 = True
        if interrupted1:
            if not alive_ips:
                run_stage2 = False
            else:
                q = input(G + "    ¿Verificar ahora los " + str(len(alive_ips)) + " hosts vivos? (s/N): " + E).strip().lower()
                run_stage2 = (q == 's')

        interrupted2 = False
        if run_stage2 and alive_ips:
            print()
            print(Y + "[*] Etapa 2/2 (" + label + "): CONNECT+E2E..." + E)
            print()
            processed2 = 0
            start2 = time.time()
            executor2 = ThreadPoolExecutor(max_workers=w2)
            try:
                for start in range(0, len(alive_ips), CHUNK):
                    chunk = alive_ips[start:start + CHUNK]
                    futs = {executor2.submit(verify_ip, ip): ip for ip in chunk}
                    for fut in as_completed(futs):
                        processed2 += 1
                        result = fut.result()
                        with self.lock:
                            if result['status'] == 'positive':
                                self.stats['positive'] += 1
                                positive_ips.append(result)
                                print(G + "\n[✓] " + result['ip'] + ":" + str(result['port']) +
                                      " → PROXY ACTIVO (" + result['message'] + ")" + E)
                            else:
                                self.stats['negative'] += 1
                            self.render_bar(processed2, len(alive_ips), start2, label + '/E2')
            except KeyboardInterrupt:
                interrupted2 = True
                print("\n" + Y + "[•] Ctrl+C en etapa 2." + E)
                try:
                    executor2.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    executor2.shutdown(wait=False)
            else:
                executor2.shutdown(wait=True)
                sys.stdout.write("\r" + " " * (term_cols() - 1) + "\r")
                sys.stdout.flush()
            self.logger.info("Pipeline '" + label + "' E2: " + str(len(positive_ips)) + " positivos de " + str(len(alive_ips)) + " vivos")
        return positive_ips, alive_ips, (interrupted1 or interrupted2)

    def mobile_proxy_scan(self, filepath):
        print(B + "\n[•] ATILA: Mobile Proxy Scanner - Rango IPv4" + E)
        filepath = os.path.expanduser(filepath)
        print(Y + "\n[*] Verificando estado de conexión..." + E)
        if self._check_internet_connection():
            print(R + "\n[!] ⚠️  CONEXIÓN DETECTADA" + E)
            choice = input(G + "\n    's' para continuar igual o ENTER para cancelar: " + E).strip().lower()
            if choice != 's':
                print(Y + "[*] Escaneo cancelado." + E)
                return
        else:
            print(G + "[✓] Modo señal de chip activado" + E)
        if not os.path.exists(filepath):
            print(R + "[-] Archivo no encontrado: " + filepath + E)
            return
        try:
            with open(filepath, 'r') as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        except PermissionError:
            print(R + "[-] Permiso denegado. Ejecuta: termux-setup-storage" + E)
            return
        except Exception as e:
            print(R + "[-] Error al leer: " + str(e) + E)
            return
        if not lines:
            print(R + "[-] Archivo vacío o sin rangos válidos" + E)
            return
        ranges_list = []
        all_ips = []
        for line in lines:
            try:
                network = ipaddress.ip_network(line, strict=False)
                hosts = [str(ip) for ip in network.hosts()]
                ranges_list.append((line, hosts))
                all_ips.extend(hosts)
                print(G + "  ✓ " + line + " → " + str(len(hosts)) + " IPs" + E)
            except ValueError:
                print(R + "  ✗ " + line + " → CIDR inválido" + E)
        if not all_ips:
            print(R + "[-] No se encontraron IPs válidas" + E)
            return
        total_ips = len(all_ips)
        in_tmux = bool(os.environ.get('TMUX'))
        cols = term_cols()
        print()
        print(C + '═' * cols + E)
        print(C + "[★] RESUMEN DE CARGA" + E)
        print(C + '═' * cols + E)
        print(G + "✓ Rangos válidos: " + str(len(ranges_list)) + E)
        print(Y + "★ Total de IPs: " + str(total_ips) + E)
        print(G + "✓ Sesión: " + ("tmux detectada (protegido ante cierres)" if in_tmux else "SIN tmux (si cierras la app, se pierde)") + E)
        print(C + '═' * cols + E)
        self.logger.info("Escaneo [11] iniciado: " + os.path.basename(filepath) + " (" + str(total_ips) + " IPs)")
        if total_ips > 100000 and not in_tmux:
            print()
            print(R + "[!] ⚠️  AIRBAG TMUX ACTIVADO" + E)
            pwrap(Y, "Lista de " + str(total_ips) + " IPs y NO estás dentro de una sesión tmux.")
            pwrap(Y, "Si cierras Termux o Android mata la app, el escaneo muere sin guardar nada.")
            print(D + "    Lo recomendado: cancelar ahora y relanzar protegido:" + E)
            print(G + "        tmux new -s caza   →   atila   →   menú 11" + E)
            print(D + "    Para maratones largas: termux-wake-lock evita que Android congele el CPU." + E)
            q = input(G + "\n    ¿Continuar igual sin tmux? (s/N): " + E).strip().lower()
            if q != 's':
                print(Y + "[*] Escaneo cancelado. Relanza dentro de tmux, socio." + E)
                return
        print()
        print(Y + "    Modo de escaneo:" + E)
        print(G + "    [1]" + E + " Continuo (todos los rangos de corrido)")
        print(G + "    [2]" + E + " Rango por rango")
        def_mode = str(self.cfg.get('modo_default', '1'))
        mode = input(G + "    > Modo (Enter = " + def_mode + "): " + E).strip() or def_mode
        input(G + "\n    ENTER para comenzar..." + E)
        print()
        start_all = time.time()
        positive_ips = []
        alive_ips = []
        stopped = False
        if mode == '2':
            for idx, (cidr, ips) in enumerate(ranges_list, 1):
                cols = term_cols()
                print()
                print(C + '═' * cols + E)
                print(C + "[★] " + fit("RANGO " + str(idx) + "/" + str(len(ranges_list)) + ": " + cidr +
                      " → " + str(len(ips)) + " IPs", cols - 2) + E)
                print(C + "    Positivos acumulados: " + str(len(positive_ips)) + E)
                print(C + '═' * cols + E)
                q = input(G + "    [ENTER] escanear | [x] saltar | [n] parar y guardar: " + E).strip().lower()
                if q == 'n':
                    stopped = True
                    break
                if q == 'x':
                    print(Y + "    → Rango saltado." + E)
                    continue
                pos, alv, interrupted = self.run_pipeline(ips, 'R' + str(idx))
                positive_ips.extend(pos)
                alive_ips.extend(alv)
                print(G + "\n[✓] Rango " + cidr + " terminado: " + str(len(pos)) + " positivos nuevos." + E)
                if interrupted:
                    stopped = True
                    break
        else:
            positive_ips, alive_ips, stopped = self.run_pipeline(all_ips, 'TODO')
        cols = term_cols()
        print("\n" + B + '═' * cols + E)
        print(C + "[★] RESULTADOS" + (" (PARCIALES)" if stopped else "") + E)
        print(B + '═' * cols + E)
        print(G + "✓ Proxies positivos: " + str(len(positive_ips)) + E)
        print(C + "• Hosts vivos: " + str(len(alive_ips)) + E)
        print(Y + "⏱ Tiempo: " + str(round(time.time() - start_all, 2)) + "s" + E)
        self.logger.info("Escaneo terminado: " + str(len(positive_ips)) + " proxies, " + str(len(alive_ips)) + " vivos")
        if alive_ips:
            resultados_dir = os.path.join(os.path.dirname(os.path.abspath(filepath)), 'resultados')
            os.makedirs(resultados_dir, exist_ok=True)
            alive_file = os.path.join(resultados_dir, 'hosts_vivos_' + time.strftime('%Y%m%d_%H%M%S') + '.txt')
            with open(alive_file, 'w') as f:
                f.write("# Hosts con puertos abiertos\n")
                for ip in alive_ips:
                    f.write(ip + "\n")
            pwrap(C, "[i] Hosts vivos guardados en: " + alive_file)
        if positive_ips:
            print("\n" + G + "╔" + "═" * (cols - 2) + "╗" + E)
            print(G + "║" + cpad(" PROXIES DETECTADOS (USAR)", cols - 2) + "║" + E)
            print(G + "╚" + "═" * (cols - 2) + "╝" + E)
            for proxy in positive_ips:
                pwrap(G, "  → " + proxy['ip'] + ":" + str(proxy['port']) + " (" + proxy['message'] + ")")
            output_file = self.save_results(positive_ips, filepath, partial=stopped)
            pwrap(Y, "[*] Guardado en: " + output_file)
        exportables = []
        if positive_ips:
            exportables.append(('proxies', positive_ips))
        if alive_ips:
            exportables.append(('vivos', alive_ips))
        if exportables:
            if self.cfg.get('export_auto'):
                print(Y + "[i] Export automático activado por config." + E)
                do_export = 's'
            else:
                do_export = input(G + "\n    ¿Exportar resultados también a JSON/CSV/HTML? (s/N): " + E).strip().lower()
            if do_export == 's':
                for tipo, datos in exportables:
                    creados = self.export_results(datos, filepath, tipo)
                    for cfile in creados:
                        pwrap(C, "[✓] Exportado: " + cfile)
        print(B + '═' * cols + E)

    def update_atila(self):
        print(B + "\n[•] ATILA: Update from Gist" + E)
        gist_url = "https://gist.githubusercontent.com/prettorian/ef763f8e724a1cf62e1885ff2745e274/raw/atila.py"
        print(Y + "[*] Verificando actualizaciones..." + E)
        try:
            response = requests.get(gist_url, timeout=10)
            if response.status_code == 200:
                new_code = response.text
                current_file = os.path.abspath(__file__)
                with open(current_file, 'r') as f:
                    current_code = f.read()
                if new_code.strip() == current_code.strip():
                    print(G + "[✓] Ya tienes la versión más reciente" + E)
                    return
                print(Y + "[!] Nueva versión disponible" + E)
                choice = input(G + "    ¿Actualizar? (s/n): " + E).strip().lower()
                if choice == 's':
                    with open(current_file + '.backup', 'w') as f:
                        f.write(current_code)
                    with open(current_file, 'w') as f:
                        f.write(new_code)
                    prefix = os.environ.get('PREFIX', '/data/data/com.termux/files/usr')
                    bin_target = os.path.join(prefix, 'bin', 'atila')
                    if os.path.exists(bin_target):
                        try:
                            shutil.copyfile(current_file, bin_target)
                            os.chmod(bin_target, 0o755)
                            print(Y + "[*] Comando 'atila' refrescado en $PREFIX/bin" + E)
                        except Exception:
                            pass
                    print(G + "[✓] ¡ATILA actualizado! Reinicia el script" + E)
                else:
                    print(Y + "[*] Cancelado" + E)
        except Exception as e:
            print(R + "[-] Error: " + str(e) + E)

    def install_command(self):
        print(B + "\n[•] ATILA: Install command" + E)
        prefix = os.environ.get('PREFIX', '/data/data/com.termux/files/usr')
        target = os.path.join(prefix, 'bin', 'atila')
        src = os.path.abspath(__file__)
        try:
            shutil.copyfile(src, target)
            os.chmod(target, 0o755)
            pwrap(G, "[✓] Instalado en: " + target)
            print(G + "[✓] Escribe 'atila' en cualquier terminal para lanzarlo" + E)
        except Exception as e:
            print(R + "[-] Error al instalar: " + str(e) + E)

def menu():
    atila = ATILA()
    while True:
        atila.banner()
        draw_menu()
        print()
        choice = input(G + "> Choice: " + E).strip()
        try:
            if choice == '01':
                t = input("Target: ").strip()
                if t: atila.single_host(t)
            elif choice == '02':
                fp = input("Host list file: ").strip()
                if fp: atila.browse_scan(fp)
            elif choice == '03':
                atila.quick_test()
            elif choice == '04':
                c = input("CIDR (ej 192.168.1.0/24): ").strip()
                if c: atila.cidr_scan(c)
            elif choice == '05':
                d = input("Domain: ").strip()
                if d: atila.subdomain_enum(d)
            elif choice == '06':
                t = input("Target: ").strip()
                if t: atila.reverse_ip(t)
            elif choice == '07':
                t = input("Text or file: ").strip()
                if t: atila.domain_extractor(t)
            elif choice == '08':
                atila.proxy_relay()
            elif choice == '09':
                t = input("Target URL: ").strip()
                if t: atila.trick_lab(t)
            elif choice == '10':
                t = input("Target: ").strip()
                if t: atila.h2_detector(t)
            elif choice == '11':
                hint = atila.cfg.get('ruta_favorita', '')
                prompt = "> Ruta del archivo"
                if hint:
                    prompt += " (Enter = " + hint + ")"
                prompt += ": "
                fp = input(G + prompt + E).strip() or hint
                if fp: atila.mobile_proxy_scan(fp)
            elif choice == '12':
                atila.update_atila()
            elif choice == '13':
                atila.install_command()
            elif choice == '14':
                atila.asn_hunter()
            elif choice == '15':
                atila.macgyver_pack()
            elif choice == '16':
                atila.fresh_pools()
            elif choice == '17':
                atila.fresh_pools(PROVIDERS_WORLD, 'Fresh Cloud Pack World')
            elif choice == '18':
                atila.vivos_lab()
            elif choice == '19':
                atila.view_log()
            elif choice == '20':
                atila.configuracion()
            elif choice == '21':
                atila.view_history()
            elif choice == '22':
                atila.licencia_menu()
            elif choice == '00':
                print(R + "\n[!] Exiting..." + E)
                atila.logger.info("Sesión finalizada por el usuario")
                sys.exit(0)
            else:
                print(R + "[!] Invalid option" + E)
            input(D + "\nPress Enter to continue..." + E)
        except KeyboardInterrupt:
            print("\n" + Y + "[•] Cancelled" + E)
        except Exception as err:
            print(R + "[!] Error: " + str(err) + E)
            input(D + "\nPress Enter to continue..." + E)

if __name__ == "__main__":
    argv = sys.argv[1:]
    if '--activate' in argv:
        idx = argv.index('--activate')
        if idx + 1 < len(argv):
            key = argv[idx + 1]
        else:
            key = input("Pega tu key: ").strip()
        ok, msg = activate_license(key)
        if ok:
            print(G + "[✓] " + msg + E)
            sys.exit(0)
        else:
            print(R + "[✗] " + msg + E)
            sys.exit(1)
    if '--license' in argv:
        estado = load_license_state()
        print("Estado de licencia: " + estado.get('estado', 'LIBRE'))
        if estado.get('estado') != 'LIBRE':
            print("alias=" + estado.get('alias', '') + " tier=" + estado.get('tier', '') +
                  " exp=" + estado.get('exp', ''))
        sys.exit(0)
    print(B + "[•] Checking dependencies..." + E)
    try:
        __import__('requests')
    except ImportError:
        print(Y + "  → Installing requests..." + E)
        os.system('pip install requests -q 2>/dev/null')
    print(G + "[+] ATILA ready!" + E + "\n")
    time.sleep(1)
    menu()
