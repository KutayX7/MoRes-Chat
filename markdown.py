
# Made entirely by @KutayX7
# None of the current AIs has managed make this properly

# TODO: Add subtext, lists, nested lists

_markdown_symbols = [
    ('header3', '\n### ', '\n', '\n'),
    ('header2', '\n## ', '\n', '\n'),
    ('header1', '\n# ', '\n', '\n'),
    ('underline+bold+italics', '__***', '***__', ''),
    ('underline+bold', '__**', '**__', ''),
    ('underline+italics', '__*', '*__', ''),
    ('bold+italics', '***', '***', ''),
    ('multiline_codeblock', '```', '```', ''),
    ('bold', '**', '**', ''),
    ('strikethrough', '~~', '~~', ''),
    ('codeblock', '`', '`', ''),
    ('italics', '*', '*', '')
]


# Don't ask me how this works
# Don't ask me to add more comments
# It just barely works
def parse_markdown(text: str) -> list[tuple[str, str]]:
    result = []
    buffer = "\n"
    mode = 'normal'
    def set_mode(m):
        nonlocal mode, buffer, result
        c = 1
        for t, s, e, a in _markdown_symbols:
            if t == m:
                c = len(s)
                if len(a) > 0:
                    result.append((a, 'normal'))
        result.append((buffer[:-c], mode))
        buffer = ''
        mode = m

    max_match_count = 0

    for char in text:
        buffer += char
        if mode == 'normal':
            match_count = 0
            matched_space = False
            for t, s, e, a in _markdown_symbols:
                if s == buffer[-len(s):]:
                    match_count += 1
                    if s[-1] == ' ':
                        matched_space = True
            if max_match_count > 0 and match_count == 0 and char != ' ':
                max_match_count = 0
                for t, s, e, a in _markdown_symbols:
                    if s == buffer[-len(s)-1:-1]:
                        buffer = buffer[:-1]
                        set_mode(t)
                        buffer += char
                        break
            elif match_count > max_match_count:
                max_match_count = match_count
            if mode == 'normal' and char in ' \n\\\t':
                if matched_space:
                    for t, s, e, a in _markdown_symbols:
                        if s == buffer[-len(s):]:
                            set_mode(t)
                            break
                else:
                    result.append((buffer[:-1], 'normal'))
                    buffer = char[:]
        else:
            for t, s, e, a in _markdown_symbols:
                if t == mode and e == buffer[-len(e):]:
                    result.append((buffer[:-len(e)], mode))
                    buffer = ''
                    mode = 'normal'
                    break
    if len(buffer) > 0:
        result.append((buffer, mode))
    if len(result) > 0:
        result[0] = (result[0][0][1:], result[0][1])
    result = list(filter(lambda wm: len(wm[0]) > 0, result))
    return result
