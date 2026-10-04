import io
import zipfile

import pytest

from app.core import SubmissionError
from app.submissions.python_bundle import locate_bundle_dir
from app.submissions.zip_safety import safe_extract_zip


def _zip(entries: dict[str, bytes], path):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return path


def test_extracts_normal_archive(tmp_path):
    z = _zip(
        {"submission.py": b"def predict(X): return X[:,0]", "sub/weights.bin": b"\x00" * 10},
        tmp_path / "a.zip",
    )
    written = safe_extract_zip(z, tmp_path / "out")
    assert sorted(written) == ["sub/weights.bin", "submission.py"]
    assert (tmp_path / "out/submission.py").read_bytes().startswith(b"def predict")


def test_path_traversal_rejected(tmp_path):
    z = _zip({"../evil.py": b"x", "submission.py": b"y"}, tmp_path / "a.zip")
    with pytest.raises(SubmissionError, match="traversal"):
        safe_extract_zip(z, tmp_path / "out")
    assert not (tmp_path / "evil.py").exists()


def test_absolute_path_rejected(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("/etc/passwd", b"x")
    (tmp_path / "a.zip").write_bytes(buf.getvalue())
    with pytest.raises(SubmissionError, match="absolute"):
        safe_extract_zip(tmp_path / "a.zip", tmp_path / "out")


def test_symlink_rejected(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        info = zipfile.ZipInfo("link")
        info.external_attr = 0o120777 << 16
        zf.writestr(info, "/etc/passwd")
        zf.writestr("submission.py", "x")
    (tmp_path / "a.zip").write_bytes(buf.getvalue())
    with pytest.raises(SubmissionError, match="symbolic link"):
        safe_extract_zip(tmp_path / "a.zip", tmp_path / "out")


def test_too_many_files(tmp_path):
    z = _zip({f"f{i}.txt": b"x" for i in range(20)}, tmp_path / "a.zip")
    with pytest.raises(SubmissionError, match="too many"):
        safe_extract_zip(z, tmp_path / "out", max_files=10)


def test_zip_bomb_declared_size(tmp_path):
    z = _zip({"big.bin": b"\x00" * (2 * 1024 * 1024)}, tmp_path / "a.zip")
    with pytest.raises(SubmissionError, match="too large"):
        safe_extract_zip(z, tmp_path / "out", max_total_uncompressed=1024 * 1024)


def test_zip_bomb_lying_header(tmp_path):
    """Header claims a tiny size but the stream is large: the streaming cap must catch it."""
    z = _zip({"big.bin": b"\x00" * (3 * 1024 * 1024)}, tmp_path / "a.zip")
    data = bytearray(z.read_bytes())
    # Corrupt the central-directory uncompressed size field to a small value.
    with zipfile.ZipFile(z) as zf:
        info = zf.infolist()[0]
        assert info.file_size == 3 * 1024 * 1024
    import struct

    cd_offset = data.rfind(b"PK\x01\x02")
    # central directory header: uncompressed size at offset 24
    data[cd_offset + 24 : cd_offset + 28] = struct.pack("<I", 10)
    lh = data.find(b"PK\x03\x04")
    data[lh + 22 : lh + 26] = struct.pack("<I", 10)
    z.write_bytes(bytes(data))
    with pytest.raises(SubmissionError):
        safe_extract_zip(z, tmp_path / "out", max_total_uncompressed=1024 * 1024)


def test_locate_bundle_in_single_folder(tmp_path):
    z = _zip({"mybundle/submission.py": b"x", "mybundle/w.pt": b"y"}, tmp_path / "a.zip")
    safe_extract_zip(z, tmp_path / "out")
    assert locate_bundle_dir(tmp_path / "out") == tmp_path / "out" / "mybundle"


def test_missing_entrypoint(tmp_path):
    z = _zip({"model.py": b"x"}, tmp_path / "a.zip")
    safe_extract_zip(z, tmp_path / "out")
    with pytest.raises(SubmissionError, match="submission.py"):
        locate_bundle_dir(tmp_path / "out")
