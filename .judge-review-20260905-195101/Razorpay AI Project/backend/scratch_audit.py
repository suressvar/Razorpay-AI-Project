import urllib.request
import json

BASE = "http://127.0.0.1:8000"

def request(path, method="GET", data=None, headers=None):
    url = f"{BASE}{path}"
    hdrs = headers or {}
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    hdrs.setdefault("Accept", "application/json")
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read().decode("utf-8")
            res_data = json.loads(raw) if "json" in content_type else raw
            return resp.status, res_data, None
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        return e.code, None, err_msg
    except Exception as e:
        return 0, None, str(e)

endpoints_to_test = [
    ("Health", "/health", "GET", None, None),
    ("Metrics Summary", "/metrics/summary", "GET", None, None),
    ("Evaluation Metrics", "/metrics/evaluation", "GET", None, None),
    ("Cases List", "/cases?limit=5", "GET", None, None),
    ("Unmatched Webhooks", "/webhooks/unmatched", "GET", None, None),
    ("Copilot Info", "/copilot", "GET", None, None),
    ("Copilot Chat", "/copilot/chat", "POST", {"query": "Explain failure for case"}, None),
    ("Copilot V2 Investigate", "/copilot/v2/investigate", "POST", {"query": "Investigate payment failure"}, None),
    ("Copilot V2 Context", "/copilot/v2/context", "POST", {"current_page": "/cases"}, None),
    ("Copilot V2 Issues List", "/copilot/v2/issues", "GET", None, None),
    ("Copilot V2 Automation Status", "/copilot/v2/automation/status", "GET", None, None),
    ("Automation Check Mismatch", "/copilot/v2/automation/check/payment-mismatch", "POST", None, None),
    ("Automation Check SLA", "/copilot/v2/automation/check/issue-sla", "POST", None, None),
    ("Admin Kill-Switch Status", "/admin/kill-switch/status", "GET", None, None),
    ("Admin Audit Logs", "/admin/audit-logs", "GET", None, None),
]

print("=== Running Backend Endpoints Audit ===")
failures = []
for name, path, method, data, hdrs in endpoints_to_test:
    status, res, err = request(path, method, data, hdrs)
    if 200 <= status < 300:
        print(f"[OK {status}] {name} ({method} {path})")
    else:
        print(f"[FAIL {status}] {name} ({method} {path}): {err}")
        failures.append((name, path, status, err))

# Test dynamic workflow: Case Detail, Audit, Notifications, Approve, Reject
status, cases, err = request("/cases?limit=1")
if status == 200 and cases and len(cases) > 0:
    case_id = cases[0]["case_id"]
    print(f"\nTesting specific case endpoints for {case_id}:")
    for sub, meth in [("", "GET"), ("/audit", "GET"), ("/notifications", "GET")]:
        st, res, err = request(f"/cases/{case_id}{sub}", meth)
        if 200 <= st < 300:
            print(f"[OK {st}] Case {sub or 'detail'}")
        else:
            print(f"[FAIL {st}] Case {sub or 'detail'}: {err}")
            failures.append((f"Case {sub}", f"/cases/{case_id}{sub}", st, err))

# Test dynamic workflow: Email draft & get
print("\nTesting email draft generation & retrieval:")
st, draft, err = request("/copilot/v2/email/draft", "POST", {
    "template_id": "payment_link",
    "recipient_email": "test@example.com",
    "recipient_name": "Test Customer",
    "variables": {"amount": "1,500.00", "payment_link": "https://rzp.io/i/test1234"}
})
if st == 200 and draft and "draft_id" in draft:
    draft_id = draft["draft_id"]
    print(f"[OK {st}] Email draft generated: {draft_id}")
    st2, draft_ret, err2 = request(f"/copilot/v2/email/draft/{draft_id}")
    if st2 == 200:
        print(f"[OK {st2}] Email draft retrieved")
    else:
        print(f"[FAIL {st2}] Email draft retrieve: {err2}")
        failures.append(("Get Draft", f"/copilot/v2/email/draft/{draft_id}", st2, err2))
else:
    print(f"[FAIL {st}] Email draft creation: {err}")
    failures.append(("Create Draft", "/copilot/v2/email/draft", st, err))

print(f"\n=== Audit Complete: {len(failures)} failures found ===")
