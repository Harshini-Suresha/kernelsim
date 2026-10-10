import time
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from kernelsim import (Proc, schedule, page_replace, bankers, effective_access_time,
                       cpu_utilisation, race, dining, allocate, page_size_overhead,
                       optimal_page_size, monte_carlo, disk_schedule, amdahl, page_table_kb, simulate_ticks)

st.set_page_config(page_title="KernelSim", layout="wide")
st.title("KernelSim")
st.caption("Interactive OS simulator: CPU scheduling and virtual-memory page replacement.")

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
    ["CPU scheduling", "Page replacement", "Deadlock", "Memory performance", "Concurrency",
     "Allocation & paging cost", "Benchmarks & storage", "Live runner"])

with tab1:
    default = pd.DataFrame({"PID": ["P1", "P2", "P3", "P4"], "Arrival": [0, 1, 2, 3],
                            "Burst": [5, 3, 8, 6], "Priority": [2, 1, 3, 2]})
    st.write("Edit the process table (add or remove rows as needed).")
    df = st.data_editor(default, num_rows="dynamic", use_container_width=True)
    c1, c2, c3 = st.columns(3)
    algos = c1.multiselect("Algorithms", ["FCFS", "SJF", "Priority", "RR", "MLFQ"],
                           default=["FCFS", "SJF", "RR", "MLFQ"])
    quantum = c2.slider("Round Robin quantum", 1, 10, 2)
    pre = c3.checkbox("Preemptive SJF / Priority", value=False)
    df = df.dropna()
    procs = [Proc(str(r.PID), int(r.Arrival), int(r.Burst), int(r.Priority)) for r in df.itertuples()]
    if procs and algos:
        cmp = {}
        colors = plt.cm.Set3.colors
        for a in algos:
            g, rows, s = schedule(procs, a, quantum=quantum, preemptive=pre)
            cmp[a] = s
            st.subheader(a)
            fig, ax = plt.subplots(figsize=(10, 1.2))
            ids = [p.pid for p in procs]
            for pid, s0, e0 in g:
                col = "#dddddd" if pid == "idle" else colors[ids.index(pid) % 12]
                ax.barh(0, e0 - s0, left=s0, color=col, edgecolor="k")
                ax.text((s0 + e0) / 2, 0, pid, ha="center", va="center", fontsize=8)
            ax.set_yticks([]); ax.set_xlabel("time")
            st.pyplot(fig); plt.close(fig)
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.subheader("Comparison")
        cdf = pd.DataFrame(cmp).T
        st.dataframe(cdf.round(2), use_container_width=True)
        st.bar_chart(cdf[["Avg waiting", "Avg turnaround", "Avg response"]])

with tab2:
    refs_txt = st.text_input("Reference string", "7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1")
    frames = st.slider("Frames", 1, 10, 3)
    try:
        refs = [int(x) for x in refs_txt.replace(",", " ").split()]
    except ValueError:
        refs = []; st.error("Use whole numbers separated by spaces or commas.")
    if refs:
        res = {}
        for a in ["FIFO", "LRU", "OPT"]:
            steps, f, fr, hr = page_replace(refs, frames, a)
            res[a] = {"Faults": f, "Fault rate %": round(fr * 100, 1), "Hit rate %": round(hr * 100, 1)}
            with st.expander(f"{a}: {f} faults", expanded=(a == "LRU")):
                table = pd.DataFrame({
                    "Ref": [s["ref"] for s in steps],
                    **{f"Frame {i+1}": [s["frames"][i] if i < len(s["frames"]) else "-" for s in steps]
                       for i in range(frames)},
                    "Fault": ["fault" if s["fault"] else "hit" for s in steps],
                    "Evicted": [s["evicted"] if s["evicted"] is not None else "" for s in steps]}).T
                st.dataframe(table, use_container_width=True)
        st.dataframe(pd.DataFrame(res).T, use_container_width=True)
        sweep = pd.DataFrame({a: [page_replace(refs, k, a)[1] for k in range(1, 11)]
                              for a in ["FIFO", "LRU", "OPT"]}, index=range(1, 11))
        sweep.index.name = "frames"
        st.write("Faults vs. number of frames (watch for Belady's anomaly under FIFO)")
        st.line_chart(sweep)

