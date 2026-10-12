import json
import pathlib
import datetime
import urllib.request

FILE = pathlib.Path(__file__).with_name("quotes.json")
TZ = datetime.timezone(datetime.timedelta(hours=8))
now = datetime.datetime.now(TZ).isoformat(timespec="seconds")
old = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}

prices = old.get("prices", {}).copy()
sources = old.get("sources", {}).copy()
price_dates = old.get("priceDates", {}).copy()
messages = []

try:
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        rows = json.load(response)

    row = next((x for x in rows if x.get("Code") == "00757"), None)
    if not row:
        raise ValueError("證交所資料沒有 00757")

    price = float(str(row["ClosingPrice"]).replace(",", ""))
    raw_date = str(row["Date"]).strip()
    if len(raw_date) != 7 or not raw_date.isdigit():
        raise ValueError("交易日期格式無法確認")
    trade_date = f"{int(raw_date[:3])+1911:04d}-{raw_date[3:5]}-{raw_date[5:7]}"
    datetime.date.fromisoformat(trade_date)

    if price <= 0:
        raise ValueError("收盤價無效")

    previous_date = price_dates.get("00757", "")
    if previous_date and trade_date < previous_date:
        raise ValueError("來源日期比已保存的報價更舊")

    prices["00757"] = price
    price_dates["00757"] = trade_date
    sources["00757"] = "TWSE STOCK_DAY_ALL"
    messages.append(f"00757 更新成功：{trade_date}，NT$ {price}")
except Exception as exc:
    messages.append(f"00757 更新失敗，保留舊資料：{exc}")

result = {
    "updatedAt": now if "00757 更新成功" in messages[0] else old.get("updatedAt", "尚未取得已驗證報價"),
    "checkedAt": now,
    "prices": prices,
    "priceDates": price_dates,
    "sources": sources,
    "status": "；".join(messages) + "；其他三檔基金尚未串接。",
}
FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(result["status"])
