import json
import time
from pathlib import Path

from config import Config
from building_graph import load_graph, get_all_room_ids
from dataset_utils import extract_label_from_filename
from localization import localize


def run_evaluation_benchmark() -> dict:
    """Run full evaluation benchmark on all dataset images."""
    print("=" * 65)
    print("  WayLens Evaluation Benchmark: Full Dataset Scan")
    print("=" * 65)

    graph = load_graph()
    valid_rooms = get_all_room_ids(graph)

    dataset_dirs = [Config.TRAIN_DIR, Config.VAL_DIR, Config.TEST_DIR]
    total_images = 0
    results = []

    stats = {
        "total": 0,
        "located": 0,
        "rescan": 0,
        "by_method": {"ocr": 0, "clip": 0, "none": 0},
        "by_split": {"train": {"total": 0, "located": 0}, "val": {"total": 0, "located": 0}, "test": {"total": 0, "located": 0}},
    }

    start_time = time.time()

    for d in dataset_dirs:
        split_name = d.name
        files = sorted([f for f in d.iterdir() if f.is_file() and f.suffix.lower() in (".jpeg", ".jpg", ".png")])

        for f in files:
            stats["total"] += 1
            stats["by_split"][split_name]["total"] += 1
            true_labels = extract_label_from_filename(f.name)

            t0 = time.time()
            node_id, conf, method, msg = localize(f, valid_rooms=valid_rooms, graph=graph)
            elapsed = time.time() - t0

            is_correct = (node_id in true_labels) if node_id != "rescan" else False

            if node_id != "rescan":
                stats["located"] += 1
                stats["by_split"][split_name]["located"] += 1

            stats["by_method"][method] = stats["by_method"].get(method, 0) + 1

            res_entry = {
                "file": f.name,
                "split": split_name,
                "true_labels": true_labels,
                "detected_node": node_id,
                "confidence": conf,
                "method": method,
                "is_correct": is_correct,
                "elapsed_sec": round(elapsed, 4),
            }
            results.append(res_entry)

    total_elapsed = time.time() - start_time
    avg_latency = total_elapsed / stats["total"] if stats["total"] > 0 else 0

    print(f"\nBenchmark Summary ({stats['total']} images processed in {total_elapsed:.2f}s):")
    print(f"  - Located: {stats['located']}/{stats['total']} ({(stats['located']/stats['total'])*100:.1f}%)")
    print(f"  - Rescan:  {stats['rescan']}/{stats['total']}")
    print(f"  - Method Breakdown: {stats['by_method']}")
    print(f"  - Avg Latency per scan: {avg_latency:.3f}s")

    for split, sdata in stats["by_split"].items():
        acc = (sdata['located']/sdata['total'])*100.0 if sdata['total'] > 0 else 0
        print(f"  - Split '{split:5s}': {sdata['located']}/{sdata['total']} ({acc:.1f}%)")

    # Save to logs
    Config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = Config.LOGS_DIR / "walk_test_report.json"

    report_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "stats": stats,
        "avg_latency_sec": round(avg_latency, 4),
        "total_elapsed_sec": round(total_elapsed, 2),
        "results": results,
    }

    with open(report_path, "w", encoding="utf-8") as out:
        json.dump(report_data, out, indent=2)

    print(f"\n✓ Report saved to {report_path}")
    print("=" * 65)

    return report_data


if __name__ == "__main__":
    run_evaluation_benchmark()
