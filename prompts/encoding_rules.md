# Encoding Rules

The project runs on Windows and contains older files that may be UTF-8 or GBK.

## Reading

- Text reads should prefer `read_text_auto`.
- Try UTF-8 first.
- If the decoded text contains mojibake markers, retry GBK.
- JSON reads should use the shared JSON helper so the same fallback behavior applies.

## Writing

- New prompt, JSON, CSS, HTML, and JavaScript files should be UTF-8 unless there is a strong compatibility reason.
- Avoid adding Chinese comments or string literals to legacy GBK Python files unless the file is being intentionally normalized.
- Do not mass-convert encodings during unrelated feature work.

## Frontend

- The web server must serve HTML, CSS, and JavaScript as UTF-8.
- If the browser displays mojibake, fix the source file encoding or the literal text, not the campaign memory.
