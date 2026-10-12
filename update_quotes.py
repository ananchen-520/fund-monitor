"""Update fund-monitor/quotes.json. Python standard library only.

Each source is checked independently. A green GitHub Action means the script ran,
not necessarily that all quotes were refreshed: inspect quotes.json -> status.
"""
import datetime as dt
import html
import json
import pathlib
import re
import urllib.request
from html.parser import HTMLParser

FILE = pathlib.Path(__file__).with_name('quotes.json')
TZ = dt.timezone(dt.timedelta(hours=8))
NOW = dt.datetime.now(TZ)
old = json.loads(FILE.read_text(encoding='utf-8')) if FILE.exists() else {}
prices = dict(old.get('prices') or {})
dates = dict(old.get('priceDates') or {})
sources = dict(old.get('sources') or {})
funds = dict(old.get('funds') or {})
funds.update({
    'DSE11': {'name': '安聯台灣科技基金', 'isin': 'TW000T3604Y3', 'currency': 'TWD', 'quoteStatus': 'automatic_public_NAV'},
    'DSE4': {'name': '安聯台灣大壩基金-A類型-新臺幣', 'isin': 'TW000T3601Y9', 'currency': 'TWD', 'quoteStatus': 'automatic_public_NAV'},
    'JFE15': {'name': '摩根美國科技基金 A(acc) USD', 'isin': 'LU0210536867', 'currency': 'USD', 'quoteStatus': 'automatic_public_NAV'},
    '00757': {'name': '統一NYSE FANG+ ETF', 'currency': 'TWD', 'quoteStatus': 'TWSE_automatic'},
})
messages = []
updated_at = old.get('updatedAt', '')

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
        if tag in ('td', 'th', 'tr', 'div', 'p', 'li', 'h1', 'h2', 'h3', 'br'):
            self.parts.append(' ')
    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.skip:
            self.skip -= 1
        self.parts.append(' ')
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

def get(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; PersonalFundMonitor/1.1)',
        'Accept': 'text/html,application/json,*/*',
        'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.7',
    })
    with urllib.request.urlopen(req, timeout=25) as response:
        raw = response.read()
        charset = response.headers.get_content_charset()
    # Some MoneyDJ sites declare Big5 only in HTML, not HTTP headers.
    meta = re.search(br'charset\s*=\s*[\"\']?([a-zA-Z0-9_-]+)', raw[:8192], re.I)
    declared = meta.group(1).decode('ascii') if meta else None
    for encoding in [declared, charset, 'utf-8', 'big5', 'cp950']:
        if not encoding:
            continue
        try:
            decoded = raw.decode(encoding)
            if '\ufffd' not in decoded:
                return decoded
        except (UnicodeError, LookupError):
            pass
    # A malformed byte in otherwise valid Big5 must not turn the entire page
    # into UTF-8 mojibake. Identity validation still rejects damaged titles.
    for encoding in [declared, charset]:
        if encoding:
            try:
                return raw.decode(encoding, errors='replace')
            except LookupError:
                pass
    return raw.decode('utf-8', errors='replace')

def accept(code, day, value, source):
    global updated_at
    day = dt.date.fromisoformat(day)
    if day > NOW.date() or day < NOW.date() - dt.timedelta(days=20):
        raise ValueError('報價日期超出允許範圍：' + str(day))
    if not 0 < value < 1000000:
        raise ValueError('報價數值不合理')
    if dates.get(code) and str(day) < dates[code]:
        raise ValueError('新來源日期比已儲存資料舊')
    prices[code] = round(value, 6)
    dates[code] = str(day)
    sources[code] = source
    updated_at = NOW.isoformat(timespec='seconds')
    messages.append(f'{code} 成功：{day}，{value}')

def parse_nav(code, url, identity, section):
    page = get(url)
    parser = TextExtractor()
    parser.feed(page)
    plain = html.unescape(re.sub(r'\s+', ' ', ''.join(parser.parts))).strip()
    # Verify exact fund identity and share class before using any numbers.
    if not all(re.search(term, plain, re.I) for term in identity):
        raise ValueError('基金名稱或級別驗證失敗')
    position = plain.find(section)
    if position < 0:
        raise ValueError('找不到淨值歷史區塊')
    tail = plain[position:position + 3500]
    # Historical NAV table: first YYYY/MM/DD followed by NAV.
    m = re.search(r'(20\d{2})[/-](\d{1,2})[/-](\d{1,2})\s+([\d,]+(?:\.\d+)?)', tail)
    if not m:
        raise ValueError('淨值歷史表格式不符')
    y, mo, d, nav = m.groups()
    accept(code, f'{int(y):04d}-{int(mo):02d}-{int(d):02d}', float(nav.replace(',', '')), url)

try:
    rows = json.loads(get('https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL'))
    row = next(r for r in rows if r.get('Code') == '00757')
    rawdate = str(row['Date']).strip()
    if not re.fullmatch(r'\d{7}', rawdate):
        raise ValueError('TWSE 日期格式異常')
    day = f'{int(rawdate[:3]) + 1911:04d}-{rawdate[3:5]}-{rawdate[5:]}'
    accept('00757', day, float(str(row['ClosingPrice']).replace(',', '')), 'TWSE STOCK_DAY_ALL')
except Exception as e:
    messages.append('00757 失敗，保留原值：' + str(e))

# Correct share-class-specific fund pages, not bank-internal DSE/JFE identifiers.
fund_pages = [
    ('DSE11', 'https://pscnetsecrwd.moneydj.com/w/wr/wr02.djhtm?a=ACDD04-A210003A',
     [r'安聯台灣科技基金'], '近30日淨值'),
    ('DSE4', 'https://mmafund.sinopac.com/w/wr/wr02.djhtm?a=ACDD01-TT1',
     [r'安聯台灣大壩基金-A類型-新臺幣'], '近30日淨值'),
    ('JFE15', 'https://tw.finance.yahoo.com/fund/F0GBR05VVS%3AFO/history',
     [r'摩根', r'美國科技', r'A股', r'累計'], '30天歷史報價'),
]
for code, url, identity, section in fund_pages:
    try:
        parse_nav(code, url, identity, section)
    except Exception as e:
        messages.append(f'{code} 失敗，保留原值：{e}')

fx = old.get('fx')
try:
    data = json.loads(get('https://open.er-api.com/v6/latest/USD'))
    if data.get('result') != 'success' or data.get('base_code') != 'USD':
        raise ValueError('匯率回傳狀態或幣別異常')
    rate = float(data['rates']['TWD'])
    day = dt.datetime.fromtimestamp(int(data['time_last_update_unix']), TZ).date()
    if not 15 < rate < 50 or day > NOW.date() or day < NOW.date() - dt.timedelta(days=10):
        raise ValueError('匯率或日期不合理')
    fx = round(rate, 6)
    old['fxDate'] = str(day)
    old['fxSource'] = 'ExchangeRate-API open access (reference rate)'
    messages.append(f'USD/TWD 成功：{day}，{rate}')
except Exception as e:
    messages.append('USD/TWD 失敗，保留原值：' + str(e))

result = dict(old)
result.update({
    'updatedAt': updated_at,
    'checkedAt': NOW.isoformat(timespec='seconds'),
    'prices': prices,
    'priceDates': dates,
    'sources': sources,
    'funds': funds,
    'status': '；'.join(messages),
})
if fx is not None:
    result['fx'] = fx
FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(result['status'])
