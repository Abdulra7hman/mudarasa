"""SUS scores and task times from the user test (eval/usertest/*.csv). Usage: python -m eval.usertest.sus"""
import csv
import pathlib
import statistics as st

HERE = pathlib.Path(__file__).resolve().parent


def main():
    sus = []
    for r in csv.DictReader(open(HERE / "sus.csv", encoding="utf-8")):
        try:
            a = [int(r[f"q{i}"]) for i in range(1, 11)]
        except (ValueError, KeyError):
            continue
        sus.append(2.5 * sum((x - 1) if i % 2 == 0 else (5 - x) for i, x in enumerate(a)))
    print(f"SUS: n={len(sus)}" + (f", mean {st.mean(sus):.1f}, min {min(sus):.0f}, max {max(sus):.0f}" if sus else ""))
    rows = [r for r in csv.DictReader(open(HERE / "results.csv", encoding="utf-8")) if r["seconds"].strip()]
    for tool in ("mudarasa", "turath", "shamela"):
        t = [r for r in rows if r["tool"] == tool]
        if t:
            ok = sum(r["success"].strip().lower() in ("1", "yes", "نعم", "y") for r in t)
            print(f"{tool}: {ok}/{len(t)} tasks succeeded; median time to source {st.median(float(r['seconds']) for r in t):.0f} s")


if __name__ == "__main__":
    main()