with tab3:
    st.subheader("Banker's algorithm")
    av = st.selectbox("Available resources (R1 R2 R3)", ["3 3 2", "2 2 1", "1 1 1", "0 0 0"])
    avail = [int(x) for x in av.split()]
    safe, order, trace, need = bankers(avail)
    from kernelsim import BANKER_ALLOC, BANKER_MAX
    st.dataframe(pd.DataFrame({"Allocated": [str(a) for a in BANKER_ALLOC],
                               "Max": [str(m) for m in BANKER_MAX],
                               "Still needs": [str(n) for n in need]},
                              index=[f"P{i}" for i in range(5)]), use_container_width=True)
    if safe:
        st.success("Safe state. One order that works: " + " then ".join(order))
    else:
        stuck = [f"P{i}" for i in range(5) if f"P{i}" not in order]
        st.error(f"Unsafe state. {', '.join(stuck)} cannot finish, so deadlock is possible.")
    if trace:
        st.write("Safe-sequence trace")
        st.dataframe(pd.DataFrame([{"Runs to completion": p, "Free before": str(b), "Free after release": str(a)}
                                   for p, b, a in trace]), use_container_width=True, hide_index=True)

with tab4:
    st.subheader("Effective memory access time")
    c1, c2, c3 = st.columns(3)
    hit = c1.slider("TLB hit ratio (%)", 50, 100, 90)
    tlb_ns = c2.number_input("TLB lookup (ns)", 0, 1000, 10)
    mem_ns = c3.number_input("Memory access (ns)", 1, 10000, 100)
    e = effective_access_time(hit / 100, tlb_ns, mem_ns)
    st.metric("Effective access time", f"{e:.1f} ns", f"{(e / mem_ns - 1) * 100:.0f}% slower than one memory access",
              delta_color="inverse")
    xs = list(range(50, 101, 5))
    st.line_chart(pd.DataFrame({"EAT (ns)": [effective_access_time(x / 100, tlb_ns, mem_ns) for x in xs]}, index=xs))
    st.subheader("CPU utilisation vs degree of multiprogramming")
    ns = list(range(1, 11))
    st.line_chart(pd.DataFrame({f"{int(p * 100)}% I/O wait": [100 * cpu_utilisation(p, n) for n in ns]
                                for p in (0.2, 0.5, 0.8)}, index=ns))

with tab5:
    st.subheader("Race condition: two threads, 1,000 increments each")
    if st.button("Run 10 new trials") or "race" not in st.session_state:
        st.session_state.race = pd.DataFrame({"No lock": [race(False) for _ in range(10)],
                                              "With mutex": [race(True) for _ in range(10)]}, index=range(1, 11))
    st.bar_chart(st.session_state.race)
    st.caption(f"Average without a lock: {st.session_state.race['No lock'].mean():.0f} of 2000. With a mutex: always 2000.")
    st.subheader("Dining philosophers")
    runs = 200
    res = {s: [dining(s, 300) for _ in range(runs)] for s in ("naive", "ordered")}
    for s_name, r in res.items():
        dead = sorted(d for _, d, _ in r if d is not None)
        st.write(f"**{s_name}**: deadlocked in {len(dead)} of {runs} runs"
                 + (f", median at step {dead[len(dead) // 2]}" if dead else ""))
    st.line_chart(pd.DataFrame({k: v[0][0] for k, v in res.items()}))
    st.caption("Meals eaten over time in one sample run per strategy. The naive strategy stalls "
               "once every philosopher holds one fork.")

