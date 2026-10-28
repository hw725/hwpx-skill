"""Retirement gate for shipped assets, routing and installed-copy drift.

Run with --root PATH to check an installed skill too. This does not restrict
user-provided documents or legitimate mentions of organizations in their text.
"""
import argparse
import hashlib
from pathlib import Path
from zipfile import ZipFile

# ── CJK Text Contract E3 (CJK-TEXT-CONTRACT.md) ───────────────────
# 한국어 Windows 콘솔의 기본은 cp949 다. 한글·한자는 대개 있지만 《—》·《✓》·확장
# 한자·옛한글은 **없어서**, 그런 글자를 print 하면 UnicodeEncodeError 로 즉사한다.
# 이 PC 는 사용자 환경변수 PYTHONUTF8=1 이 박혀 있어 겪지 않는다 — 받는 사람 PC
# 에는 없다. 스킬끼리는 import 하지 않으므로(각자 junction 으로 배포) 네 줄을 품는다.
# (로컬 분기 — 상류 jkf87/hwpx-skill 에는 없다. vendor/hwpx/.upstream.json 참조)
import sys  # noqa: E402
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass  # 파이프·리다이렉트 등 재설정 불가 환경

RETIRED_PATHS = (
    "assets/report-template.hwpx", "assets/government-reference.hwpx",
    "templates/government", "scripts/sanitize_report_template.py",
)
RETIRED_HASHES = {
    "a89abf467278c189b0953060eb8ca2b31a8d1d1c3d1e43df6741da4ec50c8257",
    "d83ddd0020e0cdb7162a91660a20ea5c885ec21e3b83e01edc3e1ef93054ea51",
    "2bfdf345f11f7c375a327aab5183438f2a9ec987b06632f1c01f34400f55cc18",
}
MARKERS = ("브라더", "brother", "체육건강안전과", "학교체육활성화", "어디서나 운동장")


def check_root(root: Path) -> None:
    for relative in RETIRED_PATHS:
        assert not (root / relative).exists(), f"Retired asset restored: {relative}"
    for directory in (root / "assets", root / "templates"):
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            data = path.read_bytes()
            assert hashlib.sha256(data).hexdigest() not in RETIRED_HASHES, path
            if path.suffix == ".hwpx":
                with ZipFile(path) as archive:
                    for name in archive.namelist():
                        payload = archive.read(name)
                        assert hashlib.sha256(payload).hexdigest() not in RETIRED_HASHES, (path, name)
                        if name.endswith((".xml", ".txt", ".hpf", ".rdf")):
                            text = payload.decode("utf-8", "replace").lower()
                            assert not any(m in text for m in MARKERS), (path, name)
            elif path.suffix == ".xml":
                text = data.decode("utf-8", "replace").lower()
                assert not any(m in text for m in MARKERS), path
    # Historical release notes and regression tests are intentionally excluded.
    paths = [root / "SKILL.md", root / "README.md"]
    paths += list((root / "scripts").rglob("*.py"))
    paths += list((root / "references").rglob("*.md"))
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert not any(p in text for p in RETIRED_PATHS), path
        assert "report-template.hwpx" not in text, path
    print(f"PASS retired assets, renamed copies, residue and routes absent: {root}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    check_root(parser.parse_args().root)
