import json, re

p = r'v:\TRPG\trpg_orchestrator\outbox\chatgpt_raw_output.md'
t = open(p, 'r', encoding='utf-8').read()

# 1. Replace curly quotes with straight quotes
t = t.replace('\u201c', '"').replace('\u201d', '"')

# 2. In body fields, internal double quotes need to be escaped
# Strategy: find all "body": "..." patterns and escape quotes inside the body value
# We'll use a regex to find body values and escape internal quotes

def escape_inner_quotes(match):
    prefix = match.group(1)  # "body": "
    content = match.group(2) # the body text
    suffix = match.group(3)  # ",
    # Escape any unescaped double quotes inside content
    content = content.replace('"', '\\"')
    return prefix + content + suffix

# Match "body": "...content...",
pattern = r'("body"\s*:\s*")(.*?)(",?\s*)$'

# This is tricky because body spans multiple lines. Let's try a different approach.
# First, let's find all body values manually.

# Simpler approach: parse the JSON manually, fix, and reconstruct
# Since we know the structure, let's find each body field and escape quotes

lines = t.split('\n')
result = []
in_body = False
body_accumulator = []

for line in lines:
    stripped = line.strip()
    
    if not in_body and '"body":' in stripped:
        in_body = True
        body_accumulator = [line]
        continue
    
    if in_body:
        body_accumulator.append(line)
        # Check if body ends: line ends with ",\n  or "\n}
        if stripped.endswith('",') or stripped.endswith('"'):
            in_body = False
            full_body_text = '\n'.join(body_accumulator)
            
            # Extract the value part
            # Find start of body value
            start_marker = '"body": "'
            idx = full_body_text.index(start_marker)
            value_start = idx + len(start_marker)
            
            # Find the closing quote - it's the last '"' followed by ',' or end
            # Actually, we need to find the LAST '"' that is the JSON string delimiter
            # The last '"' in the last line that ends with '",' or '"'
            
            # Strategy: take everything between value_start and the LAST '"' that closes the string
            last_line = body_accumulator[-1]
            if last_line.strip().endswith('",'):
                # Find the last '"' before '",'
                value_end_in_last_line = last_line.rstrip().rindex('",')
                # Calculate global position
                preceding_lines_len = sum(len(l) + 1 for l in body_accumulator[:-1])
                value_end = preceding_lines_len + value_end_in_last_line
            elif last_line.strip().endswith('"'):
                value_end_in_last_line = last_line.rstrip().rindex('"')
                preceding_lines_len = sum(len(l) + 1 for l in body_accumulator[:-1])
                value_end = preceding_lines_len + value_end_in_last_line
            else:
                raise ValueError(f"Cannot find end of body: {last_line}")
            
            body_value = full_body_text[value_start:value_end]
            # Escape internal quotes in body value
            escaped_value = body_value.replace('"', '\\"')
            
            # Reconstruct
            prefix = full_body_text[:value_start]
            suffix = full_body_text[value_end:]
            fixed = prefix + escaped_value + suffix
            result.append(fixed)
            continue
    
    if not in_body:
        result.append(line)

fixed_text = '\n'.join(result)
open(p, 'w', encoding='utf-8').write(fixed_text)

# Verify
try:
    data = json.load(open(p, 'r', encoding='utf-8'))
    print(f'JSON OK! blocks: {len(data.get("blocks", []))}')
    for b in data['blocks']:
        print(f'  - {b["type"]}: {b.get("body", "")[:40]}...')
except json.JSONDecodeError as e:
    print(f'Error: {e}')
    t2 = open(p, 'r', encoding='utf-8').read()
    start = max(0, e.pos - 60)
    end = min(len(t2), e.pos + 60)
    print(f'Context: {repr(t2[start:end])}')
