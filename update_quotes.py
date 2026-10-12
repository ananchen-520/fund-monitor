"""Conservative daily quote checker: verified TWSE quote, fund identity registry."""
import datetime
import json
import pathlib
import urllib.request

FILE = pathlib.Path(__file__).with_name('quotes.json')
TZ = datetime.timezone(datetime.timedelta(hours=8))
now = datetime.datetime.now(TZ).isoformat(timespec='seconds')
old = json.loads(FILE.read_text(encoding='utf-8')) if FILE.exists() else {}
prices = dict(old.get('prices') or {})
price_dates = dict(old.get('priceDates') or {})
sources = dict(old.get('sources') or {})
funds = dict(old.get('funds') or {})
funds.update({
    'DSE11': {'name': '安聯台灣科技基金', 'isin': 'TW000T3604Y3', 'currency': 'TWD', 'quoteStatus': 'awaiting_verified_automatic_source'},
    'DSE4': {'name': '安聯台灣大壩基金-A類型-新臺幣', 'isin': 'TW000T3601Y9', 'currency': 'TWD', 'quoteStatus': 'awaiting_verified_automatic_source'},
    'JFE15': {'name': '摩根美國科技基金（級別待確認）', 'currency': 'USD', 'quoteStatus': 'awaiting_share_class_verification'},
    '00757': {'name': '統一NYSE FANG+ ETF', 'currency': 'TWD', 'quoteStatus': 'TWSE_automatic'},
})
messages = []
updated_at = old.get('updatedAt', '')
try:
    req = urllib.request.Request('https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL', headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=25) as response:
        rows = json.load(response)
    row = next((r for r in rows if r.get('Code') == '00757'), None)
    if row is None:
        raise ValueError('TWSE response did not include 00757')
    price = float(str(row['ClosingPrice']).replace(',', ''))
    raw_date = str(row['Date']).strip()
    if len(raw_date) != 7 or not raw_date.isdigit():
        raise ValueError('Unrecognized ROC date: ' + raw_date)
    date = f'{int(raw_date[:3]) + 1911:04d}-{raw_date[3:5]}-{raw_date[5:7]}'
    parsed_date = datetime.date.fromisoformat(date)
    if price <= 0 or parsed_date > datetime.datetime.now(TZ).date():
        raise ValueError('Invalid quote value or future date')
    if price_dates.get('00757') and date < price_dates['00757']:
        raise ValueError('Source quote is older than stored quote')
    prices['00757'] = price
    price_dates['00757'] = date
    sources['00757'] = 'TWSE STOCK_DAY_ALL'
    updated_at = now
    messages.append(f'00757 更新成功：{date}，NT$ {price}')
except Exception as exc:
    messages.append(f'00757 更新失敗，保留原報價：{exc}')
messages.append('DSE11、DSE4 已登錄基金身分，尚未啟用自動淨值抓取；JFE15 待核對級別')
result = dict(old)
result.update({'updatedAt': updated_at, 'checkedAt': now, 'prices': prices, 'priceDates': price_dates, 'sources': sources, 'funds': funds, 'status': '；'.join(messages)})
FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(result['status'])
