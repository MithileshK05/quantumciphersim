import urllib.request
import json
import time

def check(label, url, count=3):
    print(f"\n=== {label} ===")
    prev = None
    for i in range(count):
        r = urllib.request.urlopen(url)
        d = json.loads(r.read())
        same = "(SAME AS PREV - BUG!)" if prev and d["qber"] == prev["qber"] and d["key_rate"] == prev["key_rate"] else "(UNIQUE - OK)"
        print(f"  Call {i+1}: qber={d['qber']}, key_rate={d['key_rate']}, status={d['status']} {same}")
        prev = d
        time.sleep(0.15)

base = "http://localhost:8000/metrics/?"

check(
    "BB84 No Attack (baseline)",
    base + "noise_level=0.05&attack_probability=0.0&auto_mitigate=false&active_protocol=BB84"
)
check(
    "BB84 + Eve (compromised)",
    base + "noise_level=0.05&attack_probability=1.0&auto_mitigate=false&active_protocol=BB84"
)
check(
    "BB84 + Eve + PA Mitigation (KEY BUG FIX)",
    base + "noise_level=0.05&attack_probability=1.0&auto_mitigate=true&active_protocol=BB84"
)
check(
    "E91 No Attack",
    base + "noise_level=0.05&attack_probability=0.0&auto_mitigate=false&active_protocol=E91"
)
check(
    "E91 + Eve, No Mitigation (Bell Violation)",
    base + "noise_level=0.05&attack_probability=1.0&auto_mitigate=false&active_protocol=E91"
)
check(
    "E91 + Eve + Mitigation (Shielded)",
    base + "noise_level=0.05&attack_probability=1.0&auto_mitigate=true&active_protocol=E91"
)

print("\n=== DONE ===")
