"""Labelling sheet: 50 random Ibn Qasim notes (seed 42) from the fixed linking, for a human check of precision.

Adapted from prep/step2_extraction/make_label_sheet.py; the prep sheet was built from notes attached by the buggy
page lookup and must not be used. Output (gitignored, quotes the books): eval/linking/linking_sample_50.csv
Run: python -m eval.linking.make_label_sheet      Score: python -m eval.linking.make_label_sheet --score
"""
import csv
import json
import pathlib
import random
import sys

from app import books as B

HERE = pathlib.Path(__file__).resolve().parent
SHEET = HERE / "linking_sample_50.csv"
HEAD = ["م", "حاشية ابن قاسم: الجزء", "حاشية ابن قاسم: الصفحة", "رقم الحاشية", "الكلمات التي عليها رقم الحاشية",
        "نص الحاشية كاملا", "الروض المربع (ط الرسالة): الصفحة المربوطة", "مقطع الروض المربوط (المتن بين قوسين ثم الشرح)",
        "طريقة الربط", "رابط صفحة الحاشية", "رابط صفحة الروض", "الربط صحيح؟ (نعم/لا)", "ملاحظة (إن كان خطأ: أين موضعها الصحيح)"]
METHOD = {"exact": "تطابق تام", "exact_span": "تطابق تام عبر مقطعين متجاورين", "fuzzy": "تطابق تقريبي",
          "struct": "بترتيب المتن", "title": "عنوان الباب"}


def make():
    rows = json.loads((B.DATA / "build/iq_links.json").read_text(encoding="utf-8"))
    units = json.loads((B.DATA / "build/study.json").read_text(encoding="utf-8"))["units"]
    random.seed(42)
    sample = random.sample(rows, 50)
    with open(SHEET, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(HEAD)
        for i, x in enumerate(sample, 1):
            u = units.get(x["anchor_unit"]) or {}
            p = B.page(12216, x["pg"])
            ap = B.page(1679, u["pg"]) if u else {}
            w.writerow([i, p["vol"], p["page"], x["n"], x["lemma"], x["note"], ap.get("page", ""), u.get("text", "").strip(),
                        METHOD.get(x["method"], x["method"]), B.turath_link(12216, x["pg"]),
                        B.turath_link(1679, u["pg"]) if u else "", "", ""])
    print("written", SHEET)


def score():
    with open(SHEET, encoding="utf-8-sig") as f:
        labels = [r[11].strip() for r in list(csv.reader(f))[1:]]
    done = [l for l in labels if l]
    yes = sum(l in ("نعم", "yes", "y", "1") for l in done)
    print(f"labelled {len(done)}/50; correct {yes}/{len(done)}" + (f" = {yes / len(done):.0%}" if done else ""))


if __name__ == "__main__":
    score() if "--score" in sys.argv else make()