with tab6:
    st.subheader("Memory allocation strategies")
    blocks, reqs = [100, 500, 200, 300, 600], [212, 417, 112, 426]
    st.write(f"Free blocks (KB): {blocks}. Requests (KB): {reqs}.")
    fig, axes = plt.subplots(3, 1, figsize=(9, 6), sharex=True)
    rows = []
    for ax, strat in zip(axes, ["first", "best", "worst"]):
        rem, placed, failed = allocate(blocks, reqs, strat)
        for k, b in enumerate(blocks):
            left = 0
            for i, q in placed[k]:
                ax.barh(k, q, left=left, color=plt.cm.Set2.colors[i], edgecolor="k")
                ax.text(left + q / 2, k, f"R{i + 1}", ha="center", va="center", fontsize=8)
                left += q
            ax.barh(k, b - left, left=left, color="none", edgecolor="gray", linestyle="--")
        ax.set_title(f"{strat}-fit", loc="left", fontsize=10)
        ax.set_yticks(range(len(blocks))); ax.set_yticklabels([f"{b} KB" for b in blocks]); ax.invert_yaxis()
        rows.append({"Strategy": f"{strat}-fit", "Placed": len(reqs) - len(failed),
                     "Failed": ", ".join(f"R{i + 1} ({reqs[i]} KB)" for i in failed) or "none",
                     "Free left (KB)": sum(rem), "Largest free chunk (KB)": max(rem)})
    axes[-1].set_xlabel("KB")
    st.pyplot(fig); plt.close(fig)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.subheader("Choosing a page size")
    c1, c2 = st.columns(2)
    proc_kb = c1.number_input("Process size (KB)", 16, 1048576, 1024)
    entry = c2.number_input("Page-table entry size (bytes)", 1, 64, 8)
    sizes = [2 ** k for k in range(8, 17)]
    ov = [page_size_overhead(proc_kb * 1024, entry, p) for p in sizes]
    st.line_chart(pd.DataFrame(ov, columns=["Page table", "Internal fragmentation", "Total"], index=sizes))
    best = optimal_page_size(proc_kb * 1024, entry)
    st.info(f"Total overhead is lowest near {best:,.0f} bytes per page (square root of 2 x process size x entry size).")

with tab7:
    st.subheader("Scheduler benchmark on random workloads")
    n = st.slider("Random workloads", 50, 1000, 300, step=50)
    res, wins = monte_carlo(n, seed=1)
    summary = pd.DataFrame({a: {"Mean waiting": pd.Series(r["wait"]).mean(),
                                "Median waiting": pd.Series(r["wait"]).median(),
                                "90th percentile waiting": pd.Series(r["wait"]).quantile(.9),
                                "Mean response": pd.Series(r["resp"]).mean(),
                                "Lowest waiting in % of workloads": 100 * wins[a] / n}
                            for a, r in res.items()}).T.round(2)
    st.dataframe(summary, use_container_width=True)
    st.bar_chart(summary[["Mean waiting", "Mean response"]])
    st.caption("Ties count as a win for every tied algorithm, so percentages can add up to more than 100.")

    st.subheader("Disk scheduling")
    c1, c2 = st.columns([3, 1])
    reqs_txt = c1.text_input("Cylinder requests (0-199)", "98 183 37 122 14 124 65 67")
    head = c2.number_input("Head position", 0, 199, 53)
    try:
        dreqs = [int(x) for x in reqs_txt.replace(",", " ").split()]
    except ValueError:
        dreqs = []; st.error("Use whole numbers separated by spaces or commas.")
    if dreqs:
        fig, ax = plt.subplots(figsize=(9, 3.5))
        totals = {}
        for a, label in [("FCFS", "FCFS"), ("SSTF", "SSTF"), ("SCAN", "SCAN"), ("CSCAN", "C-SCAN")]:
            path, tot = disk_schedule(dreqs, head, a)
            totals[label] = tot
            ax.plot(range(len(path)), path, marker="o", label=f"{label} ({tot})")
        ax.set_xlabel("step"); ax.set_ylabel("cylinder"); ax.legend(); ax.grid(alpha=.3)
        st.pyplot(fig); plt.close(fig)
        st.bar_chart(pd.Series(totals, name="Total head movement"))

    st.subheader("Amdahl's law")
    cores = [1, 2, 4, 8, 16, 32, 64]
    st.line_chart(pd.DataFrame({f"{int(p * 100)}% parallel": [amdahl(p, c) for c in cores]
                                for p in (0.5, 0.9, 0.95, 0.99)}, index=cores))

    st.subheader("Page-table memory: flat vs two-level")
    used = [4, 16, 64, 256, 1024, 4096]
    tabs = [page_table_kb(u) for u in used]
    st.line_chart(pd.DataFrame({"Flat (KB)": [t[0] for t in tabs], "Two-level (KB)": [t[1] for t in tabs]},
                               index=[f"{u} MB" for u in used]))
    st.caption("32-bit addresses, 4 KB pages, 4-byte entries, mapped memory contiguous. "
               "Two-level tables win until nearly the whole address space is in use.")

