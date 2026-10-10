"""KernelSim core: CPU scheduling + page replacement simulators."""
from dataclasses import dataclass
from typing import List, Tuple, Dict


@dataclass
class Proc:
    pid: str
    arrival: int
    burst: int
    priority: int = 1


def _metrics(procs, finish, first, gantt):
    rows = []
    for p in procs:
        tat = finish[p.pid] - p.arrival
        rows.append({"PID": p.pid, "Arrival": p.arrival, "Burst": p.burst,
                     "Priority": p.priority, "Completion": finish[p.pid],
                     "Turnaround": tat, "Waiting": tat - p.burst,
                     "Response": first[p.pid] - p.arrival})
    end = max(finish.values())
    busy = sum(e - s for pid, s, e in gantt if pid != "idle")
    n = len(rows)
    summary = {"Avg waiting": sum(r["Waiting"] for r in rows) / n,
               "Avg turnaround": sum(r["Turnaround"] for r in rows) / n,
               "Avg response": sum(r["Response"] for r in rows) / n,
               "Throughput": n / end,
               "CPU utilisation %": 100 * busy / end}
    return rows, summary


def _push(g, pid, s, e):
    if g and g[-1][0] == pid and g[-1][2] == s:
        g[-1] = (pid, g[-1][1], e)
    else:
        g.append((pid, s, e))


def schedule(procs: List[Proc], algo: str, quantum: int = 2,
             mlfq_quanta=(2, 4, 8), preemptive: bool = False):
    """Returns (gantt[(pid,start,end)], rows, summary). algo in
    FCFS, SJF, Priority, RR, MLFQ. preemptive applies to SJF (SRTF) / Priority."""
    rem = {p.pid: p.burst for p in procs}
    first, finish, g = {}, {}, []
    t, done = 0, 0
    n = len(procs)
    by = {p.pid: p for p in procs}

    if algo in ("RR", "MLFQ"):
        levels = len(mlfq_quanta) if algo == "MLFQ" else 1
        q = [[] for _ in range(levels)]
        lvl = {p.pid: 0 for p in procs}
        arrived = set()

        def admit(upto):
            for p in sorted(procs, key=lambda x: (x.arrival, x.pid)):
                if p.arrival <= upto and p.pid not in arrived:
                    arrived.add(p.pid); q[0].append(p.pid)
        admit(t)
        while done < n:
            cur = next((i for i in range(levels) if q[i]), None)
            if cur is None:
                nxt = min(p.arrival for p in procs if p.pid not in arrived)
                _push(g, "idle", t, nxt); t = nxt; admit(t); continue
            pid = q[cur].pop(0)
            slice_ = (mlfq_quanta[cur] if algo == "MLFQ" else quantum)
            run = min(slice_, rem[pid])
            first.setdefault(pid, t)
            _push(g, pid, t, t + run); t += run; rem[pid] -= run
            admit(t)
            if rem[pid] == 0:
                finish[pid] = t; done += 1
            elif algo == "MLFQ":
                nl = min(cur + 1, levels - 1); lvl[pid] = nl; q[nl].append(pid)
            else:
                q[0].append(pid)
    else:
        key = {"FCFS": lambda p: (p.arrival, p.pid),
               "SJF": lambda p: (rem[p.pid], p.arrival),
               "Priority": lambda p: (p.priority, p.arrival)}[algo]
        pre = preemptive and algo != "FCFS"
        while done < n:
            ready = [p for p in procs if p.arrival <= t and rem[p.pid] > 0]
            if not ready:
                nxt = min(p.arrival for p in procs if rem[p.pid] > 0)
                _push(g, "idle", t, nxt); t = nxt; continue
            p = min(ready, key=key)
            first.setdefault(p.pid, t)
            if pre:
                fut = [x.arrival for x in procs if x.arrival > t]
                run = min(rem[p.pid], (min(fut) - t) if fut else rem[p.pid])
            else:
                run = rem[p.pid]
            _push(g, p.pid, t, t + run); t += run; rem[p.pid] -= run
            if rem[p.pid] == 0:
                finish[p.pid] = t; done += 1
    rows, summary = _metrics(procs, finish, first, g)
    return g, rows, summary


