"""Conservative quote update: never invent prices; preserve only verified feeds."""
import json, datetime, pathlib, urllib.request
p=pathlib.Path(__file__).with_name('quotes.json')
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds')
old=json.loads(p.read_text()) if p.exists() else {}
# No unofficial or unverified mappings are treated as fund NAVs.
# Preserve previously verified data and its original timestamp, not today's check time.
prices=old.get('prices', {})
result={'updatedAt':old.get('updatedAt','尚未取得已驗證報價'),
        'checkedAt':now,'prices':prices,
        'status':'每日檢查已執行；尚未設定經驗證的四筆基金報價來源。',
        'sources':old.get('sources',{})}
p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(result['status'],now)
