from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Sequence


EXPECTED_PART_SIZES = (
    1_000_000_000,
    1_000_000_000,
    1_000_000_000,
    1_000_000_000,
    931_277_734,
)
EXPECTED_FILE_SIZE = 4_931_277_734
EXPECTED_SHA256 = "d3a38eae866061bcd69796713722dcc40668b314b7608b6eb49f4197b4415dae"
BUFFER_SIZE = 8 * 1024 * 1024


def restore_parts(
    part_paths: Sequence[Path],
    destination: Path,
    expected_part_sizes: Sequence[int],
    expected_size: int,
    expected_sha256: str,
) -> None:
    if len(part_paths) != len(expected_part_sizes) or not part_paths:
        raise ValueError("The part list does not match the expected number of parts.")
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination.with_name(f".{destination.name}.restore-tmp")
    if temporary_path.exists():
        raise FileExistsError(f"Remove the incomplete restore file first: {temporary_path}")

    digest = hashlib.sha256()
    total_size = 0
    try:
        with temporary_path.open("xb") as output:
            for part_path, expected_part_size in zip(
                part_paths, expected_part_sizes, strict=True
            ):
                part_size = 0
                with part_path.open("rb") as part:
                    while block := part.read(BUFFER_SIZE):
                        output.write(block)
                        digest.update(block)
                        part_size += len(block)
                        total_size += len(block)

                if part_size != expected_part_size:
                    raise ValueError(
                        f"{part_path} has {part_size} bytes; "
                        f"expected {expected_part_size}."
                    )

        if total_size != expected_size:
            raise ValueError(
                f"Restored file has {total_size} bytes; expected {expected_size}."
            )

        actual_sha256 = digest.hexdigest()
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"SHA-256 mismatch: got {actual_sha256}, expected {expected_sha256}."
            )

        temporary_path.replace(destination)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    parts_dir = (
        project_root
        / "backend"
        / "uploads"
        / "film_parts"
        / "film_1_243e511cfeeb4f89a993870d642366ba"
    )
    destination = (
        project_root
        / "backend"
        / "uploads"
        / "films"
        / "film_1_243e511cfeeb4f89a993870d642366ba.mp4"
    )
    part_paths = tuple(
        parts_dir / f"part-{index:03}.mp4"
        for index in range(1, len(EXPECTED_PART_SIZES) + 1)
    )

    try:
        restore_parts(
            part_paths,
            destination,
            EXPECTED_PART_SIZES,
            EXPECTED_FILE_SIZE,
            EXPECTED_SHA256,
        )
    except (OSError, ValueError) as error:
        print(f"Could not restore movie file: {error}", file=sys.stderr)
        return 1

    print(f"Restored movie file: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
