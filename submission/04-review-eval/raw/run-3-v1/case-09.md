## Review of case-09

**Finding 1: README.md, new line "To reset the sample data without restarting, sign out and sign in again." (hunk at line 18)**
- What goes wrong: the diff changes no code, so nothing in it makes sign-out or sign-in reseed data. The preceding sentence says the data lives in an in-memory store that is "recreated on every start". A restart is the only reset the text supports. If sign-in does not reseed, a reader who follows this instruction will think the data was reset when it was not. If sign-in does reseed, that is an unusual behavior, and it would have to be implemented somewhere that is not in this diff.
- Confidence: medium. I can only see the diff, so I can't rule out that reseeding on sign-in exists elsewhere. Someone should confirm it against the auth and seeding code or remove the sentence.

**Finding 2: README.md, "These accounts exist only in the in-memory store" (low confidence, about 25%)**
- This is a factual claim about where accounts are stored. I can't verify it from the diff. Check that the demo accounts really come from the same in-memory store as the invoice data and not from separate auth configuration.

**appsettings.json**
- Adding `"Microsoft.AspNetCore": "Warning"` is valid JSON, and the trailing-comma handling is correct. It only reduces framework log noise. I found no defect.

Apart from the findings above, I found no defects.
