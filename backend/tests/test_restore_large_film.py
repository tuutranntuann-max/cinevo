import hashlib

import pytest

from scripts.restore_large_film import restore_parts


def test_restore_parts_reassembles_and_verifies_checksum(tmp_path):
    content = b"movie data split across parts"
    first_part = tmp_path / "part-001.mp4"
    second_part = tmp_path / "part-002.mp4"
    first_part.write_bytes(content[:10])
    second_part.write_bytes(content[10:])
    destination = tmp_path / "restored.mp4"

    restore_parts(
        [first_part, second_part],
        destination,
        [10, len(content) - 10],
        len(content),
        hashlib.sha256(content).hexdigest(),
    )

    assert destination.read_bytes() == content


def test_restore_parts_rejects_checksum_mismatch_and_removes_partial_file(tmp_path):
    part = tmp_path / "part-001.mp4"
    part.write_bytes(b"not the expected content")
    destination = tmp_path / "restored.mp4"

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        content = part.read_bytes()
        restore_parts(
            [part],
            destination,
            [len(content)],
            len(content),
            "0" * 64,
        )

    assert not destination.exists()
    assert not destination.with_name(".restored.mp4.restore-tmp").exists()


def test_restore_parts_does_not_overwrite_existing_file(tmp_path):
    part = tmp_path / "part-001.mp4"
    part.write_bytes(b"content")
    destination = tmp_path / "restored.mp4"
    destination.write_bytes(b"existing")

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        restore_parts([part], destination, [len(part.read_bytes())], 7, "0" * 64)

    assert destination.read_bytes() == b"existing"
