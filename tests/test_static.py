import re
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / 'static'
HTML_PAGES = sorted(STATIC.glob('*.html'))

SHARED_ASSETS = [
  '/static/js/tailwind.config.js',
  '/static/js/tailwind.min.js',
  '/static/css/app.css',
  '/static/js/app.js',
]


def _local_asset_paths(html):
  refs = re.findall(r'(?:src|href)="(/static/[^"]+)"', html)
  return sorted(set(refs))


def test_pages_have_no_external_urls():
  for page in HTML_PAGES:
    html = page.read_text()
    assert not re.search(r'https?://', html), f'{page.name} references an external URL'
    assert not re.search(r'//cdn\.', html), f'{page.name} references a CDN'


def test_pages_use_shared_design_system():
  for page in HTML_PAGES:
    html = page.read_text()
    for asset in SHARED_ASSETS:
      assert asset in html, f'{page.name} is missing {asset}'


def test_referenced_assets_exist():
  for page in HTML_PAGES:
    html = page.read_text()
    for ref in _local_asset_paths(html):
      target = STATIC / ref.removeprefix('/static/')
      assert target.exists(), f'{page.name} references missing asset {ref}'


def test_own_js_and_css_are_offline():
  for path in [STATIC / 'js/app.js', STATIC / 'js/tailwind.config.js', STATIC / 'css/app.css']:
    content = path.read_text()
    assert not re.search(r'https?://', content), f'{path.name} references an external URL'


def test_inter_font_is_bundled():
  font = STATIC / 'fonts' / 'inter-latin-wght-normal.woff2'
  assert font.exists()
  assert font.stat().st_size > 1000


def test_new_interface_mockup_removed():
  assert not (STATIC / 'newInterface.html').exists()


# Atributos/métodos padrão de elementos DOM que podem aparecer como `el.X`
# sem ser uma chave do objeto `el` (ex.: el.addEventListener, el.textContent).
DOM_API = {
  'addEventListener', 'removeEventListener', 'classList', 'title', 'value',
  'disabled', 'focus', 'blur', 'select', 'textContent', 'style', 'readOnly',
  'innerHTML', 'querySelector', 'querySelectorAll', 'replaceWith',
}


def test_inline_scripts_el_references_resolve():
  for page in HTML_PAGES:
    html = page.read_text()
    for m in re.finditer(r'<script>([\s\S]*?)</script>', html):
      src = m.group(1)
      if 'const el = {' not in src:
        continue
      el_match = re.search(r'const el = \{(.*?)\};', src, flags=re.DOTALL)
      assert el_match, f'{page.name}: could not parse el object'
      keys = set(re.findall(r'(\w+)\s*:', el_match.group(1)))
      clean = re.sub(r'/\*.*?\*/', '', src, flags=re.DOTALL)
      clean = re.sub(r'//[^\n]*', '', clean)
      clean = re.sub(r'const el = \{.*?\};', '', clean, flags=re.DOTALL)
      for use in re.findall(r'\bel\.(\w+)', clean):
        assert use in keys or use in DOM_API, \
          f'{page.name}: el.{use} used but not defined in the el object'

