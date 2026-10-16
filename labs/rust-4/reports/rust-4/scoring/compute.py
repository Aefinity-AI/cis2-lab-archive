#!/usr/bin/env python3
# rust-4 scoring: recompute every figure from rows.jsonl, result.json, run.log, FEED/job.json, local payload and penguin build files. No ssh. Writes figs.json.
import json, os, re, hashlib, statistics, glob, subprocess, sys
R = '<root>/state/'
D = R + 'reports/rust-lab/rust-4/'
FEED = R + 'feed/'
PAY = os.path.expanduser('~/feed-payload/rust4')
PAYRUN = os.path.expanduser('~/feed-payload/rust4-run')
M4B = os.path.expanduser('~/scratch-rust4/m4build')
HOSTS = ['box1', 'box2', 'box3', 'box4', 'box5']
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()
def med(v): return statistics.median(v)
F = {}
# ---- pins appendix constants (copied from the amended text, then compared)
APP = {'R': 'd0f8ec89e4f63c6ed37fb6d5416662e3b56e740b202126d8f8637cb5cb6e6503', 'C': '5a6ccc32ec04ca14d831f6b508bb69822ea51c6f16b7305f601dd87a056e1fd8',
       'witness': 'ecafd089d17bb72e7ec9e7196dfbf7cb2f1539936ebeae71911379860c7e79e9', 'wheelhouse': '21360ef99c777608fc5e0b3e13bf8d898cbfad6970b11701c36f80ee390e738e',
       'run_py': 'b71fb02c613d2b16', 'frozen_full': '697610dd05e120a3cffceef1cc483aa4cb384676a06294201dfe763b63d67e94', 'frozen_lite': 'ea2b972e09cf0ab84f26e0ff0462c7aff2dc82c01a265a83caa1ac2132d14b85'}
# ---- amended bar integrity
bars = open(R + 'plans/rust-lab/bars/rust-4.txt').read().rstrip('\n'); pins = open(D + 'PINS.txt').read().strip()
F['amended_bar_sha256_recomputed'] = hashlib.sha256((bars + '\n\n' + pins).encode()).hexdigest()
F['registered_bar_file_sha256_stripped'] = hashlib.sha256(bars.encode()).hexdigest()
# ---- payload and runner, local copies
F['payload_list_sha_full'] = sha(PAY + '/PAYLOAD_SHA256'); F['payload_list_sha_lite'] = sha(PAYRUN + '/PAYLOAD_SHA256')
F['run_py_sha_full'] = sha(PAY + '/run.py'); F['run_py_sha_lite'] = sha(PAYRUN + '/run.py')
def check_list(root):
    bad = 0; n = 0
    for l in open(root + '/PAYLOAD_SHA256').read().splitlines():
        h, _, fn = l.partition('  '); n += 1
        if not os.path.exists(os.path.join(root, fn)) or sha(os.path.join(root, fn)) != h: bad += 1
    return n, bad
