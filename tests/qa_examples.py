"""Explicit, opt-in Hancom page evidence for representative workflows."""

import argparse
import copy
import json
from pathlib import Path
import sys

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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import one_shot
from fill_hwpx import replace_hwpx
from layout_repair import repair_layout
from quality_gate import run_quality_gate
from render_hwpx import render_document
from test_structured_document import example


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = args.output.resolve()
    if base.exists() and any(base.iterdir()):
        raise ValueError("QA output must be new or empty")
    base.mkdir(parents=True, exist_ok=True)
    specs = {f"markdown-{p}": example(p) for p in ("process", "hierarchy", "swimlane")}
    specs["brief-process"] = example("process", "brief-report")
    specs["plan-process"] = example("process", "plan-report")
    specs["official-letter"] = copy.deepcopy(one_shot.EXAMPLES["official-letter"])
    specs["multi-page"] = {
        "version": 2,
        "kind": "markdown",
        "output": "multi.hwpx",
        "title": "AX 실행 계획 검증 자료",
        "profile": "public",
        "metadata_date": "2026-08-25",
        "blocks": [{"type": "heading", "text": "첫째 단계: 현황 진단"}]
        + [
            {
                "type": "paragraph",
                "text": f"과제 {i}: 업무 수요와 데이터 품질을 확인하고 검증 결과를 기록함",
            }
            for i in range(1, 9)
        ]
        + [{"type": "pagebreak"}, {"type": "heading", "text": "둘째 단계: 시범 적용"}]
        + [
            {
                "type": "paragraph",
                "text": f"과제 {i}: 담당 부서와 성과 기준을 합의하고 적용 결과를 공유함",
            }
            for i in range(9, 17)
        ],
        "quality": {"hancom": "off"},
    }
    reports = {}
    for name, spec in specs.items():
        spec["output"] = str(base / f"{name}.hwpx")
        spec.setdefault("quality", {})["hancom"] = "off"
        built = one_shot.build(spec, spec_dir=base)
        assert built["ok"], built["errors"]
        rendered = render_document(Path(spec["output"]), base / (name + "-pages"))
        reports[name] = {"build": built, "render": rendered}
        print(name, rendered["ok"], rendered.get("pages"), flush=True)
    edited = base / "edited-label.hwpx"
    replace_hwpx(
        str(base / "markdown-process.hwpx"),
        str(edited),
        {"현황 진단": "현황·업무 진단"},
    )
    repairs = repair_layout(edited)
    checked = run_quality_gate(
        edited, required_text=["현황·업무 진단", "우선과제 선정"], hancom="off"
    )
    assert checked["ok"], checked["errors"]
    reports["edited-label"] = {
        "check": checked,
        "repairs": repairs,
        "render": render_document(edited, base / "edited-label-pages"),
    }
    (base / "qa.json").write_text(
        json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return int(any(not value["render"]["ok"] for value in reports.values()))


if __name__ == "__main__":
    sys.exit(main())
