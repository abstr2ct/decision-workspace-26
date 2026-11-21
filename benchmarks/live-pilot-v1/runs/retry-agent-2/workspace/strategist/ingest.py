"""Bounded, read-only extraction. No macros, scripts or remote resources run."""

import csv
import hashlib
import io
import ipaddress
import json
import re
import socket
import urllib.parse
import urllib.request
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

MAX_BYTES = 8 * 1024 * 1024
MAX_EXPANDED = 32 * 1024 * 1024


class InputError(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


class ReadableHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript', 'template'):
            self.hidden += 1
        if tag in ('p', 'div', 'li', 'br', 'h1', 'h2', 'h3', 'tr'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'template') and self.hidden:
            self.hidden -= 1

    def handle_data(self, text):
        if not self.hidden:
            self.parts.append(text)


def decode(data):
    try:
        return data.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise InputError('Expected UTF-8. Convert the input explicitly; do not guess encoding.') from exc


def safe_zip(data):
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise InputError('Corrupt or non-Office ZIP container') from exc
    infos = archive.infolist()
    if len(infos) > 2000 or sum(i.file_size for i in infos) > MAX_EXPANDED:
        raise InputError('Office archive exceeds extraction limits')
    for info in infos:
        if info.flag_bits & 1:
            raise InputError('Encrypted archives are unsupported')
    return archive


def extract(data, suffix):
    if len(data) > MAX_BYTES:
        raise InputError('Source exceeds 8 MiB')
    suffix = suffix.lower()
    if suffix in ('.md', '.txt', '.json', '.jsonl'):
        return [{'locator': f'line:{i}', 'text': line} for i, line in enumerate(decode(data).splitlines(), 1) if line.strip()]
    if suffix in ('.html', '.htm'):
        parser = ReadableHTML()
        parser.feed(decode(data))
        lines = [' '.join(x.split()) for x in ''.join(parser.parts).splitlines() if x.strip()]
        return [{'locator': f'block:{i}', 'text': t} for i, t in enumerate(lines, 1)]
    if suffix in ('.csv', '.tsv'):
        text = decode(data)
        delimiter = '\t' if suffix == '.tsv' else ','
        rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
        if not rows:
            raise InputError('Empty table')
        width = len(rows[0])
        if not width or any(len(r) != width for r in rows):
            raise InputError('Ragged table: check delimiter and missing columns')
        return [{'locator': f'row:{i}', 'text': json.dumps(row, ensure_ascii=False)} for i, row in enumerate(rows, 1)]
    if suffix == '.docx':
        with safe_zip(data) as z:
            root = ET.fromstring(z.read('word/document.xml'))
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        result = []
        for i, p in enumerate(root.findall('.//w:p', ns), 1):
            value = ''.join(n.text or '' for n in p.findall('.//w:t', ns))
            if value.strip():
                result.append({'locator': f'p:{i}', 'text': value})
        return result
    if suffix == '.xlsx':
        ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        result = []
        with safe_zip(data) as z:
            strings = []
            if 'xl/sharedStrings.xml' in z.namelist():
                for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', ns):
                    strings.append(''.join(n.text or '' for n in si.findall('.//m:t', ns)))
            workbook = ET.fromstring(z.read('xl/workbook.xml'))
            relroot = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
            rels = {r.attrib['Id']: r.attrib['Target'] for r in relroot}
            for sheet in workbook.findall('m:sheets/m:sheet', ns):
                rid = sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
                target = rels[rid].replace('\\', '/')
                member = target.lstrip('/') if target.startswith('/') else 'xl/' + target
                # Reject traversal even though entries are never extracted to disk.
                if '..' in member.split('/'):
                    raise InputError('Unsafe worksheet reference')
                root = ET.fromstring(z.read(member))
                for cell in root.findall('.//m:sheetData/m:row/m:c', ns):
                    if cell.find('m:f', ns) is not None:
                        raise InputError('XLSX formulas are not evaluated. Export a verified values-only sheet.')
                    value = cell.find('m:v', ns)
                    text = value.text if value is not None else ''
                    if cell.attrib.get('t') == 's':
                        text = strings[int(text)]
                    elif cell.attrib.get('t') == 'inlineStr':
                        text = ''.join(n.text or '' for n in cell.findall('.//m:t', ns))
                    if text:
                        result.append({'locator': f"sheet:{sheet.attrib['name']}!{cell.attrib['r']}", 'text': text})
        return result
    raise InputError(f'Unsupported {suffix}. Use UTF-8 text, CSV/TSV, HTML, DOCX or values-only XLSX. PDF/OCR/audio/video require a separately attributed transcript.')


def validate_url(url, allowed_hosts):
    p = urllib.parse.urlsplit(url)
    if p.scheme != 'https' or p.username or p.password or p.port not in (None, 443):
        raise InputError('Only credential-free HTTPS on port 443 is allowed')
    host = (p.hostname or '').lower().rstrip('.')
    if not host or host not in allowed_hosts:
        raise InputError(f'Host is not explicitly allowed: {host}')
    if p.fragment:
        raise InputError('Remove the fragment before fetching; keep it in a citation if needed')
    # Check every resolved address; this is a guardrail, not a network sandbox.
    infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not infos or any(not ipaddress.ip_address(i[4][0]).is_global for i in infos):
        raise InputError('Non-public network address is forbidden')
    return host


class AllowedRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts):
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl, self.hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, hosts):
    validate_url(url, hosts)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), AllowedRedirect(hosts))
    req = urllib.request.Request(url, headers={'User-Agent': 'ProductStrategistResearch/0.1'})
    with opener.open(req, timeout=20) as response:
        final_url = response.geturl()
        validate_url(final_url, hosts)
        content_type = response.headers.get_content_type()
        if content_type not in ('text/html', 'text/plain', 'application/json'):
            raise InputError(f'Unsupported web content type: {content_type}')
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise InputError('Web response exceeds 8 MiB')
        charset = response.headers.get_content_charset() or 'utf-8'
        try:
            data = data.decode(charset).encode('utf-8')
        except (UnicodeError, LookupError) as exc:
            raise InputError('Cannot decode response charset') from exc
        if content_type == 'text/html':
            reject_access_challenge(data)
    return data, '.html' if content_type == 'text/html' else '.txt', final_url


def reject_access_challenge(data):
    head = data[:256*1024].decode('utf-8', errors='replace').casefold()
    title = re.search(r'<title[^>]*>(.*?)</title>',head,re.S)
    blocked_title = title and any(x in title.group(1) for x in ('client challenge','just a moment','access denied','verify you are human'))
    if blocked_title or '/cdn-cgi/challenge-platform/' in head:
        raise InputError('Access challenge returned instead of source content. Do not treat it as an article; use an authorized browser/source alternative and record acquisition provenance.')