def page_replace(refs: List[int], frames: int, algo: str):
    """algo in FIFO, LRU, OPT. Returns (steps, faults, fault_rate, hit_rate).
    steps: list of dicts {ref, frames, fault, evicted}."""
    mem: List[int] = []
    last: Dict[int, int] = {}
    steps, faults = [], 0
    for i, r in enumerate(refs):
        fault, ev = r not in mem, None
        if fault:
            faults += 1
            if len(mem) == frames:
                if algo == "FIFO":
                    ev = mem.pop(0)
                elif algo == "LRU":
                    ev = min(mem, key=lambda x: last[x]); mem.remove(ev)
                else:  # OPT
                    def nxt(x):
                        try: return refs.index(x, i + 1)
                        except ValueError: return float("inf")
                    ev = max(mem, key=nxt); mem.remove(ev)
            mem.append(r)
        last[r] = i
        steps.append({"ref": r, "frames": list(mem), "fault": fault, "evicted": ev})
    n = len(refs)
    return steps, faults, faults / n, 1 - faults / n


# ---------------------------------------------------------------- deadlock
import random

BANKER_ALLOC = [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]]
BANKER_MAX = [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]]


def bankers(available, alloc=BANKER_ALLOC, mx=BANKER_MAX):
    """Banker's safety algorithm. Returns (safe, order, trace, need).
    trace rows: (process, free_before, free_after)."""
    need = [[m - a for m, a in zip(mr, ar)] for mr, ar in zip(mx, alloc)]
    work, done, trace = list(available), [], []
    while len(done) < len(alloc):
        i = next((k for k in range(len(alloc)) if k not in done
                  and all(n <= w for n, w in zip(need[k], work))), None)
        if i is None:
            break
        before = list(work)
        work = [w + a for w, a in zip(work, alloc[i])]
        trace.append((f"P{i}", before, list(work)))
        done.append(i)
    return len(done) == len(alloc), [f"P{i}" for i in done], trace, need


# ------------------------------------------------------- memory performance
def effective_access_time(hit, tlb_ns=10, mem_ns=100):
    """Single-level page table: a TLB miss costs one extra memory access."""
    return hit * (tlb_ns + mem_ns) + (1 - hit) * (tlb_ns + 2 * mem_ns)


def cpu_utilisation(io_wait, n):
    """Classic model: utilisation = 1 - p**n for n processes each waiting on I/O a fraction p."""
    return 1 - io_wait ** n


# ------------------------------------------------------------- concurrency
def race(lock, n=1000, threads=2, rng=random):
    """Final value of a shared counter when each thread increments it n times.
    Each increment is load, add, store; without a lock the steps interleave."""
    c, reg, pc = 0, [0] * threads, [0] * threads
    left, holder = [n] * threads, -1
    while any(left):
        act = [i for i in range(threads) if left[i] and (not lock or holder < 0 or holder == i)]
        i = rng.choice(act)
        if lock and holder < 0 and pc[i] == 0:
            holder = i
        if pc[i] == 0:
            reg[i] = c
        elif pc[i] == 1:
            reg[i] += 1
        else:
            c = reg[i]; left[i] -= 1
            if lock:
                holder = -1
        pc[i] = (pc[i] + 1) % 3
    return c


def dining(strategy="naive", steps=300, n=5, seed=None):
    """Dining philosophers under random scheduling. strategy: naive | ordered.
    Returns (meals_over_time, deadlock_step_or_None, final_states) where
    states are 0 thinking, 1 holding first fork, 2 eating."""
    rng = random.Random(seed)
    owner, state, meals, hist, dead = [None] * n, [0] * n, 0, [], None
    for t in range(steps):
        if dead is None and all(s == 1 for s in state):
            dead = t
        i = rng.randrange(n)
        l, r = i, (i + 1) % n
        a, b = (l, r) if strategy == "naive" else (min(l, r), max(l, r))
        if state[i] == 0 and owner[a] is None:
            owner[a] = i; state[i] = 1
        elif state[i] == 1 and owner[b] is None:
            owner[b] = i; state[i] = 2
        elif state[i] == 2:
            owner[a] = owner[b] = None; state[i] = 0; meals += 1
        hist.append(meals)
    return hist, dead, state


