# A/B Test Candidates

## Goal

Reduce the user's cleanup time after document analysis while still keeping the terms, expressions, and sentence patterns they will probably need later.

This is not a translation-quality test. The core question is:

> Does GemmaLens help a learner keep only useful learning objects with less manual work?

## Primary Metric

- Time from analysis result shown to "I am done organizing this document."

## Secondary Metrics

- Number of saved items the user later says are useful.
- Number of saved items the user deletes or ignores.
- Number of important items the user says were missed.
- Whether the user understands why each item was highlighted.
- Whether the user can continue reading without copy/paste into a translator.

## Test Setup

- Use the same short document for all variants.
- Start with Korean users learning English from a paper or movie/article excerpt.
- Keep support language and learning language selectable, but first test can default to Korean support and English learning.
- Use 5-8 users per round, fix obvious UX problems, then repeat.
- Do not test too many variants at once. Pick one decision per round.

## Variant 1: Dictionary Save Mode

Question: How much should the app decide automatically?

### A. Manual Save

The result shows suggested terms and expressions. User manually saves what they want.

Expected strength:
- User feels in control.
- Lower risk of saving junk.

Risk:
- Cleanup time may still feel like work.

### B. Auto-Save High Priority

The app automatically saves high-priority terms and expressions. User reviews and removes items.

Expected strength:
- Faster when model quality is good.
- Better for demos because the dictionary fills immediately.

Risk:
- Bad suggestions create cleanup burden.

Suggested first test:
- A vs B with 10-15 candidate items.
- Measure cleanup time and final useful saved count.

## Variant 2: Highlight Labels

Question: Which labels help the user decide quickly?

### A. Learning Priority Labels

- Must know
- Useful in this document
- Field term
- Seen before
- Low priority

Expected strength:
- Directly supports cleanup decisions.

Risk:
- "Must know" can feel too absolute if model confidence is weak.

### B. Reason Labels

- Blocks understanding
- Repeats in this document
- Important field term
- Academic expression
- Structure pattern

Expected strength:
- Explains why the item is shown.

Risk:
- More text to read.

Suggested first test:
- Ask user to keep or discard items from the analysis page.
- Measure how often they hesitate or ask "why this?"

## Variant 3: Result Layout

Question: What result page minimizes sorting effort?

### A. Table First

Show all terms and expressions in a dense table with filters.

Expected strength:
- Fast for advanced users.
- Good for scanning many items.

Risk:
- Feels like admin work.

### B. Reading Context First

Show the original paragraph with inline highlights. Side panel shows meaning, source sentence, and save action.

Expected strength:
- Keeps user in reading flow.
- Easier to understand contextual meaning.

Risk:
- Slower if user wants bulk cleanup.

Suggested first test:
- Same document, ask users to finish study setup.
- Compare total time and confidence in saved list.

## Variant 4: Dictionary Item Detail

Question: What minimum detail makes an item worth saving?

### A. Compact Item

- Term or expression
- Short support-language meaning
- Source sentence
- Save/view state

Expected strength:
- Low clutter.

Risk:
- Not enough for later review.

### B. Learning Card

- Term or expression
- Context meaning
- General meaning
- Source sentence
- Why important
- One extra example
- Save/view state

Expected strength:
- More useful later.

Risk:
- Too heavy during sorting.

Suggested first test:
- Use compact cards on result page.
- Use expanded cards only inside dictionary detail.

## Variant 5: Review State

Question: Which status model feels natural?

### A. Simple State

- New
- Viewed
- Familiar

Expected strength:
- Easy and low maintenance.

Risk:
- Weak for real learning progress.

### B. Study State

- New
- Review soon
- Familiar
- Mastered
- Ignore

Expected strength:
- Better for future review/quiz.

Risk:
- More decisions during cleanup.

Suggested first test:
- Keep simple state now.
- Add "Ignore" because avoiding bad items is part of minimizing cleanup time.

## Variant 6: User Fit Signal

Question: How should the app know what the user already knows?

### A. Ask During Onboarding

Ask target level, field, and known vocabulary confidence.

Expected strength:
- Better first analysis.

Risk:
- Onboarding friction.

### B. Learn From Actions

Infer from saved, ignored, viewed, and familiar items.

Expected strength:
- Less setup.
- Becomes more personalized over time.

Risk:
- Cold start is weaker.

Suggested first test:
- Minimal onboarding plus action learning:
  - support language
  - learning language
  - target level
  - current field/domain

## Recommended First A/B Round

Test only these:

1. Manual save vs auto-save high priority.
2. Learning priority labels vs reason labels.
3. Table-first result vs reading-context-first result.

Keep everything else stable.

## Current Prototype Switch

The analysis result page now includes browser-local A/B controls:

- Save mode: A manual save / B auto-save high priority.
- Labels: A learning priority / B reason shown.
- Layout: A table first / B reading context first.
- Item detail: A compact item / B learning card.
- Review state: A simple state / B study state.
- User fit: A ask during onboarding / B learn from actions.

Default is all A. The switch is intentionally local to the browser so the team can compare variants without database migration or backend deployment. On Vercel, `/analysis/demo` uses fixed sample data so reviewers can test these controls without a local model server. `/experiments` provides the full visible dashboard for team review.

## Discussion Questions For Team

- Are we optimizing for first demo speed or long-term learning value?
- Should dictionary store fewer high-confidence items or more candidate items with easy cleanup?
- Should "viewed" mean the user opened the card, or confirmed they understood it?
- Is the first vertical demo a paper, a movie/article excerpt, or both?
- Should the result page feel like a study desk, a document reader, or a data table?
- Which mistakes are worse: missing useful terms, or saving too many useless terms?

## Product Decision Leaning

Current best bet:

- Result page: reading context first, with a compact sortable list below.
- Highlight reason: show both priority and reason, but keep the label short.
- Dictionary: auto-save only high-confidence "must review" items, leave the rest as suggestions.
- User control: every saved item must be easy to ignore, delete, or mark familiar.
- Personalization: use user actions as the main signal, not long onboarding.
