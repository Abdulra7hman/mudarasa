"""Throwaway (prep): build the specialist's labelling sheet for 50 random Ibn Qasim notes (seed 42).

Input: results/q3_ibn_qasim.json (from analyse.py). Output: linking_sample_50.csv (UTF-8 with BOM, opens in Excel).
Full texts, no truncation; each row links to both pages on Turath.
"""
import csv
import json
import pathlib
import random

HERE = pathlib.Path(__file__).resolve().parent
rows = json.loads((HERE / "results/q3_ibn_qasim.json").read_text(encoding="utf-8"))["rows"]
random.seed(42)
sample = random.sample(rows, 50)

HEAD = ["م", "حاشية ابن قاسم: الجزء", "حاشية ابن قاسم: الصفحة", "رقم الحاشية",
        "الكلمات التي عليها رقم الحاشية", "نص الحاشية كاملا",
        "الروض المربع (ط الرسالة): الصفحة المربوطة", "مقطع الروض المربوط (المتن بين قوسين ثم الشرح)",
        "طريقة الربط", "رابط صفحة الحاشية", "رابط صفحة الروض",
        "الربط صحيح؟ (نعم/لا)", "ملاحظة (إن كان خطأ: أين موضعها الصحيح)"]
METHOD = {"exact": "تطابق تام", "exact_span": "تطابق تام عبر مقطعين متجاورين", "fuzzy": "تطابق تقريبي", "struct": "بترتيب المتن"}

with open(HERE / "linking_sample_50.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(HEAD)
    for i, x in enumerate(sample, 1):
        a = x["text_anchor"] or x["struct_anchor"] or {}
        method = x["text_link"] if x["text_anchor"] else "struct"
        w.writerow([
            i, x["iq_vol"], x["iq_page"], x["note"], x["lemma"], x["note_text"],
            a.get("page", ""), a.get("text", ""), METHOD.get(method, method),
            f"https://app.turath.io/book/12216?page={x['iq_pg']}",
            f"https://app.turath.io/book/1679?page={a['pg']}" if a.get("pg") else "",
            "", "",
        ])
print("written", len(sample))