F['payload_files_checked'] = {'full': check_list(PAY), 'lite': check_list(PAYRUN)}
F['bin_local'] = {k: {'bytes': os.path.getsize(PAY + '/bin/' + n), 'sha256': sha(PAY + '/bin/' + n)} for k, n in (('R', 'R_cis2_ref'), ('C', 'C_sv5_driver'))}
F['m1_ratio_s'] = F['bin_local']['R']['bytes'] / F['bin_local']['C']['bytes']
# ---- per host
H = {}
for h in HOSTS:
    d = D + h + '/'
    rj = json.load(open(d + 'result.json'))
    rt = open(d + 'RESULT.txt').read().splitlines()[0]
    log = open(d + 'run.log').read().splitlines()
    rows = [json.loads(l) for l in open(d + 'rows.jsonl')]
    fj = json.load(open(FEED + 'cm-%s/done/rust4-%s/job.json' % (h, h))); ff = json.load(open(FEED + 'cm-%s/done/rust4-%s/FEED.json' % (h, h)))
    o = {'result_word': rt.split()[1], 'rj_keys': sorted(rj.keys()), 'feed_status': ff['status'], 'feed_result_equals_RESULT_txt': ff['result_line'] == rt, 'job': fj}
    # RESULT.txt vs result.json consistency
    o['rj_word'] = rj.get('verdict') or rj.get('word') or rj.get('result')
    o['elapsed_job_s_recorded'] = rj.get('elapsed_job_s')
    start = re.search(r'start=(\S+)', log[0]).group(1)
    from datetime import datetime
    def t(s): return datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ')
    ts = []
    for r in rows:
        for k in ('before', 'after'):
            if r.get(k, {}).get('t'): ts.append(r[k]['t'])
    for l in log:
        m = re.search(r'HOSTCHECK close (\{.*\})', l)
        if m: ts.append(json.loads(m.group(1))['t'])
    o['start'] = start; o['end_last_stamp'] = max(ts)
    o['elapsed_from_log_s'] = (t(max(ts)) - t(start)).total_seconds()
    # baseline recompute
    b = rj['baseline']; w = b['windows']
    ba = max(x[0] for x in w); bh = max(x[1] for x in w)
    o['baseline'] = {'base_arm': ba, 'base_host': bh, 'limit_arm': max(0.02, round(ba + 0.02, 4)), 'limit_host': max(0.10, round(bh + 0.05, 4)), 'rj_limit_arm': b['limit_arm'], 'rj_limit_host': b['limit_host'],
                     'ok_vs_max': (ba <= 0.15 and bh <= 0.30), 'match': (max(0.02, round(ba + 0.02, 4)) == b['limit_arm'] and max(0.10, round(bh + 0.05, 4)) == b['limit_host'])}
    # rows accounting
    acc = {}
    for r in rows:
        key = (r['phase'], r['arm'], r['status'], r.get('reason', ''))
        acc[str(key)] = acc.get(str(key), 0) + 1
    o['row_counts'] = acc
    o['n_rows'] = len(rows)
    o['discards_rows'] = sum(1 for r in rows if r['status'] == 'DISCARD'); o['voids_rows'] = sum(1 for r in rows if r['status'] == 'VOID')
    o['discards_recorded'] = rj.get('discards'); o['voids_recorded'] = rj.get('voids')
    o['install'] = [{'rep': r['rep'], 'status': r['status'], 'wall_to_exit_s': r['wall_to_exit_s'], 'mhz_ref': r['detail']['mhz_ref'], 'mhz_low': r['detail']['mhz_rep_low'],
                     'drop_pct': round(100 * (1 - r['detail']['mhz_rep_low'] / r['detail']['mhz_ref']), 1), 'thr_changed': r['detail']['thr_changed'], 'foreign': r['detail']['foreign'],
                     'limit_arm': r['detail']['limit_arm'], 'rc': r['rc'], 'maxrss_kb': r['maxrss_kb']} for r in rows if r['phase'] == 'install']
    o['install_kept_s_from_rows'] = [round(r['wall_to_exit_s'], 2) for r in rows if r['phase'] == 'install' and r['status'] == 'KEPT']
    o['m2_cache'] = [{'arm': r['arm'], 'status': r['status'], 'before_kb': r.get('cached_kb_before'), 'after_kb': r.get('cached_kb_after'),
                      'fall_pct': round(100 * (1 - r['cached_kb_after'] / r['cached_kb_before']), 1)} for r in rows if r['phase'] == 'm2']
    # per-row hygiene: any kept row above limits?
    hyg = []
    for r in rows:
        if r.get('detail'):
            f = r['detail']['foreign']; hyg.append((r['phase'], r['arm'], r['rep'], r['status'], f['foreign_arm'], r['detail']['limit_arm'], f['foreign_host'], r['detail']['limit_host']))
    o['kept_rows_over_limit'] = [x for x in hyg if x[3] == 'KEPT' and ((x[4] or 0) > x[5] or (x[6] or 0) > x[7])]
    o['rows_over_limit_any'] = [x for x in hyg if ((x[4] or 0) > x[5] or (x[6] or 0) > x[7])]
    o['load_before_max'] = max([r['before']['load'][0] for r in rows if r.get('before')] or [0]); o['load_after_max'] = max([r['after']['load'][0] for r in rows if r.get('after')] or [0])
    o['load_before_rows'] = [(r['phase'], r['arm'], r['rep'], r['before']['load'][0]) for r in rows if r.get('before')]
    o['thr_values'] = sorted({str(r['before']['thr']) for r in rows if r.get('before')} | {str(r['after']['thr']) for r in rows if r.get('after')})
    o['scaling_changed_any'] = any(r['detail']['scaling_max_changed'] for r in rows if r.get('detail'))
    # box1 build rows
    o['m3_rows'] = [{'arm': r['arm'], 'rep': r['rep'], 'status': r['status'], 'wall_to_exit_s': r['wall_to_exit_s'], 'rc': r['rc'], 'maxrss_kb': r['maxrss_kb'], 'mhz_n': r['detail']['mhz_n'], 'foreign': r['detail']['foreign'], 'limit_arm': r['detail']['limit_arm'], 'limit_host': r['detail']['limit_host'], 'after_load': r['after']['load'][0], 'before_load': r['before']['load'][0], 'thr': r['after']['thr']} for r in rows if r['phase'] == 'm3']
    o['m3_json'] = rj.get('m3'); o['p_json'] = rj.get('p'); o['m2_json'] = rj.get('m2'); o['tools'] = rj.get('tools')
    o['m1_json'] = {'bytes': rj.get('m1_bytes_shipped'), 'sha256': rj.get('m1_sha256_shipped')}
    o['payload_sha'] = rj.get('payload_sha256'); o['frozen_sha'] = rj.get('frozen_payload_sha256'); o['run_py'] = rj.get('run_py_sha256')
    o['notrun'] = rj.get('notrun'); o['timers_paused'] = rj.get('timers_paused'); o['timers_restored'] = rj.get('timers_restored'); o['phases'] = rj.get('phases')
    o['reason'] = rj.get('reason'); o['gate_witness'] = rj.get('gate_witness')
    o['wheelhouse'] = (o['p_json'] or {}).get('wheelhouse_sha256_here'); o['cpu_line'] = [l for l in log if l.startswith('host=')][0]
    o['rj_top'] = {k: rj[k] for k in rj if k in ('host', 'job')}
    # raw timed/ files present?
    o['timed_files'] = sorted(os.listdir(d + 'timed')); o['builds_files'] = sorted(os.listdir(d + 'builds')) if os.path.isdir(d + 'builds') else []
    H[h] = o
