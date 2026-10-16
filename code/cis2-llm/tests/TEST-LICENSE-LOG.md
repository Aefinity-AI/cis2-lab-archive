# LLM-3 licensing test log (2026-09-17T20:46:58Z)

```
== cis2-llm licensing test ==
workdir: /tmp/tmp.2SCnKCsSle

-- keygen --
backend=cryptography
wrote private key: /tmp/tmp.2SCnKCsSle/priv.pem
wrote public key:  /tmp/tmp.2SCnKCsSle/pub.pem

-- issue (valid, far-future expiry) --
issued license -> /tmp/tmp.2SCnKCsSle/lic-ok.json
{
  "expiry": "2099-01-01",
  "format_version": 1,
  "instance_id": "inst-1",
  "issued": "2026-09-17T20:46:57Z",
  "issuer": "AEFINITY AI INC.",
  "licensee": "Test Co",
  "max_receipts_per_day": 1000,
  "tier": "per-instance"
}

-- verify (expect OK) --
OK: valid, expires 2099-01-01

-- tamper one byte in the license file, verify (expect INVALID) --
diff:
1,13c1
< {
<   "license": {
<     "expiry": "2099-01-01",
<     "format_version": 1,
<     "instance_id": "inst-1",
<     "issued": "2026-09-17T20:46:57Z",
<     "issuer": "AEFINITY AI INC.",
<     "licensee": "Test Co",
<     "max_receipts_per_day": 1000,
<     "tier": "per-instance"
<   },
<   "sig": "qgse7PbYoxAxEhvdeMd/ZGMAn5ZwWZmArWHb8yoYl+7OJMywbdmcSkwylsEhE38BtKap4KHYonL/ZTZ7n36oDA=="
< }
---
> {"license": {"expiry": "2099-01-01", "format_version": 1, "instance_id": "inst-1-FORGED", "issued": "2026-09-17T20:46:57Z", "issuer": "AEFINITY AI INC.", "licensee": "Test Co", "max_receipts_per_day": 1000, "tier": "per-instance"}, "sig": "qgse7PbYoxAxEhvdeMd/ZGMAn5ZwWZmArWHb8yoYl+7OJMywbdmcSkwylsEhE38BtKap4KHYonL/ZTZ7n36oDA=="}
\ No newline at end of file
INVALID: signature verification failed: 

-- issue with past expiry, verify (expect EXPIRED) --
issued license -> /tmp/tmp.2SCnKCsSle/lic-expired.json
{
  "expiry": "2020-01-01",
  "format_version": 1,
  "instance_id": "inst-2",
  "issued": "2026-09-17T20:46:57Z",
  "issuer": "AEFINITY AI INC.",
  "licensee": "Test Co",
  "max_receipts_per_day": 10,
  "tier": "eval"
}
EXPIRED: license expired 2020-01-01

PASS: keygen/issue/verify-OK/tamper-INVALID/expired-EXPIRED all as expected.
```
