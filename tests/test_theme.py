#!/usr/bin/env python3
"""set-theme (P6) 회귀 테스트 — in-place 제목색·표머리색 + md2hwpx --theme.

사용법: python3 tests/test_theme.py
"""
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from neutral_report_fixture import build_report

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
FILL = ROOT / "scripts" / "fill_hwpx.py"
MD2 = ROOT / "scripts" / "md2hwpx.py"

PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name} {detail}")


def run(*args, expect=0):
    r = subprocess.run([sys.executable, str(FILL), *map(str, args)],
                       capture_output=True, text=True, encoding="utf-8")
    out = json.loads(r.stdout) if r.stdout.strip() else None
    return r.returncode, out


def hx(p, name):
    return zipfile.ZipFile(p).read(name).decode()


def crcs(p):
    return {i.filename: i.CRC for i in zipfile.ZipFile(p).infolist()}


def main():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        report = build_report(d / "report.hwpx")

        # ── in-place: 남색 테마 ──
        navy = d / "navy.hwpx"
        code, rep = run("set-theme", report, navy, "--theme", "남색")
        check("set-theme 남색 성공", code == 0 and rep and rep["ok"])
        check("제목 charPr recolor(>0) + 표머리 색칠(>0)",
              rep and rep["headings_recolored"] > 0
              and rep["header_cells_colored"] > 0)
        h = hx(navy, "Contents/header.xml")
        check("헤더에 남색 #1F3864", "#1F3864" in h)
        check("표머리 배경 #D6DCE5", "#D6DCE5" in h)
        b, n = crcs(report), crcs(navy)
        changed = sorted(k for k in b if b[k] != n.get(k))
        check("header+section만 변경",
              changed == ["Contents/header.xml", "Contents/section0.xml"]
              and not [k for k in n if k not in b])
        code, _ = run("check", navy, "--strict")
        check("남색 테마 check --strict 통과", code == 0)

        # ── override 색 ──
        ov = d / "ov.hwpx"
        code, rep = run("set-theme", report, ov, "--heading-color", "FF0000",
                        "--table-header-color", "FFFF00")
        check("override 색 적용",
              code == 0 and "#FF0000" in hx(ov, "Contents/header.xml")
              and "#FFFF00" in hx(ov, "Contents/header.xml"))

        # ── 잘못된 테마 거부 ──
        code, _ = run("set-theme", report, d / "x.hwpx", "--theme", "없는테마",
                      expect=1)
        check("잘못된 테마 거부(exit 1)", code == 1)

        # ── md2hwpx --theme (새 문서 생성 + 테마) ──
        md = d / "in.md"
        md.write_text("# 월별 실적\n\n| 월 | 값 |\n| --- | --- |\n| 1월 | 10 |\n",
                      encoding="utf-8")
        out = d / "themed.hwpx"
        r = subprocess.run([sys.executable, str(MD2), str(md), "-o", str(out),
                            "--theme", "남색"], capture_output=True, text=True, encoding="utf-8")
        if out.is_file():
            check("md2hwpx --theme 생성", r.returncode == 0)
            code, _ = run("check", out, "--strict")
            check("md2hwpx --theme check --strict 통과", code == 0)
        else:
            check("md2hwpx --theme 생성", False,
                  f"(출력 없음: {r.stderr.strip()[:150]})")

    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