F['hosts'] = H
# ---- cost cap
F['elapsed_sum_recorded_s'] = sum(H[h]['elapsed_job_s_recorded'] for h in HOSTS)
F['elapsed_sum_from_log_s'] = sum(H[h]['elapsed_from_log_s'] for h in HOSTS)
# ---- M3 box1 recompute
b1 = H['box1']['m3_rows']
Rs = [x['wall_to_exit_s'] for x in b1 if x['arm'] == 'R']; Cs = [x['wall_to_exit_s'] for x in b1 if x['arm'] == 'C']
F['m3'] = {'R_s_rows': Rs, 'C_s_rows': Cs, 'R_med': med(Rs), 'C_med': med(Cs), 't': med(Rs) / med(Cs), 't_rounded_figs': 190.56 / 2.2,
           't_per_rep_min': min(Rs) / max(Cs), 't_per_rep_max': max(Rs) / min(Cs), 'R_hashes': H['box1']['m3_json']['R_sha256'], 'C_hashes': H['box1']['m3_json']['C_sha256'],
           'R_bytes': H['box1']['m3_json']['R_bytes'], 'C_bytes': H['box1']['m3_json']['C_bytes'], 'netns': H['box1']['m3_json']['netns'], 'jobs': H['box1']['m3_json']['jobs'],
           'rows_kept_all': all(x['status'] == 'KEPT' and x['rc'] == 0 for x in b1)}
