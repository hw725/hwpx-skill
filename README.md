# hwpx (벤더링본)

이 폴더는 [jkf87/hwpx-skill](https://github.com/jkf87/hwpx-skill)을 커밋 `ba90fc5`(2026-09-15)에 고정해 들여온 스킬이다. 상류에는 라이선스 파일이 없다(NOTICE.md §4).

- 사용법·라우팅의 정본은 `SKILL.md`다. 확장자를 정하지 않은 한글 문서 요청은 `hwp` 스킬이 먼저 받는다.
- 상류 동기화 계약(고정 커밋·받는 경로·받지 않는 경로·지켜야 할 로컬 분기)은 `.upstream.json`에 있고, `py -3 scripts/sync_upstream.py --dry-run vendor/hwpx`가 그것을 읽는다.
- 상류의 README·RELEASE_NOTES는 저장소 소개 문서라 받지 않는다. 이 파일은 그 자리를 채우는 로컬 안내문이며, `tests/test_retired_templates.py`가 이 파일을 읽는다.
- 서드파티 고지는 `THIRD_PARTY_NOTICES.md`·`licenses/`·`scripts/vendor/rhwp/LICENSE`(MIT)에 있다.
