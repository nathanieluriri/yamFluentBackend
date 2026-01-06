Mispronounced words flow

This is how mispronounced words are produced based on the current code:

1) ASR transcript
- In `controller/grading/calculate_turn_score.py`, `_run_asr()` sends the uploaded audio to OpenAI and returns a transcript.
- The expected text is the script text for the current user turn.

2) Tokenization
- `controller/grading/text_align.py:tokenize` lowercases and strips punctuation, then splits on whitespace.
- Example: "I don't know." becomes ["i", "don't", "know"].

3) Word alignment
- `controller/grading/text_align.py:align_words` uses an edit-distance DP to align expected vs actual tokens.
- It produces `AlignmentResult` with substitutions, insertions, deletions, and `aligned_pairs`.

4) Mispronounced extraction
- `controller/grading/scoring.py:build_mispronounced_words` iterates over aligned pairs.
- It ignores pairs where either side is empty (insertions/deletions).
- It ignores exact matches.
- It only marks a word as mispronounced if the normalized edit distance between expected and actual is <= 0.4.
  - This is the key detail: it only captures "close but not exact" words.
  - Example: expected "coffee" vs actual "cofee" might count; expected "coffee" vs actual "tea" will NOT count.
- It de-duplicates repeated expected words.

5) Stored on the turn
- `controller/grading/calculate_turn_score.py` puts the list into `TurnUpdate.mispronounced_words`.


Why it can look like it is not working

- The <= 0.4 threshold means only near-matches are flagged as mispronounced.
  - If a user says a totally different word, it shows up as a substitution in WER,
    but will not be listed as "mispronounced".
- Insertions/deletions are ignored for mispronounced words, so missing words
  and extra words are never listed.
- Tokenization strips punctuation and lowercases, so differences in casing or
  punctuation do not count toward mispronunciation.
- If ASR returns a transcript that differs a lot (background noise, fast speech,
  clipped audio), mispronounced words can end up empty even though the match is bad,
  because differences become substitutions/insertions/deletions instead of near-matches.


Where to look if you want different behavior

- `controller/grading/scoring.py:build_mispronounced_words`
  - Adjust the distance threshold or logic.
  - Include substitutions with higher distance (e.g., <= 0.6).
  - Optionally include deletions/insertions as mispronounced (or a separate list).
- `controller/grading/text_align.py:tokenize`
  - Adjust tokenization rules (e.g., keep hyphens, handle contractions).