bl = D + 'box1/builds/'
F['m3']['flags'] = {n: open(bl + n).read() for n in ('R-FLAGS.txt', 'C-FLAGS.txt')}
F['m3']['err_sizes'] = {n: os.path.getsize(bl + n) for n in sorted(os.listdir(bl)) if n.endswith('.err')}
F['m3']['err_has_network_text'] = {n: bool(re.search(r'network|dns|resolve|connect|download|registry|Updating crates', open(bl + n).read(), re.I)) for n in sorted(os.listdir(bl)) if n.endswith('.err')}
F['m3']['out_C_sizes'] = {n: os.path.getsize(D + 'box1/timed/' + n) for n in ('m3-C-rep1.out', 'm3-C-rep2.out', 'm3-C-rep3.out')}
F['m3']['out_R_empty'] = all(os.path.getsize(D + 'box1/timed/m3-R-rep%d.out' % i) == 0 for i in (1, 2, 3))
F['m3']['C_out_dirs'] = [re.search(r"Entering directory '([^']+)'", open(D + 'box1/timed/m3-C-rep%d.out' % i).read()).group(1) for i in (1, 2, 3)]
F['m3']['musl_install_line'] = [l for l in open(D + 'box1/run.log').read().splitlines() if 'musl-tools install' in l]
F['m3']['tools_at_start'] = [l[:400] for l in open(D + 'box1/run.log').read().splitlines() if l.startswith('TOOLS')]
# ---- M4
pt = {}
for l in open(D + 'm4-penguin/penguin-m4.txt'):
    p = l.split()
    pt[' '.join(p[:-1])] = p[-1]
F['m4'] = {'penguin_txt': pt, 'penguin_recomputed': {'R1': sha(M4B + '/p1/outR/cis2_ref'), 'R2': sha(M4B + '/p2/outR/cis2_ref'), 'C1': sha(M4B + '/p1/outC/sv5_driver'), 'C2': sha(M4B + '/p2/outC/sv5_driver')},
           'penguin_sizes': {k: os.path.getsize(M4B + v) for k, v in (('R1', '/p1/outR/cis2_ref'), ('R2', '/p2/outR/cis2_ref'), ('C1', '/p1/outC/sv5_driver'), ('C2', '/p2/outC/sv5_driver'))},
           'box1_R': F['m3']['R_hashes'], 'box1_C': F['m3']['C_hashes'], 'shipped': APP}
four_R = [F['m4']['penguin_recomputed']['R1'], F['m4']['penguin_recomputed']['R2'], F['m3']['R_hashes'][0], F['m3']['R_hashes'][1]]
four_C = [F['m4']['penguin_recomputed']['C1'], F['m4']['penguin_recomputed']['C2'], F['m3']['C_hashes'][0], F['m3']['C_hashes'][1]]
F['m4']['R_identical'] = len(set(four_R)) == 1; F['m4']['C_identical'] = len(set(four_C)) == 1
F['m4']['R_distinct_all'] = len(set(four_R + [F['m3']['R_hashes'][2], APP['R']]))
F['m4']['C_distinct_all'] = len(set(four_C + [F['m3']['C_hashes'][2], APP['C']]))
F['m4']['label'] = {(True, True): 'BOTH', (True, False): 'RUST ONLY', (False, True): 'C ONLY', (False, False): 'NEITHER'}[(F['m4']['R_identical'], F['m4']['C_identical'])]
tc = open(D + 'm4-penguin/toolchain.txt').read()
F['m4']['toolchain_penguin'] = tc
t1 = H['box1']['tools']
F['m4']['tool_equal'] = {'rustc_commit': ('88d9e12ae178fab0fb5cc050a94da85685d449ea' in tc and '88d9e12ae178fab0fb5cc050a94da85685d449ea' in t1['rustc']),
                         'gcc': (tc.splitlines()[7] == t1['gcc']) if len(tc.splitlines()) > 7 else None, 'musl_tools': ('1.2.5-3.1~deb13u1' in tc and t1['musl_tools_pkg'] == '1.2.5-3.1~deb13u1'), 'penguin_gcc_line': tc.splitlines()[7], 'box1_gcc': t1['gcc']}
