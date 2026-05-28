import json
import time
import urllib.request
import urllib.error

API_URL = "https://script.google.com/macros/s/AKfycbzXtgU_bEQx-3B15FoV4SrolI1int0s6PUo9WKnHJ2Wz8zV5jq62MWNFQLjI51OqsWH/exec"

# (date, llc, total_amount)  →  split 50/50 into your_amount / partner_amount
rows = [
    ("2025-01-01", "Divando LLC",          10000),
    ("2025-02-01", "Divando LLC",          29366),
    ("2025-03-01", "Yale Townhomes, LLC",   3500),
    ("2025-03-01", "Dorado LLC",            7000),
    ("2025-03-01", "Divando LLC",           4500),
    ("2025-04-01", "Divando LLC",           6000),
    ("2025-05-01", "Divando LLC",           7500),
    ("2025-05-01", "Dorado LLC",            5000),
    ("2025-06-01", "Divando LLC",           2000),
    ("2025-06-01", "Yale Townhomes, LLC",   3000),
    ("2025-06-01", "Dorado LLC",            2500),
    ("2025-07-01", "Divando LLC",           6000),
    ("2025-07-01", "Yale Townhomes, LLC",   9000),
    ("2025-07-01", "Dorado LLC",            3300),
    ("2025-08-01", "5070 Donald, LLC",      3000),
    ("2025-08-01", "Divando LLC",           6500),
    ("2025-08-01", "Yale Townhomes, LLC",   5400),
    ("2025-08-01", "Dorado LLC",            4000),
    ("2025-09-01", "5070 Donald, LLC",      1600),
    ("2025-09-01", "Yale Townhomes, LLC",   1700),
    ("2025-09-01", "Dorado LLC",            4000),
    ("2025-09-01", "Divando LLC",          10000),
    ("2025-10-01", "Divando LLC",           9500),
    ("2025-10-01", "Dorado LLC",            3700),
    ("2025-11-01", "5070 Donald, LLC",          0),
    ("2025-11-01", "Divando LLC",               0),
    ("2025-11-01", "Yale Townhomes, LLC",        0),
    ("2025-11-01", "Dorado LLC",                0),
    ("2025-12-01", "Dorado LLC",            6200),
    ("2025-12-01", "5070 Donald, LLC",      7000),
    ("2025-12-01", "Divando LLC",          14000),
    ("2025-12-01", "Yale Townhomes, LLC",       0),
    ("2026-01-01", "5070 Donald, LLC",      3000),
    ("2026-01-01", "Dorado LLC",            3100),
    ("2026-02-01", "Divando LLC",           3750),
    ("2026-02-01", "Yale Townhomes, LLC",   1900),
    ("2026-02-01", "Dorado LLC",            1900),
    ("2026-03-01", "Yale Townhomes, LLC",   2500),
    ("2026-03-01", "5070 Donald, LLC",      3200),
    ("2026-03-01", "Divando LLC",           8000),
    ("2026-03-01", "Dorado LLC",            5200),
]

def post_json(payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(API_URL, data=body,
                                  headers={"Content-Type": "text/plain"}, method="POST")
    opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())

    class KeepPostOnRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            new_req = urllib.request.Request(newurl, data=req.data,
                                              headers=req.headers, method="POST")
            return new_req

    opener = urllib.request.build_opener(KeepPostOnRedirect())
    try:
        with opener.open(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

total = len(rows)
ok = 0
for i, (date, llc, amount) in enumerate(rows):
    half = round(amount / 2, 2)
    payload = {
        "action": "add_distribution",
        "date": date,
        "llc": llc,
        "your_amount": half,
        "partner_amount": half,
        "notes": "Historical import"
    }
    result = post_json(payload)
    status = "✅" if result.get("ok") else "❌ " + str(result.get("error", result))
    print(f"[{i+1}/{total}] {date} | {llc:<25} | ${amount:>8,.2f} → {half:,.2f} each  {status}")
    time.sleep(0.6)

print(f"\nDone. {ok}/{total} rows sent.")
