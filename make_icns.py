#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ICON_SIZES = [16, 32, 64, 128, 256, 512, 1024]


def build_icns(source: Path, output: Path) -> None:
    if shutil.which("iconutil") is None:
        raise RuntimeError("未找到 iconutil，无法生成 macOS icns 图标。")

    with Image.open(source) as image, tempfile.TemporaryDirectory() as temp_dir:
        iconset_dir = Path(temp_dir) / "Android.iconset"
        iconset_dir.mkdir(parents=True, exist_ok=True)

        for size in ICON_SIZES:
            resized = image.convert("RGBA").resize((size, size))
            resized.save(iconset_dir / f"icon_{size}x{size}.png")
            if size < 1024:
                retina_size = size * 2
                image.convert("RGBA").resize((retina_size, retina_size)).save(iconset_dir / f"icon_{size}x{size}@2x.png")

        result = subprocess.run(["iconutil", "-c", "icns", str(iconset_dir), "-o", str(output)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "iconutil 执行失败")


def main() -> None:
    parser = argparse.ArgumentParser(description="将 ICO 转换为 macOS 打包可用的 ICNS。")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    if not args.input.is_file():
        raise FileNotFoundError(f"图标文件不存在：{args.input}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    build_icns(args.input, args.output)
    print(args.output)


if __name__ == "__main__":
    main()
