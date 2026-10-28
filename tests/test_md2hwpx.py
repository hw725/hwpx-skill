#!/usr/bin/env python3
"""md2hwpx.py 회귀 테스트 — py3.9 호환 + 본문 반영 PrvText.

잠그는 버그 2종:
  (1) py3.9에서 `list[...] | None` 어노테이션으로 import 시 크래시 (from __future__ 누락)
  (2) PrvText 미생성 → fill_hwpx check --strict가 raw('빈 페이지')로 차단

build_hwpx.py(→lxml)를 호출하므로 lxml이 필요하다(test_gonmun과 동일 전제).
사용법: python3 tests/test_md2hwpx.py
"""
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# ── CJK Text Contract E3 (CJK-TEXT-CONTRACT.md) ───────────────────
# 한국어 Windows 콘솔의 기본은 cp949 다. 한글·한자는 대개 있지만 《—》·《✓》·확장
# 한자·옛한글은 **없어서**, 그런 글자를 print 하면 UnicodeEncodeError 로 즉사한다.
# 이 PC 는 사용자 환경변수 PYTHONUTF8=1 이 박혀 있어 겪지 않는다 — 받는 사람 PC
# 에는 없다. 스킬끼리는 import 하지 않으므로(각자 junction 으로 배포) 네 줄을 품는다.
# (로컬 분기 — 상류 jkf87/hwpx-skill 에는 없다. vendor/hwpx/.upstream.json 참조)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass  # 파이프·리다이렉트 등 재설정 불가 환경

ROOT = Path(__file__).resolve().parent.parent
MD2 = ROOT / "scripts" / "md2hwpx.py"
FILL = ROOT / "scripts" / "fill_hwpx.py"

PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name} {detail}")


MD = """# 코드 에이전트 조합 표

소개 문단.

| 하니스 | 모델 | 결과 |
| --- | --- | --- |
| Qwen-Code | Qwen3.6 | 4/5 |
| Claude Code | North Mini Code | 5/5 |
"""


def main():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        md = d / "in.md"
        md.write_text(MD, encoding="utf-8")
        out = d / "out.hwpx"

        # (1) 현재 파이썬에서 크래시 없이 실행 (py3.9 호환)
        r = subprocess.run(
            [sys.executable, str(MD2), str(md), "-o", str(out),
             "--title", "조합 표"],
            capture_output=True, text=True, encoding="utf-8")
        check("md2hwpx 실행 (크래시 없음, exit 0)", r.returncode == 0,
              f"\n    {r.stderr.strip()[:300]}")
        if r.returncode != 0 or not out.is_file():
            print(f"\n{PASS} passed, {FAIL} failed")
            return 1 if FAIL else 0

        # (2) PrvText가 본문을 반영 → check --strict 통과 (raw 아님)
        prv = zipfile.ZipFile(out).read("Preview/PrvText.txt").decode(
            "utf-8", "replace")
        check("PrvText가 본문 반영 (placeholder 아님)",
              len(prv) > 50 and "Qwen-Code" in prv, f"(len={len(prv)})")

        c = subprocess.run(
            [sys.executable, str(FILL), "check", str(out), "--strict"],
            capture_output=True, text=True, encoding="utf-8")
        check("check --strict 통과 (raw 빈 페이지 아님)", c.returncode == 0,
              f"\n    {c.stdout.strip()[:300]}")

        # 표/내용 반영 확인
        sec = zipfile.ZipFile(out).read("Contents/section0.xml").decode()
        check("표(hp:tbl) 생성", sec.count("<hp:tbl") >= 1)
        check("표 셀 내용 반영", "North Mini Code" in sec and "5/5" in sec)

    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
