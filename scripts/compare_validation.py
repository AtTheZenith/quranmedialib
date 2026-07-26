#!/usr/bin/env python3
"""Compares v2 and v3 rendered output pixel by pixel.

Usage:
    uv run scripts/compare_validation.py
"""

from __future__ import annotations

import json
import os

from PIL import Image, ImageChops


def compare_dirs(v2_dir: str, v3_dir: str, report_dir: str) -> bool:
    os.makedirs(report_dir, exist_ok=True)

    with open(os.path.join(v2_dir, "results.json")) as f:
        v2_results: list[dict] = json.load(f)
    with open(os.path.join(v3_dir, "results.json")) as f:
        v3_results: list[dict] = json.load(f)

    v2_files = {r["scenario"]: r for r in v2_results}
    v3_files = {r["scenario"]: r for r in v3_results}

    all_pass = True
    report: dict = {
        "scenarios": [],
        "summary": {"total": 0, "identical": 0, "different": 0, "errors": 0},
    }

    for scenario in sorted(set(list(v2_files.keys()) + list(v3_files.keys()))):
        entry: dict = {"scenario": scenario}
        r2 = v2_files.get(scenario)
        r3 = v3_files.get(scenario)

        if r2 is None or r3 is None:
            entry["status"] = "missing"
            entry["detail"] = f"v2: {r2}, v3: {r3}"
            all_pass = False
            report["summary"]["errors"] += 1
            report["scenarios"].append(entry)
            continue

        if r2["status"] == "error" or r3["status"] == "error":
            entry["status"] = "error"
            entry["v2_error"] = r2.get("error")
            entry["v3_error"] = r3.get("error")
            all_pass = False
            report["summary"]["errors"] += 1
            report["scenarios"].append(entry)
            continue

        if r2["pages"] != r3["pages"]:
            entry["status"] = "page_count_mismatch"
            entry["v2_pages"] = r2["pages"]
            entry["v3_pages"] = r3["pages"]
            all_pass = False
            report["summary"]["different"] += 1
            report["scenarios"].append(entry)
            continue

        report["summary"]["total"] += 1
        scenario_pass = True
        page_diffs: list[dict] = []

        for i in range(r2["pages"]):
            v2_file = os.path.join(v2_dir, f"{scenario}_p{i}.png")
            v3_file = os.path.join(v3_dir, f"{scenario}_p{i}.png")

            v2_img = Image.open(v2_file)
            v3_img = Image.open(v3_file)

            if v2_img.size != v3_img.size:
                page_diffs.append({
                    "page": i,
                    "issue": "size_mismatch",
                    "v2_size": v2_img.size,
                    "v3_size": v3_img.size,
                })
                scenario_pass = False
                continue

            if list(v2_img.getdata()) != list(v3_img.getdata()):
                diff = ImageChops.difference(v2_img, v3_img)
                bbox = diff.getbbox()

                diff_pixels = sum(
                    1 for p in diff.getdata() if any(c != 0 for c in (p if isinstance(p, tuple) else (p,)))
                )
                total_pixels = diff.size[0] * diff.size[1]

                diff.save(os.path.join(report_dir, f"{scenario}_p{i}_diff.png"))

                page_diffs.append({
                    "page": i,
                    "issue": "pixel_mismatch",
                    "diff_pixels": diff_pixels,
                    "total_pixels": total_pixels,
                    "diff_percent": round(diff_pixels / total_pixels * 100, 4),
                    "bbox": list(bbox) if bbox else None,
                })
                scenario_pass = False
            else:
                page_diffs.append({"page": i, "status": "identical"})

        if scenario_pass:
            entry["status"] = "identical"
            report["summary"]["identical"] += 1
        else:
            entry["status"] = "different"
            entry["page_diffs"] = page_diffs
            all_pass = False
            report["summary"]["different"] += 1

        report["scenarios"].append(entry)

    report["all_pass"] = all_pass
    with open(os.path.join(report_dir, "validation_report.json"), "w") as f:
        json.dump(report, f, indent=2)

    print(f"{'=' * 60}")
    print(f"VALIDATION REPORT")
    print(f"{'=' * 60}")
    print(f"Total scenarios: {report['summary']['total']}")
    print(f"Identical:       {report['summary']['identical']}")
    print(f"Different:       {report['summary']['different']}")
    print(f"Errors:          {report['summary']['errors']}")
    print(f"All pass:        {report['all_pass']}")
    print(f"{'=' * 60}")

    if not all_pass:
        for s in report["scenarios"]:
            if s["status"] != "identical":
                print(f"\n! {s['scenario']}: {s['status']}")
                if "page_diffs" in s:
                    for d in s["page_diffs"]:
                        if d.get("issue") == "pixel_mismatch":
                            print(f"  Page {d['page']}: {d['diff_pixels']}/{d['total_pixels']} pixels differ ({d['diff_percent']}%)")
                        elif d.get("issue") == "size_mismatch":
                            print(f"  Page {d['page']}: size {d['v2_size']} vs {d['v3_size']}")
                        elif d.get("issue") == "page_count_mismatch":
                            print(f"  Pages: {d.get('v2_pages')} vs {d.get('v3_pages')}")

    return all_pass


def main() -> None:
    base = "./output/validation"
    v2_dir = os.path.join(base, "v2")
    v3_dir = os.path.join(base, "v3")
    report_dir = os.path.join(base, "report")
    compare_dirs(v2_dir, v3_dir, report_dir)


if __name__ == "__main__":
    main()
