#!/usr/bin/env python3
"""Elo tournament bookkeeping for the co-scientist skill.

Authoritative Elo lives in hypotheses.json (mirrored into tournament.json).
New hypotheses start at 1200. Standard logistic Elo with K (default 32).

Usage:
  python elo.py init      <run_dir>
  python elo.py add       <run_dir> <id> [--summary S] [--elo 1200]
  python elo.py ingest    <run_dir> <hypotheses.json> [--origin generation:debate]
  python elo.py match     <run_dir> <id_a> <id_b> <winner:1|2> [--type debate|single] [--k 32] [--round N]
  python elo.py setstatus <run_dir> <id> <new|reviewed|rejected|top>
  python elo.py proximity <run_dir> <graph.json>
  python elo.py rank      <run_dir> [--top N]

All writes are atomic (temp file + os.replace). Mutate state through THIS script and
SEQUENTIALLY — never hand-write the JSON or run two writers at once (it races/corrupts).
"""
import argparse, json, os, sys, tempfile, contextlib

try:
    import fcntl  # POSIX file locking (Linux/macOS/WSL). Absent on native Windows.
except ImportError:
    fcntl = None

START_ELO = 1200


def _p(run, name): return os.path.join(run, name)

def _load(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def _save(path, obj):
    # Atomic write with a UNIQUE temp file, then os.replace().
    #   - unique temp (mkstemp) so two concurrent writers never share/interleave the
    #     same scratch file — the original bug was a shared "<path>.tmp" getting two
    #     writers' bytes concatenated into one corrupt file.
    #   - os.replace is atomic on one filesystem, so a reader sees the whole old file
    #     or the whole new file, never a truncated one.
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".elo-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.remove(tmp)
        raise


@contextlib.contextmanager
def _locked(run_dir):
    # OS-level exclusive lock around a whole read-modify-write so concurrent writers
    # SERIALIZE instead of clobbering each other (prevents lost updates AND corruption).
    # This is belt-and-suspenders: the SKILL also tells the agent to mutate state
    # sequentially, but this makes a stray parallel call safe rather than catastrophic.
    if fcntl is None:
        yield  # no flock on this platform — rely on the skill's serialize-writes rule
        return
    os.makedirs(run_dir, exist_ok=True)
    lockpath = os.path.join(run_dir, ".lock")
    with open(lockpath, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def expected(ra, rb):
    return 1.0 / (1.0 + 10 ** ((rb - ra) / 400.0))


def cmd_init(a):
    os.makedirs(a.run_dir, exist_ok=True)
    h = _p(a.run_dir, "hypotheses.json")
    if not os.path.exists(h):
        _save(h, [])
    t = _p(a.run_dir, "tournament.json")
    if not os.path.exists(t):
        _save(t, {"elo": {}, "matches": [], "proximity": {}})
    print("initialized", a.run_dir)


def cmd_add(a):
    with _locked(a.run_dir):
        hp = _p(a.run_dir, "hypotheses.json")
        hyps = _load(hp, [])
        if any(x["id"] == a.id for x in hyps):
            print("exists", a.id); return
        hyps.append({"id": a.id, "summary": a.summary or "", "text": "",
                     "elo": a.elo, "status": "new", "parents": [], "origin": "",
                     "scores": {}})
        _save(hp, hyps)
        t = _load(_p(a.run_dir, "tournament.json"), {"elo": {}, "matches": []})
        t["elo"][a.id] = a.elo
        _save(_p(a.run_dir, "tournament.json"), t)
    print("added", a.id, "elo", a.elo)


def cmd_match(a):
    with _locked(a.run_dir):
        hp = _p(a.run_dir, "hypotheses.json")
        hyps = _load(hp, [])
        by = {x["id"]: x for x in hyps}
        if a.id_a not in by or a.id_b not in by:
            sys.exit(f"unknown id(s): {a.id_a} {a.id_b}")
        ra, rb = by[a.id_a].get("elo", START_ELO), by[a.id_b].get("elo", START_ELO)
        ea, eb = expected(ra, rb), expected(rb, ra)
        sa = 1.0 if a.winner == "1" else 0.0
        sb = 1.0 - sa
        na = round(ra + a.k * (sa - ea), 1)
        nb = round(rb + a.k * (sb - eb), 1)
        by[a.id_a]["elo"], by[a.id_b]["elo"] = na, nb
        _save(hp, hyps)
        t = _load(_p(a.run_dir, "tournament.json"), {"elo": {}, "matches": []})
        t.setdefault("elo", {}); t.setdefault("matches", [])
        t["elo"][a.id_a], t["elo"][a.id_b] = na, nb
        t["matches"].append({"round": a.round, "a": a.id_a, "b": a.id_b,
                             "type": a.type, "winner": a.id_a if sa else a.id_b, "k": a.k})
        _save(_p(a.run_dir, "tournament.json"), t)
    print(f"{a.id_a}: {ra}->{na}   {a.id_b}: {rb}->{nb}   winner={a.id_a if sa else a.id_b}")


def cmd_setstatus(a):
    """Mark a hypothesis reviewed|rejected|new|top WITHOUT hand-editing the JSON.
    Using this (instead of a Write to hypotheses.json) is what keeps a single,
    serialized writer on the file."""
    with _locked(a.run_dir):
        hp = _p(a.run_dir, "hypotheses.json")
        hyps = _load(hp, [])
        hit = next((x for x in hyps if x["id"] == a.id), None)
        if not hit:
            sys.exit(f"unknown id: {a.id}")
        hit["status"] = a.status
        _save(hp, hyps)
    print("status", a.id, "->", a.status)


def cmd_ingest(a):
    """Bulk-add hypotheses from a JSON file (an array of {summary,text,category,...}).
    Auto-assigns ids (h1, h2, ...) continuing after any existing ones, sets elo=1200
    and status=new. This is the safe way to persist a Generation/Evolution subagent's
    returned JSON — the orchestrator writes ONCE, through this command, instead of
    racing a hand-written Write against elo.py."""
    incoming = _load(a.json_file, None)
    if incoming is None:
        sys.exit(f"cannot read {a.json_file}")
    if isinstance(incoming, dict) and "hypotheses" in incoming:
        incoming = incoming["hypotheses"]
    if not isinstance(incoming, list):
        sys.exit("ingest expects a JSON array (or {\"hypotheses\":[...]})")
    with _locked(a.run_dir):
        hp = _p(a.run_dir, "hypotheses.json")
        hyps = _load(hp, [])
        n = 0
        for x in (h["id"] for h in hyps):
            if x.startswith("h") and x[1:].isdigit():
                n = max(n, int(x[1:]))
        t = _load(_p(a.run_dir, "tournament.json"), {"elo": {}, "matches": [], "proximity": {}})
        t.setdefault("elo", {})
        added = []
        for item in incoming:
            n += 1
            hid = f"h{n}"
            hyps.append({"id": hid, "summary": item.get("summary", ""),
                         "category": item.get("category", ""), "text": item.get("text", ""),
                         "elo": START_ELO, "status": "new",
                         "parents": item.get("parents", []), "origin": a.origin,
                         "scores": {}})
            t["elo"][hid] = START_ELO
            added.append(hid)
        _save(hp, hyps)
        _save(_p(a.run_dir, "tournament.json"), t)
    print("ingested", len(added), "->", ",".join(added))


def cmd_proximity(a):
    """Write the proximity graph (clusters/duplicates/pairs) into tournament.json
    from a JSON file, without touching the elo/matches the tournament owns."""
    graph = _load(a.json_file, None)
    if graph is None:
        sys.exit(f"cannot read {a.json_file}")
    with _locked(a.run_dir):
        t = _load(_p(a.run_dir, "tournament.json"), {"elo": {}, "matches": [], "proximity": {}})
        t["proximity"] = graph
        _save(_p(a.run_dir, "tournament.json"), t)
    print("proximity graph written:",
          len(graph.get("clusters", [])), "clusters,",
          len(graph.get("duplicates", [])), "dup-pairs")


def cmd_rank(a):
    hyps = _load(_p(a.run_dir, "hypotheses.json"), [])
    live = [x for x in hyps if x.get("status") != "rejected"]
    live.sort(key=lambda x: x.get("elo", START_ELO), reverse=True)
    top = live[: a.top] if a.top else live
    for i, x in enumerate(top, 1):
        print(f"{i:2}. [{x.get('elo', START_ELO):7.1f}] {x['id']:6} {x.get('summary','')[:90]}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("run_dir"); p.set_defaults(fn=cmd_init)
    p = sub.add_parser("add"); p.add_argument("run_dir"); p.add_argument("id")
    p.add_argument("--summary"); p.add_argument("--elo", type=float, default=START_ELO); p.set_defaults(fn=cmd_add)
    p = sub.add_parser("match"); p.add_argument("run_dir"); p.add_argument("id_a"); p.add_argument("id_b")
    p.add_argument("winner", choices=["1", "2"]); p.add_argument("--type", default="single")
    p.add_argument("--k", type=float, default=32.0); p.add_argument("--round", type=int, default=0); p.set_defaults(fn=cmd_match)
    p = sub.add_parser("setstatus"); p.add_argument("run_dir"); p.add_argument("id")
    p.add_argument("status", choices=["new", "reviewed", "rejected", "top"]); p.set_defaults(fn=cmd_setstatus)
    p = sub.add_parser("ingest"); p.add_argument("run_dir"); p.add_argument("json_file")
    p.add_argument("--origin", default="generation"); p.set_defaults(fn=cmd_ingest)
    p = sub.add_parser("proximity"); p.add_argument("run_dir"); p.add_argument("json_file"); p.set_defaults(fn=cmd_proximity)
    p = sub.add_parser("rank"); p.add_argument("run_dir"); p.add_argument("--top", type=int, default=0); p.set_defaults(fn=cmd_rank)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
