from pathlib import Path
import argparse

from config import Config
from embedding_index import CLIPEmbeddingIndex


def build_and_save_index():
    index_mgr = CLIPEmbeddingIndex()
    sources = [Config.TRAIN_DIR, Config.VAL_DIR, Config.TEST_DIR]
    if Config.AUGMENTED_DIR.exists():
        sources.append(Config.AUGMENTED_DIR)
    index_mgr.build_index(sources, output_path=Config.CLIP_INDEX_PATH)


def main():
    parser = argparse.ArgumentParser(description="WayLens Build and Evaluate CLIP Embeddings")
    parser.add_argument(
        "--source",
        type=str,
        default="all_splits",
        choices=["train", "all_splits", "augmented", "all"],
        help="Source images to index",
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Evaluate top-1 and top-3 accuracy on test dataset",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Force rebuild of embedding index",
    )

    args = parser.parse_args()
    index_mgr = CLIPEmbeddingIndex()

    sources = []
    if args.source == "train":
        sources.append(Config.TRAIN_DIR)
    elif args.source == "all_splits":
        sources = [Config.TRAIN_DIR, Config.VAL_DIR, Config.TEST_DIR]
    elif args.source == "augmented":
        if Config.AUGMENTED_DIR.exists():
            sources.append(Config.AUGMENTED_DIR)
    elif args.source == "all":
        sources = [Config.TRAIN_DIR, Config.VAL_DIR, Config.TEST_DIR]
        if Config.AUGMENTED_DIR.exists():
            sources.append(Config.AUGMENTED_DIR)

    index_path = Config.CLIP_INDEX_PATH

    if args.rebuild or not index_path.exists():
        print(f"Building CLIP embedding index from source='{args.source}'...")
        index_mgr.build_index(sources, output_path=index_path)
    else:
        print(f"Loading existing CLIP embedding index from {index_path}...")
        index_mgr.load_index(index_path)

    if args.evaluate:
        print("\nRunning Evaluation on Test Set...")
        index_mgr.evaluate(Config.TEST_DIR)


if __name__ == "__main__":
    main()
