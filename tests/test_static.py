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
