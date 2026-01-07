## Plan: Speech Analysis Persistence & Coaching Tips

This plan describes how to persist detailed speech-analysis artifacts for every graded turn and build an idempotent coaching-tips feature. It follows the existing FastAPI + MongoDB patterns and reuses the current grading/OpenAI helpers.

### Repo Notes (discovery)
- DB: MongoDB via `core.database.db` (motor). Collections already in use: `sessions`, `users`, `accessToken`, etc. Schemas are Pydantic v2 style (`model_dump`, validators).
- Sessions: `schemas.session.SessionOut` includes `script: FluencyScript` with `Turn` objects (role/text/score/mispronounced_words/user_audio_url/model_audio_url). Updates flow through `services.session_service.update_session_by_id` → `controller.grading.calculate_turn_score` → `repositories.session.update_session` (uses `$set`/`array_filters`).
- Grading pipeline: `calculate_turn_score` calls `_run_asr` (OpenAI), `tokenize` and `align_words` in `controller/grading/text_align`, `compute_scores` in `controller/grading/scoring` (returns alignment + mispronounced words).
- User profiling: `UserPersonalProfilingData` in `schemas/user_schema.py` (nativeLanguage, currentProficiency, mainGoals, learnerType, dailyPracticeTime). Scripts already rely on this.
- OpenAI helpers: `controller/script_generation/clients.py` provides AsyncOpenAI client, rate limits, and retry helper `openai_request_with_retries`.
- Existing coaching_tips files are auto-generated CRUD placeholders; we will replace with purposeful models/routes/services.

---

### Part A: Speech Analysis Persistence
1) **Add speech-analysis schemas**
   - New module `schemas/speech_analysis.py` defining:
     - `WordTiming`, `Token` (idx, text, timing/confidence optional).
     - `ASRMeta` (model, parameters, timestamps), `TokenizationMeta` (rules, normalization flags), `AlignmentMeta` (algorithm, threshold, ignore_insertions/deletions flags).
     - `AlignedPair` (op: eq/sub/ins/del, expected_idx/actual_idx, expected, actual, edit_distance, normalized_edit_distance).
     - `AlignmentSummary` (substitutions, insertions, deletions, correct, wer).
     - `MispronouncedLogicMeta` (threshold, dedupe flags, ignores).
     - `MispronouncedWord` (expected, actual, expected_idx, actual_idx, normalized_edit_distance, reason, timings optional, deduped flag).
     - `IgnoredDifference` (op, ignored_because enum: insertion/deletion/too_far_from_expected/exact_match/empty_side/deduped).
     - `TurnSpeechAnalysis` top-level with required fields: `expected_text`, `asr_text`, `asr_meta`, `tokenization_meta`, `alignment_meta`, `mispronounced_logic_meta`, `expected_tokens`, `actual_tokens`, `aligned_pairs`, `alignment_summary`, `mispronounced_words`, `ignored_differences`, `extra: Dict[str, Any] = {}`.
   - Keep types JSON-serializable; include `Config` for aliasing if needed (match other schemas).

2) **Build speech-analysis object during grading**
   - Add a helper (e.g., `controller/grading/speech_analysis_builder.py`) that accepts:
     - expected_text, asr_text
     - expected_tokens, actual_tokens
     - alignment (from `align_words`)
     - mispronounced_words (existing list)
     - threshold/flags from current logic (0.4 threshold, ignore insertions/deletions, dedupe)
   - Compute aligned pairs with indices and edit distances; classify ops: `eq/sub/ins/del`.
   - Build `alignment_summary` with counts + WER = (S+I+D)/N_expected.
   - Populate `ignored_differences`:
     - insertions → op="insert", ignored_because="insertion"
     - deletions → op="delete", ignored_because="deletion"
     - substitutions where `normalized_edit_distance` > threshold → ignored_because="too_far_from_expected"
     - exact matches skipped from mispronounced → ignored_because="exact_match"
     - deduped near-misses → ignored_because="deduped"
   - Timings/confidence can be `None` if not provided by ASR.

3) **Extend Turn storage**
   - Add optional `speech_analysis: Optional[TurnSpeechAnalysis] = None` to `schemas.imports.Turn` and to `TurnUpdate`/`ScriptTurnsUpdate` so updates can carry it.
   - No Mongo migration needed, but ensure JSON serializable via `.model_dump()`.

4) **Persist during grading**
   - In `calculate_turn_score`, after computing alignment and mispronounced words, build the `TurnSpeechAnalysis` object.
   - Add it to `TurnUpdate` (e.g., `speech_analysis=speech_analysis`).
   - Include the raw ASR transcript already returned in `response` for debug if present; do not change existing response keys.
   - Update `repositories.session.update_session` to accept `speech_analysis` inside turn updates (existing dynamic `$set` already works, but confirm no exclude list).