# diagnostic: penguin R1 vs R2 byte diff
a = open(M4B + '/p1/outR/cis2_ref', 'rb').read(); b = open(M4B + '/p2/outR/cis2_ref', 'rb').read()
dpos = [i for i in range(len(a)) if a[i] != b[i]]
F['m4']['diag_R_diff_bytes'] = len(dpos); F['m4']['diag_R_diff_ranges'] = [dpos[0], dpos[0] + 19, dpos[-1]] if dpos else []
F['m4']['diag_path_offset_p1'] = [m.start() for m in re.finditer(rb'scratch-rust4/m4build/p1/R', a)]
F['m4']['diag_equal_length'] = len(a) == len(b)
# ---- M5 and sources
lock = open(PAY + '/src/R/Cargo.lock').read()
F['m5'] = {'cargo_lock_packages': len(re.findall(r'^\[\[package\]\]', lock, re.M)), 'onig_in_lock': ('name = "onig"' in lock, 'name = "onig_sys"' in lock)}
vend = PAY + '/src/R/vendor'
nvend = len([x for x in os.listdir(vend) if os.path.isdir(os.path.join(vend, x))])
lines_v = 0; files_v = 0
for dp, dn, fn in os.walk(vend):
    for f in fn:
        if f.endswith('.rs'):
            files_v += 1
            with open(os.path.join(dp, f), 'rb') as fh: lines_v += sum(1 for _ in fh)
lines_p = 0
for dp, dn, fn in os.walk(PAY + '/src/R/src'):
    for f in fn:
        if f.endswith('.rs'):
            with open(os.path.join(dp, f), 'rb') as fh: lines_p += sum(1 for _ in fh)
lines_c = 0; files_c = 0
for dp, dn, fn in os.walk(PAY + '/src/C'):
    for f in fn:
        if f.endswith(('.c', '.h')):
            files_c += 1
            with open(os.path.join(dp, f), 'rb') as fh: lines_c += sum(1 for _ in fh)
F['m5'].update(vendor_dirs=nvend, vendor_rs_files=files_v, vendor_rs_lines=lines_v, program_rs_lines=lines_p, R_total_rs_lines=lines_v + lines_p, C_src_files=files_c, C_src_lines=lines_c)
req = [l for l in open(PAY + '/p/requirements.lock').read().splitlines() if l.strip() and not l.startswith(' ') and '==' in l]
wh = sorted(os.listdir(PAY + '/p/wheelhouse'))
F['p_local'] = {'requirements_lines': len(req), 'wheels': len(wh), 'wheel_bytes': sum(os.path.getsize(PAY + '/p/wheelhouse/' + w) for w in wh)}
lst = ''.join('%s  %s\n' % (sha(PAY + '/p/wheelhouse/' + w), w) for w in wh)
F['p_local']['wheelhouse_hash_recomputed'] = hashlib.sha256(lst.encode()).hexdigest()
F['p_local']['wheelhouse_file_hash'] = open(PAY + '/p/WHEELHOUSE_SHA256').read().splitlines()[0].split()[0]
json.dump(F, open(os.path.expanduser('~/scratch-score/rust4/figs.json'), 'w'), indent=1, default=str)
print('ok')
