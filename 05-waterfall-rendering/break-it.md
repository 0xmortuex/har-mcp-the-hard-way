# Break It: Waterfall Rendering

## Challenge 1: Round each phase on its own

In `bar()`, replace the cumulative boundaries with `length = round(p[name] * scale)` and drawing
from a running column. Which assertion fails first? Compare the drawn length of entry 0 (316 ms,
seven phases) to what it should be.

## Challenge 2: Remove the `#` mark

Delete the `if not drawn` branch. Which assertion fails? Imagine an agent reading a waterfall in which
a 1 ms request has no row content. What would it conclude?

## Challenge 3: Ignore redirects in the critical path

Remove the `via_redirect` branch. The chain changes from `[0, 1, 4, 5]` to something else. Which, and
why does the /home request now hang off a different parent?

## Challenge 4: Pick the slowest request instead

Replace the chain selection with "the chain ending at the slowest request". Run module 05 and
explain in one sentence why the answer is wrong for "what decided when loading finished?".

## Challenge 5: Make the fallback greedy

In the fallback, replace the dynamic programme with "sort by start, take a request if it does
not overlap the last one taken". On the hand-made case it happens to agree with `[0, 2]`, so no assertion fails: that is a weak
test. Construct a case where greedy-by-start loses regardless of how ties are ordered (hint: one long
request starting at 0, and three short ones inside it that do not overlap each other), add it to
`main.py`, and confirm the DP wins.
