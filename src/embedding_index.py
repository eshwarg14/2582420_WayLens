import json
import time
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Union

import numpy as np
import open_clip
import torch
from PIL import Image

from config import Config
from dataset_utils import extract_label_from_filename


class CLIPEmbeddingIndex:
    """CLIP embedding index manager for room image retrieval."""

    def __init__(self, model_name: str = None, pretrained: str = None, device: str = "cpu"):
        self.model_name = model_name or Config.CLIP_MODEL_NAME
        self.pretrained = pretrained or Config.CLIP_PRETRAINED
        self.device = device

        self.model = None
        self.preprocess = None
        self.tokenizer = None

        self.embeddings: Optional[np.ndarray] = None
        self.labels: List[str] = []
        self.image_paths: List[str] = []

    def load_model(self):
        """Lazy load the CLIP model and preprocessing pipeline."""
        if self.model is None:
            print(f"Loading CLIP model '{self.model_name}' ({self.pretrained}) on {self.device}...")
            start = time.time()
            self.model, _, self.preprocess = open_clip.create_model_and_transforms(
                self.model_name,
                pretrained=self.pretrained,
                device=self.device,
            )
            self.model.eval()
            self.tokenizer = open_clip.get_tokenizer(self.model_name)
            print(f"CLIP model loaded in {time.time() - start:.2f}s.")

    def compute_image_embedding(self, image_input: Union[Path, str, Image.Image]) -> np.ndarray:
        """Compute normalized 512-dim embedding vector for a single PIL image or file path."""
        self.load_model()

        if isinstance(image_input, (str, Path)):
            img = Image.open(image_input).convert("RGB")
        else:
            img = image_input.convert("RGB")

        image_tensor = self.preprocess(img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            feat = self.model.encode_image(image_tensor)
            feat /= feat.norm(dim=-1, keepdim=True)

        return feat.cpu().numpy().squeeze(0)

    def build_index(
        self,
        image_sources: List[Path],
        output_path: Path = None,
        batch_size: int = 16,
    ):
        """Build embedding index from a list of image paths or directories."""
        self.load_model()
        output_path = output_path or Config.CLIP_INDEX_PATH

        all_file_entries: List[Tuple[Path, str]] = []  # (path, label)

        for src in image_sources:
            if not src.exists():
                print(f"  WARNING: Source path does not exist: {src}")
                continue

            if src.is_file():
                labels = extract_label_from_filename(src.name)
                for l in labels:
                    all_file_entries.append((src, l))
            elif src.is_dir():
                # Check if nested by room label (e.g. augmented/501/*.png) or flat image folder
                for path in sorted(src.rglob("*")):
                    if path.is_file() and path.suffix.lower() in (".jpeg", ".jpg", ".png", ".bmp"):
                        # If parent folder is named like a room, use parent name; else extract from filename
                        if path.parent.name in ("train", "val", "test", "augmented", src.name):
                            labels = extract_label_from_filename(path.name)
                        else:
                            labels = [path.parent.name]
                        for l in labels:
                            all_file_entries.append((path, l))

        if not all_file_entries:
            raise ValueError("No images found to build index.")

        print(f"Building CLIP embedding index for {len(all_file_entries)} image-label pairs...")
        start_time = time.time()

        embeddings_list = []
        labels_list = []
        paths_list = []

        # Process in batches
        for i in range(0, len(all_file_entries), batch_size):
            batch = all_file_entries[i : i + batch_size]
            tensors = []
            valid_batch_items = []

            for path, label in batch:
                try:
                    img = Image.open(path).convert("RGB")
                    tensor = self.preprocess(img)
                    tensors.append(tensor)
                    valid_batch_items.append((path, label))
                except Exception as e:
                    print(f"  WARNING: Failed to process image {path}: {e}")

            if not tensors:
                continue

            batch_tensor = torch.stack(tensors).to(self.device)
            with torch.no_grad():
                feats = self.model.encode_image(batch_tensor)
                feats /= feats.norm(dim=-1, keepdim=True)

            feats_np = feats.cpu().numpy()
            for idx, (path, label) in enumerate(valid_batch_items):
                embeddings_list.append(feats_np[idx])
                labels_list.append(label)
                paths_list.append(str(path))

        self.embeddings = np.array(embeddings_list, dtype=np.float32)
        self.labels = labels_list
        self.image_paths = paths_list

        output_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            output_path,
            embeddings=self.embeddings,
            labels=np.array(self.labels),
            image_paths=np.array(self.image_paths),
        )

        elapsed = time.time() - start_time
        print(f"✓ Index built successfully in {elapsed:.2f}s!")
        print(f"  Saved to: {output_path}")
        print(f"  Matrix shape: {self.embeddings.shape}")
        print(f"  Unique room labels: {len(set(self.labels))}")

    def load_index(self, index_path: Path = None) -> bool:
        """Load precomputed embedding index from .npz file."""
        index_path = index_path or Config.CLIP_INDEX_PATH
        if not index_path.exists():
            print(f"  WARNING: Index file not found at {index_path}")
            return False

        data = np.load(index_path)
        self.embeddings = data["embeddings"]
        self.labels = list(data["labels"])
        self.image_paths = list(data["image_paths"])
        return True

    def query(
        self,
        image_input: Union[Path, str, Image.Image],
        top_k: int = 3,
    ) -> List[Tuple[str, float]]:
        """Query nearest match for an input image.

        Returns:
            List of (room_label, similarity_score) sorted descending by similarity.
        """
        if self.embeddings is None:
            if not self.load_index():
                raise RuntimeError("Embedding index is not built or loaded.")

        query_emb = self.compute_image_embedding(image_input)

        # Cosine similarity (since embeddings are L2 normalized)
        similarities = np.dot(self.embeddings, query_emb)

        # Aggregate max score per unique label
        label_scores: Dict[str, float] = {}
        for idx, score in enumerate(similarities):
            lbl = self.labels[idx]
            if lbl not in label_scores or score > label_scores[lbl]:
                label_scores[lbl] = float(score)

        sorted_results = sorted(label_scores.items(), key=lambda x: -x[1])
        return sorted_results[:top_k]

    def evaluate(self, test_dir: Path, top_k: int = 3) -> dict:
        """Evaluate localization top-1 and top-3 accuracy on test dataset."""
        if self.embeddings is None:
            if not self.load_index():
                raise RuntimeError("Index not loaded for evaluation.")

        test_files = [
            f for f in sorted(test_dir.iterdir())
            if f.is_file() and f.suffix.lower() in (".jpeg", ".jpg", ".png", ".bmp")
        ]

        if not test_files:
            print(f"No test images found in {test_dir}")
            return {}

        top1_correct = 0
        topk_correct = 0
        details = []

        print(f"\nEvaluating CLIP index retrieval on {len(test_files)} images from {test_dir.name}...")

        for img_path in test_files:
            true_labels = extract_label_from_filename(img_path.name)
            results = self.query(img_path, top_k=top_k)

            predicted_labels = [r[0] for r in results]
            top1_match = any(p in true_labels for p in predicted_labels[:1])
            topk_match = any(p in true_labels for p in predicted_labels)

            if top1_match:
                top1_correct += 1
            if topk_match:
                topk_correct += 1

            details.append({
                "file": img_path.name,
                "true_labels": true_labels,
                "predictions": results,
                "top1_correct": top1_match,
                "topk_correct": topk_match,
            })

        total = len(test_files)
        top1_acc = (top1_correct / total) * 100.0
        topk_acc = (topk_correct / total) * 100.0

        print(f"  Top-1 Accuracy: {top1_correct}/{total} ({top1_acc:.1f}%)")
        print(f"  Top-{top_k} Accuracy: {topk_correct}/{total} ({topk_acc:.1f}%)")

        return {
            "total": total,
            "top1_accuracy": top1_acc,
            "topk_accuracy": topk_acc,
            "details": details,
        }


# ─── CLI ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="WayLens CLIP Embedding Index Utility")
    parser.add_argument("--build", action="store_true", help="Build CLIP embedding index")
    parser.add_argument("--eval", action="store_true", help="Evaluate index accuracy")
    parser.add_argument("--query-img", type=str, help="Path to image file to query")
    parser.add_argument("--source", type=str, default="train", choices=["train", "all"], help="Source images: train or train+augmented")

    args = parser.parse_args()
    index_mgr = CLIPEmbeddingIndex()

    if args.build:
        sources = [Config.TRAIN_DIR]
        if args.source == "all" and Config.AUGMENTED_DIR.exists():
            sources.append(Config.AUGMENTED_DIR)
        index_mgr.build_index(sources)

    if args.eval:
        index_mgr.evaluate(Config.TEST_DIR)

    if args.query_img:
        res = index_mgr.query(args.query_img)
        print(f"Query results for {args.query_img}:")
        for rank, (lbl, score) in enumerate(res, 1):
            print(f"  {rank}. {lbl}: {score:.4f}")
