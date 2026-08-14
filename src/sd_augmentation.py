import base64
import io
import json
import random
import sys
import time
from pathlib import Path
from typing import Optional, List

import requests
from PIL import Image

from config import Config


def image_to_base64(image_path: Path) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def base64_to_image(b64_string: str) -> Image.Image:
    img_data = base64.b64decode(b64_string)
    return Image.open(io.BytesIO(img_data))


def check_sd_server(api_url: str = None) -> bool:
    urls_to_try = [api_url or Config.SD_API_URL, "http://127.0.0.1:7861", "http://127.0.0.1:7860"]
    for url in urls_to_try:
        try:
            resp = requests.get(f"{url}/sdapi/v1/sd-models", timeout=3)
            if resp.status_code == 200:
                Config.SD_API_URL = url
                return True
        except requests.RequestException:
            continue
    return False


def generate_variations(
    image_path: Path,
    num_variations: int = None,
    api_url: str = None,
) -> List[Image.Image]:
    if num_variations is None:
        num_variations = Config.SD_VARIATIONS_PER_IMAGE
    if api_url is None:
        api_url = Config.SD_API_URL

    img_b64 = image_to_base64(image_path)

    prompts = [
        "indoor corridor classroom door sign, slightly different lighting",
        "indoor hallway room entrance signage, different exposure",
        "classroom corridor doorway with room number sign, overcast lighting",
        "indoor building corridor room sign, slightly warm lighting",
        "hallway door with room number plate, slightly dim lighting",
    ]

    variations = []
    for i in range(num_variations):
        denoising = random.uniform(
            Config.SD_DENOISING_STRENGTH_MIN,
            Config.SD_DENOISING_STRENGTH_MAX,
        )
        prompt = prompts[i % len(prompts)]

        payload = {
            "init_images": [img_b64],
            "prompt": prompt,
            "negative_prompt": "blurry, distorted text, unreadable, cartoon, painting",
            "denoising_strength": denoising,
            "steps": Config.SD_STEPS,
            "width": Config.SD_WIDTH,
            "height": Config.SD_HEIGHT,
            "seed": -1,
            "sampler_name": "Euler a",
            "cfg_scale": 7,
            "batch_size": 1,
        }

        try:
            resp = requests.post(
                f"{api_url}/sdapi/v1/img2img",
                json=payload,
                timeout=600,
            )
            resp.raise_for_status()
            result = resp.json()

            for img_b64_out in result.get("images", []):
                img = base64_to_image(img_b64_out)
                variations.append(img)

        except requests.exceptions.RequestException:
            continue

    return variations


def generate_landmark_visual(prompt: str, api_url: str = None) -> Optional[Image.Image]:
    if api_url is None:
        api_url = Config.SD_API_URL

    payload = {
        "prompt": f"photograph of university building corridor, {prompt}, interior architecture, clean lighting",
        "negative_prompt": "blurry, distorted, dark, cartoon, 3d render, painting",
        "steps": 15,
        "width": 512,
        "height": 512,
        "sampler_name": "Euler a",
        "cfg_scale": 7,
        "batch_size": 1,
    }
    try:
        resp = requests.post(f"{api_url}/sdapi/v1/txt2img", json=payload, timeout=60)
        if resp.status_code == 200:
            images = resp.json().get("images", [])
            if images:
                return base64_to_image(images[0])
    except Exception:
        pass
    return None


def augment_dataset(
    source_dir: Path = None,
    output_dir: Path = None,
    num_variations: int = None,
    resume: bool = True,
):
    if source_dir is None:
        source_dir = Config.TRAIN_DIR
    if output_dir is None:
        output_dir = Config.AUGMENTED_DIR
    if num_variations is None:
        num_variations = Config.SD_VARIATIONS_PER_IMAGE

    if not check_sd_server():
        print("ERROR: AUTOMATIC1111 server is not running!")
        print(f"  Expected at: {Config.SD_API_URL}")
        sys.exit(1)

    image_extensions = {".jpeg", ".jpg", ".png", ".bmp"}
    source_images = sorted([
        f for f in source_dir.iterdir()
        if f.is_file() and f.suffix.lower() in image_extensions
    ])

    output_dir.mkdir(parents=True, exist_ok=True)
    stats = {"processed": 0, "skipped": 0, "generated": 0, "failed": 0}
    total = len(source_images)

    for idx, img_path in enumerate(source_images, 1):
        label = img_path.stem
        label_dir = output_dir / label
        label_dir.mkdir(parents=True, exist_ok=True)

        existing = list(label_dir.glob("*.png"))
        if resume and len(existing) >= num_variations:
            stats["skipped"] += 1
            continue

        start_time = time.time()
        variations = generate_variations(img_path, num_variations)

        if variations:
            for i, var_img in enumerate(variations):
                out_path = label_dir / f"{label}_aug_{i+1}.png"
                var_img.save(out_path)
            stats["generated"] += len(variations)
            stats["processed"] += 1
        else:
            stats["failed"] += 1

    stats_path = output_dir / "augmentation_stats.json"
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="WayLens SD Augmentation")
    parser.add_argument("--check", action="store_true", help="Check if AUTOMATIC1111 server is running")
    parser.add_argument("--source", type=str, default=None, help="Source image directory")
    parser.add_argument("--output", type=str, default=None, help="Output directory")
    parser.add_argument("--variations", type=int, default=None, help="Variations per image")
    parser.add_argument("--no-resume", action="store_true", help="Do not skip already augmented images")

    args = parser.parse_args()

    if args.check:
        if check_sd_server():
            print("AUTOMATIC1111 server is running and reachable.")
        else:
            print("AUTOMATIC1111 server is NOT reachable.")
            print(f"  Expected at: {Config.SD_API_URL}")
        return

    source = Path(args.source) if args.source else None
    output = Path(args.output) if args.output else None

    augment_dataset(
        source_dir=source,
        output_dir=output,
        num_variations=args.variations,
        resume=not args.no_resume,
    )


if __name__ == "__main__":
    main()
