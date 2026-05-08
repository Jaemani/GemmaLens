# Model Benchmark Results

Date: 2026-05-08

Environment:

- Runtime: local MLX on Apple Silicon GPU
- Models:
  - `gemma4-e2b-mlx`: `~/Models/mlx/gemma-4-e2b-it-bf16`
  - `gemma4-e4b-mlx`: `~/Models/mlx/gemma-4-e4b-it-bf16`
- Script: `scripts/model_benchmark.py`
- Samples:
  - `academic_sleep`
  - `technical_docs`
  - `film_review`

## Summary

| Preset | Avg Duration | Avg Terms | Avg Phrases | Total Warnings | Summary Complete |
| --- | ---: | ---: | ---: | ---: | --- |
| Gemma 4 E2B MLX bf16 | 60.53s | 7.33 | 4.33 | 0 | 3/3 |
| Gemma 4 E4B MLX bf16 | 123.23s | 6.67 | 3.67 | 0 | 3/3 |

## Per-Sample Results

| Preset | Sample | Duration | Terms | Phrases | Sentences | Study Notes | Warnings |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| E2B | academic_sleep | 61.07s | 6 | 4 | 2 | 5 | 0 |
| E2B | technical_docs | 60.39s | 8 | 5 | 2 | 4 | 0 |
| E2B | film_review | 60.14s | 8 | 4 | 2 | 4 | 0 |
| E4B | academic_sleep | 137.64s | 6 | 3 | 2 | 3 | 0 |
| E4B | technical_docs | 116.04s | 8 | 4 | 2 | 3 | 0 |
| E4B | film_review | 116.02s | 6 | 4 | 2 | 3 | 0 |

## Engineering Notes

- Initial sandbox run could not access Metal GPU and fell back to mock output. The benchmark must run with local GPU/Metal access.
- A preset-path bug was found during measurement: benchmark config wrote only `preset_id`, but runtime config did not expand that preset into its MLX model path. This is now fixed in `ModelRuntimeService`.
- E2B appears strong enough for functional UI/product testing: it produced complete structured results with no quality warnings and roughly half the E4B runtime on these samples.
- E4B is slower but also stable. It did not show an obvious structural-completeness advantage on this small sample set.

## Next Measurement Work

- Add longer excerpts to test context length and timeout behavior.
- Add Korean-support output checks for explanations.
- Add repeated-run variance checks, especially for E2B.
- Add scoring beyond structural completeness: usefulness of selected terms, over-obvious terms, and missed important terms.