# ------------------------------------------------------ memory allocation
def allocate(blocks, requests, strategy="first"):
    """Contiguous allocation into free blocks. strategy: first | best | worst.
    Returns (remaining_per_block, placed_per_block[(request_idx, size)], failed_request_idxs)."""
    rem = list(blocks)
    placed = [[] for _ in blocks]
    failed = []
    for i, q in enumerate(requests):
        cand = [(r, k) for k, r in enumerate(rem) if r >= q]
        if not cand:
            failed.append(i)
            continue
        if strategy == "first":
            r, k = cand[0]
        elif strategy == "best":
            r, k = min(cand)
        else:
            r, k = max(cand, key=lambda x: (x[0], -x[1]))
        rem[k] -= q
        placed[k].append((i, q))
    return rem, placed, failed


def page_size_overhead(proc_bytes, entry_bytes, page_bytes):
    """Returns (page_table_bytes, internal_fragmentation_bytes, total) for one process."""
    table = proc_bytes * entry_bytes / page_bytes
    frag = page_bytes / 2
    return table, frag, table + frag


def optimal_page_size(proc_bytes, entry_bytes):
    return (2 * proc_bytes * entry_bytes) ** 0.5


# -------------------------------------------------------------- benchmarks
def gen_workload(rng):
    """Random workload of 4-5 processes with no idle gaps (arrival <= work queued so far)."""
    n = rng.randint(4, 5)
    S, a, out = 0, 0, []
    for i in range(n):
        b = rng.randint(2, 9)
        a = 0 if i == 0 else a + rng.randint(0, S - a)
        out.append(Proc(f"P{i + 1}", a, b, rng.randint(1, 4)))
        S += b
    return out


def monte_carlo(n=300, seed=None, algos=("FCFS", "SJF", "Priority", "RR", "MLFQ")):
    """Run every scheduler on n random workloads.
    Returns (results[algo] = {'wait': [...], 'resp': [...]}, wins[algo]) where a win is the lowest
    average waiting time (ties count for every tied algorithm)."""
    rng = random.Random(seed)
    res = {a: {"wait": [], "resp": []} for a in algos}
    wins = dict.fromkeys(algos, 0)
    for _ in range(n):
        w = gen_workload(rng)
        ws = {}
        for a in algos:
            _, _, s = schedule(w, a)
            res[a]["wait"].append(s["Avg waiting"])
            res[a]["resp"].append(s["Avg response"])
            ws[a] = s["Avg waiting"]
        m = min(ws.values())
        for a in algos:
            wins[a] += ws[a] == m
    return res, wins


# --------------------------------------------------------- disk scheduling
def disk_schedule(requests, head, algo="FCFS", disk_size=200):
    """algo: FCFS | SSTF | SCAN (sweeps down first) | CSCAN (sweeps up, wraps to 0).
    Returns (path, total_head_movement)."""
    reqs = list(requests)
    upper = sorted(r for r in reqs if r > head)
    lower = sorted((r for r in reqs if r <= head), reverse=True)
    if algo == "FCFS":
        order = reqs
    elif algo == "SSTF":
        left, pos, order = reqs[:], head, []
        while left:
            nxt = min(left, key=lambda r: abs(r - pos))
            left.remove(nxt); order.append(nxt); pos = nxt
    elif algo == "SCAN":
        order = lower + ([0] if lower and upper else []) + upper
    else:
        order = upper + ([disk_size - 1, 0] + lower[::-1] if lower else [])
    path = [head] + order
    return path, sum(abs(a - b) for a, b in zip(path, path[1:]))


