# Learning Research Notes

This note keeps only product-useful learning ideas. It is not a full literature review.

## 1. Do Not Save Every Unknown Word

Useful language-learning dictionaries should be selective. Unknown words are not equally valuable.

Product implication:
- Prioritize terms that block comprehension, repeat in the document, belong to the field, or appear in academic argument structure.
- Low-priority unknown words should stay visible as suggestions, not automatically become dictionary items.

Implementation hint:
- Add item fields later:
  - `learning_priority`: `must_review | useful | field_term | low_priority`
  - `reason`: short support-language explanation
  - `confidence`: model confidence estimate
  - `user_state`: `suggested | saved | ignored | viewed | familiar`

## 2. Context Meaning Beats Dictionary Meaning

For papers and technical text, the same word can matter differently by field and sentence.

Product implication:
- Each saved item should keep the source sentence.
- Show "meaning in this document" before general meaning.
- For expressions, explain function: claim, contrast, limitation, method, result, general.

Implementation hint:
- Keep `source_sentence` required for term, phrase, and sentence objects.
- Add `context_meaning` separately from `general_meaning`.

## 3. Difficulty Should Be Personalized

A document is not simply B2 or C1. It can be easy grammar but hard domain vocabulary, or familiar domain but hard syntax.

Product implication:
- Keep separate difficulty dimensions:
  - lexical
  - syntax
  - domain
- Use target level only as a user-fit reference, not as a fixed truth.

Implementation hint:
- Current schema already has `lexical_difficulty`, `syntax_difficulty`, and `domain_difficulty`.
- Later, combine these with user history: saved terms, ignored terms, viewed terms, and familiar terms.

## 4. Glosses Should Be Short

Inline help is useful when it reduces interruption. Too much explanation can become another reading task.

Product implication:
- First click should show a short gloss.
- Expanded detail can show examples, structure, and study notes.

Implementation hint:
- Result page: compact popover or side panel.
- Dictionary page: fuller learning card.

## 5. Retrieval Matters Later, Not During First Cleanup

The first product value is reducing cleanup and helping the user continue reading. Review and quiz can come later.

Product implication:
- Do not force quiz flow in the first demo.
- Track enough data now so future review is possible.

Implementation hint:
- Store `view_count`, `last_viewed_at`, and user state.
- Later add review scheduling only after users actually save useful items.

## 6. Multilingual Support Should Stay Schema-Level

The app should support user language and learning language combinations without hard-coding Korean-English everywhere.

Product implication:
- The user selects:
  - support language
  - learning language
  - target level
  - optional field/domain
- The model prompt decides output language, but saved objects should remain language-agnostic.

Implementation hint:
- Use language codes internally, display names in UI.
- Keep original text, support-language explanation, and learning-language examples as separate fields.

## 7. Test With Real Cleanup Tasks

Asking "is this useful?" is weaker than watching whether the user can finish organizing a real document quickly.

Product implication:
- A/B tests should measure behavior:
  - time to done
  - saved useful count
  - deleted/ignored count
  - missed important items
  - confusion points

Implementation hint:
- Add lightweight event logging later:
  - analysis completed
  - item saved
  - item ignored
  - item viewed
  - item marked familiar
  - dictionary opened

## Useful References

- CEFR level descriptions: https://www.coe.int/en/web/common-European-framework-reference-languages/table-1-cefr-3.3-common-reference-levels-global-scale
- W3C language tags and locale identifiers: https://www.w3.org/TR/ltli/
- Nielsen Norman Group usability testing basics: https://media.nngroup.com/media/articles/attachments/Usability-Testing-101_SizeA4.pdf
- Paul Nation vocabulary resources: https://www.wgtn.ac.nz/lals/resources/paul-nations-resources/paul-nations-publications
- Retrieval practice overview: https://link.springer.com/article/10.1186/s41235-017-0087-y
