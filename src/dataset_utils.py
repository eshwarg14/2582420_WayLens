import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

from building_graph import load_graph, get_all_room_ids, get_all_node_ids, get_node_info
from config import Config

FILENAME_TO_NODE = {
    # Named landmarks with different naming in dataset vs graph
    "Dean_School_of_Commerce": ["Dept_of_Commerce"],
    "Dept_of_Mathematics": ["Dept_of_Math"],
    "Associate_Dean_School_of_Sciences": ["Assoc_Dean_Sciences"],

    # Combined room images (single image showing multiple room signs)
    "721_724": ["721", "724"],
}


def extract_label_from_filename(filename: str) -> list[str]:
    """Extract room/node label(s) from an image filename.

    Args:
        filename: The image filename (e.g., '501.jpeg', 'Seminar_Hall.jpeg',
                  '721_724.jpeg')

    Returns:
        List of node ID(s) this image maps to.
    """
    stem = Path(filename).stem  # Remove extension

    # Check explicit mapping first
    if stem in FILENAME_TO_NODE:
        return FILENAME_TO_NODE[stem]

    # Direct match: the stem IS the node ID (most common case)
    # e.g., "501", "507A", "709C", "Seminar_Hall", "Panel_Room"
    return [stem]


def scan_dataset(dataset_dir: Path = None) -> dict:
    """Scan all dataset splits and catalog every image.

    Args:
        dataset_dir: Root dataset directory. Defaults to Config.DATASET_DIR.

    Returns:
        Dict with structure:
        {
            "splits": {
                "train": [{"file": "501.jpeg", "path": "...", "labels": ["501"]}],
                "val": [...],
                "test": [...],
            },
            "label_map": {"501": ["path1", "path2"], ...},
            "all_labels": set of all unique labels found,
            "all_files": total file count,
        }
    """
    if dataset_dir is None:
        dataset_dir = Config.DATASET_DIR

    splits = {}
    label_map = defaultdict(list)  # node_id -> [image_paths]
    all_labels = set()
    total_files = 0

    for split_name in ["train", "val", "test"]:
        split_dir = dataset_dir / split_name
        if not split_dir.exists():
            print(f"  WARNING: Split directory not found: {split_dir}")
            continue

        split_entries = []
        for f in sorted(split_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in (".jpeg", ".jpg", ".png", ".bmp"):
                labels = extract_label_from_filename(f.name)
                entry = {
                    "file": f.name,
                    "path": str(f),
                    "labels": labels,
                    "split": split_name,
                }
                split_entries.append(entry)
                total_files += 1

                for label in labels:
                    label_map[label].append(str(f))
                    all_labels.add(label)

        splits[split_name] = split_entries

    return {
        "splits": splits,
        "label_map": dict(label_map),
        "all_labels": all_labels,
        "all_files": total_files,
    }


def validate_against_graph(scan_result: dict, graph=None) -> dict:
    """Validate all dataset labels against the building knowledge graph.

    Args:
        scan_result: Output from scan_dataset().
        graph: networkx DiGraph. Loaded from JSON if not provided.

    Returns:
        Validation report dict with:
        - matched: labels that exist in the graph
        - missing_from_graph: labels in dataset but not in graph
        - missing_from_dataset: graph rooms with no images
        - stats: summary statistics
    """
    if graph is None:
        graph = load_graph()

    dataset_labels = scan_result["all_labels"]
    all_node_ids = get_all_node_ids(graph)
    navigable_ids = get_all_room_ids(graph)  # rooms + landmarks only

    # Labels in dataset that match graph nodes
    matched = dataset_labels & all_node_ids

    # Labels in dataset that DON'T match any graph node
    missing_from_graph = dataset_labels - all_node_ids

    # Navigable graph nodes that have NO images in the dataset
    missing_from_dataset = navigable_ids - dataset_labels

    # Per-split stats
    split_stats = {}
    for split_name, entries in scan_result["splits"].items():
        split_labels = set()
        for e in entries:
            split_labels.update(e["labels"])
        split_stats[split_name] = {
            "files": len(entries),
            "unique_labels": len(split_labels),
        }

    # Images per label distribution
    images_per_label = {
        label: len(paths) for label, paths in scan_result["label_map"].items()
    }

    return {
        "matched": sorted(matched),
        "missing_from_graph": sorted(missing_from_graph),
        "missing_from_dataset": sorted(missing_from_dataset),
        "images_per_label": images_per_label,
        "split_stats": split_stats,
        "stats": {
            "total_files": scan_result["all_files"],
            "unique_labels": len(dataset_labels),
            "matched_labels": len(matched),
            "missing_from_graph": len(missing_from_graph),
            "missing_from_dataset": len(missing_from_dataset),
        },
    }


def generate_label_map(scan_result: dict, output_path: Path = None):
    """Generate and save label_map.json.

    The label map is: { node_id: [list of image paths] }
    Only includes labels that exist in the building graph.

    Args:
        scan_result: Output from scan_dataset().
        output_path: Where to save. Defaults to project root/label_map.json.
    """
    if output_path is None:
        output_path = Config.PROJECT_ROOT / "label_map.json"

    graph = load_graph()
    all_node_ids = get_all_node_ids(graph)

    # Filter to only graph-valid labels
    valid_map = {}
    skipped = []
    for label, paths in scan_result["label_map"].items():
        if label in all_node_ids:
            valid_map[label] = sorted(paths)
        else:
            skipped.append(label)

    # Sort by label for readability
    sorted_map = dict(sorted(valid_map.items()))

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sorted_map, f, indent=2, ensure_ascii=False)

    print(f"  Label map saved to {output_path}")
    print(f"  {len(sorted_map)} labels with {sum(len(v) for v in sorted_map.values())} images")
    if skipped:
        print(f"  Skipped {len(skipped)} labels not in graph: {skipped}")


