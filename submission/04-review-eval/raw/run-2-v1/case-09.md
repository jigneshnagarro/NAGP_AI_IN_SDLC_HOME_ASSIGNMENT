Review of case-09 diff

Finding 1
- File: README.md (added line "To reset the sample data without restarting, sign out and sign in again.")
- Line: about line 22 of the new file (the added paragraph after the demo-accounts sentence)
- What goes wrong: The new text says that signing out and back in resets the sample data. Nothing in this diff supports that. The previous sentence says the data lives in an in-memory store that is recreated only on process start. Sign-in and sign-out are session and auth operations, and they would not normally reseed a repository. If the claim is wrong, users will expect data to be restored and it will not be. I could not check the sign-in code from this diff alone, since the diff shows no code change that implements a reset on sign-in.
- Confidence: medium (about 60%). The claim is unsupported by the diff and contradicts the sentence above it, but I cannot see the auth code.

Finding 2
- File: backend/src/InvoiceApp.Api/appsettings.json
- Line: 4-5 (added "Microsoft.AspNetCore": "Warning")
- What goes wrong: Nothing is wrong. The JSON is valid, because the comma was added after "Default". This only reduces ASP.NET Core framework log noise.
- Confidence: high that it is fine. I am not reporting a defect here.

Summary: One possible defect, the unsupported "sign out and sign in again resets the data" claim in README.md. The appsettings.json change is fine.