with tab8:
    st.subheader("Live runner")
    st.write("Edit the processes, choose an algorithm, then drag the time slider or press Play to watch the CPU tick by tick.")
    live = st.data_editor(pd.DataFrame({"Arrival": [0, 1, 2, 3], "Burst": [5, 3, 8, 6], "Priority": [2, 1, 3, 2]},
                                       index=["P1", "P2", "P3", "P4"]),
                          num_rows="dynamic", use_container_width=True, key="live_table")
    c1, c2, c3 = st.columns(3)
    names = {"FCFS": "FCFS", "SJF": "SJF", "SRTF": "SRTF (preemptive SJF)", "PRIO": "Priority",
             "PRIO-P": "Priority (preemptive)", "RR": "Round Robin", "MLFQ": "MLFQ"}
    algo = c1.selectbox("Algorithm", list(names), index=5, format_func=names.get)
    quantum = c2.slider("Quantum (Round Robin)", 1, 10, 2, key="live_q")
    delay = c3.select_slider("Play speed", ["slow", "normal", "fast"], value="normal")
    live = live.dropna()
    lp = [Proc(str(i), int(r.Arrival), max(1, int(r.Burst)), int(r.Priority)) for i, r in live.iterrows()]
    if lp:
        sim = simulate_ticks(lp, algo, quantum)
        frames, end = sim["frames"], sim["end"]
        colors = plt.cm.Set3.colors
        t_sel = st.slider("Time", 0, end, 0, key="live_t")
        play = st.button("Play from start")
        holder = st.empty()

        def draw(t):
            f = frames[t]
            with holder.container():
                a, b, c = st.columns(3)
                a.metric("Clock", f"t = {t}")
                b.metric("CPU", lp[f["run"]].pid if f["run"] >= 0 else ("idle" if t < end else "all done"))
                c.metric("Ready queue", " > ".join(lp[i].pid for i in f["ready"]) or "empty")
                fig, ax = plt.subplots(figsize=(10, 1.4))
                for k in range(t):
                    r = frames[k]["run"]
                    if r >= 0:
                        ax.barh(0, 1, left=k, color=colors[r % 12], edgecolor="k")
                        ax.text(k + .5, 0, lp[r].pid, ha="center", va="center", fontsize=7)
                ax.axvline(t, color="r"); ax.set_xlim(0, end); ax.set_yticks([]); ax.set_xlabel("time")
                st.pyplot(fig); plt.close(fig)
                rows = []
                for i, p in enumerate(lp):
                    state = ("done" if f["rem"][i] == 0 else "running" if f["run"] == i
                             else "waiting" if p.arrival <= t else "not arrived")
                    rows.append({"Process": p.pid, "State": state, "Remaining": f["rem"][i], "Burst": p.burst})
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        if play:
            gap = {"slow": 1.0, "normal": 0.5, "fast": 0.15}[delay]
            for k in range(end + 1):
                draw(k); time.sleep(gap)
        else:
            draw(t_sel)
        if t_sel == end and not play:
            n = len(lp)
            tat = [sim["fin"][i] - p.arrival for i, p in enumerate(lp)]
            st.write("Final metrics")
            st.dataframe(pd.DataFrame({"Completion": sim["fin"], "Turnaround": tat,
                                       "Waiting": [tat[i] - p.burst for i, p in enumerate(lp)],
                                       "Response": [sim["first"][i] - p.arrival for i, p in enumerate(lp)]},
                                      index=[p.pid for p in lp]), use_container_width=True)