5) **Tests (unit-level)**
   - Add `tests/test_speech_analysis.py` (or similar) with a pure-function test of the builder:
     - Given expected_text/actual_text and known tokens/alignment, assert `TurnSpeechAnalysis.model_dump()` contains expected aligned pairs, summary WER, mispronounced_words, and ignored_differences entries.
   - Keep tests minimal/no network; use pytest (add to dev deps if required).

Example builder sketch:
```python
analysis = build_speech_analysis(
    expected_text="I like coffee",
    asr_text="i like cofee",
    expected_tokens=["i", "like", "coffee"],
    actual_tokens=["i", "like", "cofee"],
    alignment=alignment,
    mispronounced_words=["coffee"],
    threshold=0.4,
)
```

---

### Part B: Coaching Tips Feature
1) **Data model**
   - Replace/augment `schemas/coaching_tips.py` with purposeful models:
     - `CoachingTipCreate` (session_id: str).
     - `CoachingTipOut` (id, session_id, user_id, tip_text, practice_words: List[str] | None, feedback/context metadata: dict, provider_meta: dict, prompt_version default "v1", created_at: datetime/int).
     - `CoachingTipListItem` (id, session_id, created_at, short_preview).
   - `TurnSpeechAnalysis` should be serializable inside `feedback/context` for reuse.
   - Repository layer (`repositories/coaching_tips.py`):
     - Use `db.coaching_tips` (rename from `coaching_tipss`) with unique index on `session_id` (and optionally user_id) to enforce one tip per session.
     - Functions: `find_one`, `insert_one`, `find_many` with user scoping.

2) **Service logic**
   - New service function `generate_or_get_coaching_tip(session_id: str, user_id: str)`:
     - Fetch existing tip by session_id + user_id → return if found.
     - Load session (`get_session`) ensuring `userId` matches.
     - Aggregate grading data:
       - Per-turn scores (confidence/fluency/hesitation), mispronounced_words.
       - New `speech_analysis` artifacts: expected_text/asr_text, mispronounced_words, ignored_differences, alignment summary.
       - Session metadata: scenario, lesson topic if available.
     - Load user profiling (`userPersonalProfilingData`).
     - Build compact AI prompt (<=280 chars result) requesting JSON:
       ```json
       {"tip_text": "...", "practice_words": ["w1","w2"]}
       ```
       - Instruct to use profiling + session scores + mispronunciations; include practice words if possible; avoid metrics jargon.
     - Call OpenAI via existing `get_openai_client` + `openai_request_with_retries`, low temperature (e.g., 0.3), small max tokens.
     - Parse JSON safely; on failure, fallback heuristic: assemble tip from common mispronounced words/ignored substitutions.
     - Insert new tip document; on duplicate key error, fetch existing and return.

3) **API endpoints (FastAPI)**
   - New router `api/v1/coaching_tips.py` (replace current scaffold) with prefix `/users/v1/coaching-tips` (consistent with session routes) and auth dependency `verify_token_user_role`.
   - Routes:
     - `POST /` → body `{ "session_id": "..." }` → calls `generate_or_get_coaching_tip` using `accessToken.userId`.
     - `GET /` → list tips for current user (lightweight `CoachingTipListItem`).
     - `GET /{id}` → detail for one tip (ensure user owns it).
   - Update `main.py` to include the router.

4) **Response schemas**
   - Wrap responses in `APIResponse[...]` as existing routes do.
   - List response should be small (id, session_id, created_at, optional preview).
   - Detail response includes: id, session_id, user_id, tip_text, practice_words, provider_meta, feedback/context (includes speech_analysis), prompt_version, created_at.

5) **Tests**
   - Add service-level tests (mock OpenAI) to verify:
     - Idempotence: second call returns existing tip without new OpenAI call (can simulate by pre-inserting in mock DB or stubbing repository).
     - Fallback logic produces short tip when AI parsing fails.
   - Keep tests fast/offline; consider dependency injection for OpenAI client or add a flag to bypass network.

Example prompt skeleton:
```
System: You are a concise pronunciation coach. Use profile, grades, and alignment insights to craft one actionable tip (<=280 chars). Include 2-6 single-word practice words if helpful. No metrics, no jargon.
User data JSON: {...profile..., "scores": {...}, "speech_analysis": [...], "scenario": "..."}
Return JSON: {"tip_text": "...", "practice_words": ["..."]}
```

---

### Rollout Steps
- [x] Implement schemas (`speech_analysis.py`, coaching tip schemas) and update imports.
- [x] Add speech-analysis builder + integrate into `calculate_turn_score`; ensure `SessionUpdate` carries `speech_analysis`.
- [x] Update repository/service layers to persist speech_analysis and new coaching tip logic (unique constraint).
- [x] Build coaching tips router and include in `main.py`.
- [x] Add tests for speech-analysis builder (unit-level).
- [x] Run code compilation/tests locally (py_compile).

After completing implementation, share endpoints and any new env vars (e.g., OPENAI model names if added). Restarting app may be needed to apply Mongo indexes.
