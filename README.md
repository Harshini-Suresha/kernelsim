# KernelSim — operating system simulator

Interactive OS simulator: CPU scheduling (FCFS, SJF/SRTF, Priority,
Round Robin, MLFQ), virtual-memory page replacement (FIFO, LRU, OPT),
Banker's deadlock avoidance, race conditions, dining philosophers,
memory allocation, disk scheduling, Amdahl's law and page-table costs.

## Live links

- **Website (GitHub Pages):** https://harshini-suresha.github.io/kernelsim/
- **Streamlit app:** https://kernelsim.streamlit.app/
- **Source code:** https://github.com/Harshini-Suresha/kernelsim
- **Notebook in Colab:**
  https://colab.research.google.com/github/Harshini-Suresha/kernelsim/blob/main/KernelSim.ipynb
- **Notebook file (.ipynb):**
  https://github.com/Harshini-Suresha/kernelsim/blob/main/KernelSim.ipynb

## What's what (the two apps are different)

| File | What it is | Where it runs |
|---|---|---|
| `index.html` | Static website, simulations re-implemented in JavaScript, runs in the browser (live runner, time-travel debugger, sound, games, pager, crash lab, shell) | GitHub Pages (free, no server) |
| `app.py` + `kernelsim.py` | Interactive Streamlit app, Python/pandas/matplotlib, 8 tabs incl. live runner | Streamlit Community Cloud |
| `KernelSim.ipynb` | Notebook with every analysis step by step | Colab / Jupyter |
| `kernelsim.py` | Core Python: scheduling, page replacement, Banker's, race/dining, allocation, disk, Amdahl, benchmarks | Imported by `app.py` and the notebook |

The static site and the Streamlit app cover the same OS concepts with
**different implementations**: JavaScript in the browser vs Python on a
server. Results match on the same inputs (same algorithms, same defaults:
P1–P4 = (0,5),(1,3),(2,8),(3,6); reference string `7 0 1 2 0 3 0 4 …`; frames = 3).

## Run locally

```bash
pip install -r requirements.txt

# Streamlit app
streamlit run app.py

# Static website (just open it, no server needed)
open index.html

# Notebook
jupyter notebook KernelSim.ipynb
```

## Push to GitHub

```bash
git init
git add index.html app.py kernelsim.py KernelSim.ipynb requirements.txt README.md .gitignore
git commit -m "KernelSim: website, Streamlit app, notebook"
git branch -M main
git remote add origin https://github.com/Harshini-Suresha/kernelsim.git
git push -u origin main
```

## Turn on the website (GitHub Pages)

1. Push (above).
2. GitHub repo → **Settings → Pages**.
3. **Source:** Deploy from a branch → **Branch:** `main`, folder `/ (root)`.
4. Save. Site is live at `https://Harshini-Suresha.github.io/kernelsim/` in ~1 min.

## Deploy the Streamlit app (separate from the website)

1. Push (above) — Streamlit Cloud reads from GitHub.
2. Go to https://share.streamlit.io → **New app** → pick repo `kernelsim`, branch `main`,
   **Main file path:** `app.py`.
3. Deploy. Live at https://kernelsim.streamlit.app/ — already linked from
   `index.html` (Links section) and the Live links above.

## Open in Colab

No setup needed once pushed. Just visit:

```
https://colab.research.google.com/github/Harshini-Suresha/kernelsim/blob/main/KernelSim.ipynb
```

Contact: harshinisuresha7@gmail.com
