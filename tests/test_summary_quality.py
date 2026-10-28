"""Quality observations from independent summary generation, without wording locks."""

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

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
import render_hwpx
from structured_document import input_findings
from table_diagram import render


class SummaryQualityTests(unittest.TestCase):
    def test_escape_warning_preserves_text_and_distinguishes_newline_paths(self):
        spec = {
            "blocks": [
                {"type": "paragraph", "text": r"예시 \n 표시"},
                {"type": "paragraph", "text": "실제\n줄바꿈"},
                {"type": "image", "path": r"C:\new\test.png", "alt": "그림"},
            ]
        }
        before = copy.deepcopy(spec)
        findings = input_findings(spec)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["pointer"], "/blocks/0/text")
        self.assertEqual(spec, before)

    def test_escape_policy_respects_fail_on_warnings(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            spec = {
                "version": 2,
                "kind": "brief-report",
                "output": "out.hwpx",
                "title": "문자 표시",
                "blocks": [{"type": "paragraph", "text": r"문자열 예시 \n 표시"}],
                "quality": {"hancom": "off", "writing": "off"},
            }
            result = one_shot.build(spec, spec_dir=base)
            self.assertTrue(result["published"])
            self.assertEqual(
                result["checks"]["input_text"]["findings"][0]["code"], "LITERAL_ESCAPE"
            )
            original = (base / "out.hwpx").read_bytes()
            spec["quality"]["fail_on_warnings"] = True
            result = one_shot.build(spec, spec_dir=base)
            self.assertFalse(result["published"])
            self.assertEqual((base / "out.hwpx").read_bytes(), original)

    def test_direction_reason_does_not_change_graph(self):
        class Styles:
            node = none = branch = "1"

            def paragraph(self, text):
                return "<hp:p/>"

        nodes = [{"id": str(i), "title": "단계"} for i in range(6)]
        diagram = {
            "pattern": "process",
            "nodes": nodes,
            "edges": [
                {"from": str(i), "to": str(i + 1), "label": "검토 조건"}
                for i in range(5)
            ],
        }
        original = copy.deepcopy(diagram)
        _, report = render(diagram, Styles(), 49000)
        self.assertEqual(report["requested_direction"], "auto")
        self.assertEqual(report["direction"], "vertical")
        self.assertIn("below 6000", report["direction_reason"])
        self.assertEqual(diagram, original)
        diagram["direction"] = "horizontal"
        _, report = render(diagram, Styles(), 49000)
        self.assertEqual(report["direction"], "horizontal")
        self.assertEqual(report["direction_reason"], "explicit")

    def test_render_page_contract_is_not_visual_approval(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            source = base / "in.hwpx"
            source.write_bytes(b"mock document")

            def fake_hancom(source, pdf):
                pdf.write_bytes(b"mock pdf")
                return {"ok": True, "status": "passed", "pages": 2}

            def fake_poppler(command, **kwargs):
                prefix = Path(command[-1])
                for index in (1, 2):
                    prefix.with_name(f"page-{index}.png").write_bytes(b"mock png")

            with (
                patch("render_hwpx.shutil.which", return_value="poppler"),
                patch("render_hwpx.run_hancom", side_effect=fake_hancom),
                patch("render_hwpx.subprocess.run", side_effect=fake_poppler),
            ):
                result = render_hwpx.render_document(
                    source, base / "bad", expected_pages=1
                )
                self.assertFalse(result["ok"])
                self.assertTrue(result["render_ok"])
                self.assertEqual(result["page_count_check"]["actual"], 2)
                self.assertEqual(result["visual_review"]["status"], "not_run")
                result = render_hwpx.render_document(
                    source, base / "good", expected_pages=2
                )
                self.assertTrue(result["ok"])
                self.assertTrue(
                    json.loads((base / "good/render.json").read_text(encoding="utf-8"))[
                        "page_count_check"
                    ]["ok"]
                )
            with patch("render_hwpx.shutil.which", return_value=None):
                result = render_hwpx.render_document(
                    source, base / "missing", expected_pages=1
                )
                self.assertIsNone(result["page_count_check"]["ok"])
            with self.assertRaises(ValueError):
                render_hwpx.render_document(source, base / "invalid", expected_pages=0)


if __name__ == "__main__":
    unittest.main()