def print_report(validation: dict):
    """Print a formatted validation report."""
    stats = validation["stats"]
    split_stats = validation["split_stats"]

    print("=" * 60)
    print("  WayLens Dataset : Validation Report")
    print("=" * 60)

    # Overview
    print(f"\n  Total image files: {stats['total_files']}")
    print(f"  Unique labels:     {stats['unique_labels']}")
    print(f"  Matched to graph:  {stats['matched_labels']}")

    # Per-split breakdown
    print("\n  Per-split breakdown:")
    for split, s in split_stats.items():
        print(f"    {split:6s}: {s['files']:3d} files, "
              f"{s['unique_labels']:3d} unique labels")

    # Missing from graph (dataset has it, graph doesn't)
    if validation["missing_from_graph"]:
        print(f"\n  WARNING: {stats['missing_from_graph']} label(s) in dataset "
              f"but NOT in building graph:")
        for label in validation["missing_from_graph"]:
            print(f"    - {label}")
        print("  Action: Add these nodes to building_graph.py or update "
              "FILENAME_TO_NODE mapping")
    else:
        print(f"\n  OK: All dataset labels match graph nodes")

    # Missing from dataset (graph has it, no images)
    if validation["missing_from_dataset"]:
        print(f"\n  INFO: {stats['missing_from_dataset']} graph node(s) have "
              f"NO images in the dataset:")
        for label in validation["missing_from_dataset"]:
            info = get_node_info(load_graph(), label)
            floor = info.get("floor", "?") if info else "?"
            ntype = info.get("type", "?") if info else "?"
            print(f"    - {label:30s}  (Floor {floor}, {ntype})")
        print("  Note: Landmarks without images will rely on OCR text detection")
    else:
        print(f"\n  OK: Every graph node has at least one image")

    # Images per label
    ipl = validation["images_per_label"]
    if ipl:
        counts = list(ipl.values())
        print(f"\n  Images per label: min={min(counts)}, max={max(counts)}, "
              f"avg={sum(counts)/len(counts):.1f}")

        # Labels with most images
        top = sorted(ipl.items(), key=lambda x: -x[1])[:5]
        print("  Top 5 labels by image count:")
        for label, count in top:
            print(f"    {label:30s}: {count} images")

    print("\n" + "=" * 60)


# ─── CLI ────────────────────────────────────────────────────────────

def main():
    """CLI entry point for dataset utilities."""
    import argparse

    parser = argparse.ArgumentParser(
        description="WayLens Dataset Utilities"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Scan dataset and validate against building graph"
    )
    parser.add_argument(
        "--generate-map", action="store_true",
        help="Generate label_map.json"
    )
    parser.add_argument(
        "--dataset-dir", type=str, default=None,
        help="Override dataset directory path"
    )

    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir) if args.dataset_dir else None

    if args.check or args.generate_map or len(sys.argv) == 1:
        print("Scanning dataset...")
        scan = scan_dataset(dataset_dir)

        print("Validating against building graph...")
        validation = validate_against_graph(scan)
        print_report(validation)

        if args.generate_map or len(sys.argv) == 1:
            print("\nGenerating label map...")
            generate_label_map(scan)


if __name__ == "__main__":
    main()
