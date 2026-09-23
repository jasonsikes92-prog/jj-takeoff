"""Build an offline copy of a case's verified, current report view."""
import base64
import hashlib
from pathlib import Path
import re

from gen_reports import inject


def render_download(report):
    template = Path(__file__).with_name('lg_report_template.html').read_text(encoding='utf-8')
    # Downloads must work without requesting external fonts or sending data out.
    template = re.sub(r'<link\b[^>]*>\s*', '', template)
    scripts = re.findall(r'<script>(.*?)</script>', template, re.S)
    if len(scripts) != 1:
        raise ValueError('Expected one report renderer')
    digest = base64.b64encode(hashlib.sha256(scripts[0].encode()).digest()).decode()
    policy = ("default-src 'none'; style-src 'unsafe-inline'; "
              f"script-src 'sha256-{digest}'; base-uri 'none'; form-action 'none'")
    template = template.replace('<head>', '<head>\n<meta http-equiv="Content-Security-Policy" content="' + policy + '">', 1)
    return inject(template, report).encode('utf-8')
