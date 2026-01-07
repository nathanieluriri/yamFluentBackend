# Walkthrough of Changes

## Speech Analysis Persistence
- Added `schemas/speech_analysis.py` defining full ASR/tokenization/alignment artifacts (tokens, aligned pairs, summaries, mispronounced logic/words, ignored differences, metadata containers).
- Implemented builder `controller/grading/speech_analysis_builder.py` to convert grading intermediates into `TurnSpeechAnalysis`, capturing ops, edit distances, WER, mispronunciation reasoning, and ignored differences (insert/delete/too-far/exact/deduped).
- Extended turn schemas (`schemas/imports.py`) to carry `speech_analysis` on `Turn` and `TurnUpdate`.
- Updated grading flow (`controller/grading/calculate_turn_score.py`) to:
  - Return ASR transcript with meta data.
  - Build and persist `speech_analysis` alongside scores and mispronounced words.
  - Use shared mispronunciation threshold constant (`controller/grading/scoring.py`).
- Enabled re-grading of turns by removing the “score already present” short-circuit and disabling noisy debug logging (`services/session_service.py`).
- Added unit test `tests/test_speech_analysis_builder.py` verifying near-miss handling, WER math, and ignored-difference logging; added `pytest` to requirements. Verified compilation via `python3 -m compileall`.

## Coaching Tips Feature
- Rebuilt coaching tip schemas (`schemas/coaching_tips.py`): request, create payload, response with provider_meta/feedback/prompt_version, and lightweight list items.
- Replaced repository layer (`repositories/coaching_tips.py`) with `coaching_tips` collection, unique (session_id, user_id) index, scoped getters, lister, and updater.
- Implemented service logic (`services/coaching_tips_service.py`):
  - Idempotent `generate_or_get_coaching_tip` that checks existing tips, loads session/user profile, aggregates scores + mispronunciations + speech-analysis traces, and generates a concise AI tip (JSON contract) with fallback heuristic and duplicate-key handling.
  - OpenAI call uses existing client/retry helpers, low temperature, and safe parsing; failures fall back to heuristic tips.
  - List and detail helpers scoped per user.
- Replaced API router (`api/v1/coaching_tips.py`) with authenticated endpoints:
  - `POST /users/v1/coaching-tips` create/idempotent
  - `GET /users/v1/coaching-tips` list (lightweight)
  - `GET /users/v1/coaching-tips/{tip_id}` detail
- Wired router into app (`main.py`) under `/users/v1`.
- Default DB type now MongoDB in `core/database.py` to match Motor-based repos.

## Bug Fixes from Potential Findings
- Fixed broken/typoed coaching tips paths and collection names; added user scoping and correct service call signatures.
- Restored session routes to `/users/v1` and kept admin router out of the public schema.
- Removed grading debug noise and enabled reprocessing when a turn already had a score.

## Notes on Usage
- Speech-analysis JSON now persists per graded turn (field `speech_analysis`) and is accessible in session documents.
- Coaching tips are one-per-session-per-user enforced both in code and DB unique index; repeated POST returns the existing tip.
- Heuristic tip generation is used automatically if the AI response is missing or unparsable.