# ------------------------------------------------- parallel speedup, tables
def amdahl(parallel_fraction, cores):
    return 1 / ((1 - parallel_fraction) + parallel_fraction / cores)


def page_table_kb(used_mb, va_bits=32, page_kb=4, entry_bytes=4):
    """Memory for a flat page table vs a two-level one when used_mb of address space is mapped
    contiguously. Returns (flat_kb, two_level_kb)."""
    entries = page_kb * 1024 // entry_bytes
    flat = 2 ** va_bits // (page_kb * 1024) * entry_bytes / 1024
    l2 = min(entries, -(-used_mb * 1024 // (page_kb * entries)))
    return flat, page_kb + l2 * page_kb


# ---------------------------------------------------------------- live runner
def simulate_ticks(procs, algo="RR", quantum=2):
    """Tick-by-tick CPU simulation for the live runners.
    algo: FCFS | SJF | SRTF | PRIO | PRIO-P | RR | MLFQ  (SRTF and PRIO-P are preemptive).
    Returns {'frames': [...], 'first': [...], 'fin': [...], 'end': int}. frames[t] is the state at
    the START of tick t: {'t', 'run' (index or -1), 'ready' (indices, next first), 'rem', 'level'};
    the last frame is the final state after every process has finished."""
    n = len(procs)
    rem = [p.burst for p in procs]
    first, fin = [None] * n, [None] * n
    qs, q, ml, lvl = (2, 4, 8), [], [[], [], []], [0] * n
    cur, slice_, pend, t, done, frames = -1, 0, -1, 0, 0, []
    pre = algo in ("SRTF", "PRIO-P")
    by_rem = lambda i: (rem[i], procs[i].arrival)
    by_pri = lambda i: (procs[i].priority, procs[i].arrival)
    key = {"FCFS": lambda i: (procs[i].arrival,), "SJF": by_rem, "SRTF": by_rem,
           "PRIO": by_pri, "PRIO-P": by_pri}.get(algo)
    while done < n and t < 10000:
        for i, p in enumerate(procs):
            if p.arrival == t:
                (q if algo == "RR" else ml[0]).append(i) if algo in ("RR", "MLFQ") else None
        if pend >= 0:
            (q if algo == "RR" else ml[lvl[pend]]).append(pend)
            pend = -1
        ready = [i for i in range(n) if procs[i].arrival <= t and rem[i] > 0]
        run = -1
        if algo == "RR":
            if cur >= 0: run = cur
            elif q: run, slice_ = q.pop(0), 0
        elif algo == "MLFQ":
            if cur >= 0: run = cur
            else:
                l = next((k for k in range(3) if ml[k]), None)
                if l is not None: run, slice_ = ml[l].pop(0), 0
        elif cur >= 0 and not pre:
            run = cur
        elif ready:
            run = min(ready, key=key)
            if cur >= 0 and pre and cur in ready and key(cur) == key(run): run = cur
        if algo == "RR": waiting = list(q)
        elif algo == "MLFQ": waiting = [i for lv in ml for i in lv]
        else: waiting = sorted((i for i in ready if i != run), key=key)
        frames.append({"t": t, "run": run, "ready": waiting, "rem": list(rem),
                       "level": lvl[run] if run >= 0 else 0})
        cur = run
        if run >= 0:
            if first[run] is None: first[run] = t
            rem[run] -= 1; slice_ += 1
            if rem[run] == 0:
                fin[run] = t + 1; done += 1; cur = -1
            elif algo == "RR" and slice_ >= quantum:
                pend, cur = run, -1
            elif algo == "MLFQ" and slice_ >= qs[lvl[run]]:
                lvl[run] = min(lvl[run] + 1, 2); pend, cur = run, -1
        t += 1
    frames.append({"t": t, "run": -1, "ready": [], "rem": list(rem), "level": 0})
    return {"frames": frames, "first": first, "fin": fin, "end": t}
