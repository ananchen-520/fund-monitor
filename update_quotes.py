"""Daily fund quote updater. Standard library only; preserves last good quotes on errors."""
import datetime as dt
import html
import json
import pathlib
import re
import urllib.request

FILE = pathlib.Path(__file__).with_name('quotes.json')
TZ = dt.timezone(dt.timedelta(hours=8))
NOW = dt.datetime.now(TZ)
old = json.loads(FILE.read_text(encoding='utf-8')) if FILE.exists() else {}
prices = dict(old.get('prices') or {})
dates = dict(old.get('priceDates') or {})
sources = dict(old.get('sources') or {})
funds = dict(old.get('funds') or {})
funds.update({
 'DSE11': {'name':'安聯台灣科技基金','isin':'TW000T3604Y3','currency':'TWD','quoteStatus':'automatic_public_NAV'},
 'DSE4': {'name':'安聯台灣大壩基金-A類型-新臺幣','isin':'TW000T3601Y9','currency':'TWD','quoteStatus':'automatic_public_NAV'},
 'JFE15': {'name':'摩根美國科技基金 A(acc) USD','isin':'LU0210536867','currency':'USD','quoteStatus':'automatic_public_NAV'},
 '00757': {'name':'統一NYSE FANG+ ETF','currency':'TWD','quoteStatus':'TWSE_automatic'},
})
messages=[]
updated_at=old.get('updatedAt','')

def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; FundMonitor/1.0)','Accept':'text/html,application/json'})
 with urllib.request.urlopen(req,timeout=25) as r:
  return r.read().decode('utf-8','replace')

def accept(code, day, value, source):
 global updated_at
 day=dt.date.fromisoformat(day)
 if day>NOW.date() or day < NOW.date()-dt.timedelta(days=20):
  raise ValueError('報價日期不合理：'+str(day))
 if not (0 < value < 1000000):
  raise ValueError('淨值不合理')
 if dates.get(code) and str(day)<dates[code]:
  raise ValueError('來源比現有報價舊')
 prices[code]=round(value,6)
 dates[code]=str(day)
 sources[code]=source
 updated_at=NOW.isoformat(timespec='seconds')
 messages.append(f'{code} 更新成功：{day}，{value}')

def fund_nav(code,url,expected_name):
 raw=get(url)
 # Convert HTML into readable text, retaining table cell boundaries.
 raw=re.sub(r'<(script|style)\b[^>]*>.*?</\1>',' ',raw,flags=re.I|re.S)
 raw=re.sub(r'<[^>]+>',' ',raw)
 plain=html.unescape(re.sub(r'\s+',' ',raw))
 if expected_name not in plain:
  raise ValueError('基金名稱驗證失敗，拒絕更新')
 # First NAV history row: date and NAV (other text may intervene).
 match=re.search(r'(20\d\d[/-]\d{1,2}[/-]\d{1,2})\s+([\d,]+(?:\.\d+)?)',plain)
 if not match:
  raise ValueError('無法辨識淨值表日期與價格')
 day=match.group(1).replace('/','-')
 y,m,d=map(int,day.split('-'))
 accept(code,f'{y:04d}-{m:02d}-{d:02d}',float(match.group(2).replace(',','')),url)

try:
 rows=json.loads(get('https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL'))
 row=next(r for r in rows if r.get('Code')=='00757')
 rawdate=str(row['Date']).strip()
 if not re.fullmatch(r'\d{7}',rawdate):raise ValueError('台股日期格式異常')
 day=f'{int(rawdate[:3])+1911:04d}-{rawdate[3:5]}-{rawdate[5:]}'
 accept('00757',day,float(str(row['ClosingPrice']).replace(',','')),'TWSE STOCK_DAY_ALL')
except Exception as e:messages.append('00757 失敗，保留原值：'+str(e))

for code,url,name in [
 ('DSE11','https://fund.hncb.com.tw/w/wr/wr02.djhtm?a=ACDD04-DSE11','安聯台灣科技'),
 ('DSE4','https://fund.hncb.com.tw/w/wr/wr02.djhtm?a=ACDD01-DSE4','安聯台灣大壩'),
 ('JFE15','https://fund.hncb.com.tw/w/wb/wb02.djhtm?a=JFZG4-01H9','摩根基金-美國科技基金A股'),
]:
 try:fund_nav(code,url,name)
 except Exception as e:messages.append(f'{code} 失敗，保留原值：{e}')

# FX: Frankfurter's reference USD/TWD rate, dated and independently checked.
fx=old.get('fx')
try:
 data=json.loads(get('https://api.frankfurter.dev/v1/latest?base=USD&symbols=TWD'))
 rate=float(data['rates']['TWD'])
 day=dt.date.fromisoformat(data['date'])
 if not 15<rate<50 or day>NOW.date() or day<NOW.date()-dt.timedelta(days=10):
  raise ValueError('匯率或日期不合理')
 fx=rate
 old['fxDate']=str(day)
 old['fxSource']='Frankfurter (reference rate)'
 messages.append(f'USD/TWD 更新成功：{day}，{rate}')
except Exception as e:messages.append('USD/TWD 失敗，保留原值：'+str(e))

result=dict(old)
result.update({'updatedAt':updated_at,'checkedAt':NOW.isoformat(timespec='seconds'),'prices':prices,'priceDates':dates,'sources':sources,'funds':funds,'status':'；'.join(messages)})
if fx is not None:result['fx']=fx
FILE.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(result['status'])
