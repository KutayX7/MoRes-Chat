
# Made entirely by @KutayX7
# None of the current AIs has managed make this properly

# TODO: Add lists, nested lists

# Heavily inspired by Discord's markdown
_markdown_symbols = [
    ('header3', '\n### ', '\n', '\n', '\n'),
    ('header2', '\n## ', '\n', '\n', '\n'),
    ('header1', '\n# ', '\n', '\n', '\n'),
    ('subtext', '\n-# ', '\n', '\n', '\n'),
    ('underline+bold+italics', '__***', '***__', '', ''),
    ('underline+bold', '__**', '**__', '', ''),
    ('underline+italics', '__*', '*__', '', ''),
    ('bold+italics', '***', '***', '', ''),
    ('multiline_codeblock', '```', '```', '', ''),
    ('bold', '**', '**', '', ''),
    ('strikethrough', '~~', '~~', '', ''),
    ('codeblock', '`', '`', '', ''),
    ('italics', '*', '*', '', '')
]


# Don't ask me how this works
# Don't ask me to add more comments
# It just barely works
def parse_markdown(text: str) -> list[tuple[str, str]]:
    result = []
    buffer = "\n" # we start with a newline to allow headers to be used in the first line
    current_tag = 'normal'
    def switch_to_tag(t):
        nonlocal current_tag, buffer, result
        c = 1
        for tag, start_seq, end_seq, prefix, suffix in _markdown_symbols:
            if tag == t:
                c = len(start_seq)
                if len(prefix) > 0:
                    result.append((prefix, 'normal'))
        result.append((buffer[:-c], current_tag))
        buffer = ''
        current_tag = t

    max_match_count = 0

    for char in text:
        buffer += char
        if current_tag == 'normal':
            match_count = 0
            matched_space = False
            for tag, start_seq, end_seq, prefix, suffix in _markdown_symbols:
                if start_seq == buffer[-len(start_seq):]:
                    match_count += 1
                    if start_seq[-1] == ' ':
                        matched_space = True
            if max_match_count > 0 and match_count == 0 and char != ' ':
                max_match_count = 0
                for tag, start_seq, end_seq, prefix, suffix in _markdown_symbols:
                    if start_seq == buffer[-len(start_seq)-1:-1]:
                        buffer = buffer[:-1]
                        switch_to_tag(tag)
                        buffer += char
                        break
            elif match_count > max_match_count:
                max_match_count = match_count
            if current_tag == 'normal' and char in ' \n\\\t':
                if matched_space:
                    for tag, start_seq, end_seq, prefix, suffix in _markdown_symbols:
                        if start_seq == buffer[-len(start_seq):]:
                            switch_to_tag(tag)
                            break
                else:
                    result.append((buffer[:-1], 'normal'))
                    buffer = char[:]
        else:
            for tag, start_seq, end_seq, prefix, suffix in _markdown_symbols:
                if tag == current_tag and end_seq == buffer[-len(end_seq):]:
                    result.append((buffer[:-len(end_seq)], current_tag))
                    buffer = suffix
                    current_tag = 'normal'
                    break
    if len(buffer) > 0:
        result.append((buffer, current_tag))
    
    # delete the extra newline at the beginning
    if len(result) > 0:
        if result[0][0][0] == '\n':
            result[0] = (result[0][0][1:], result[0][1])
    
    # remove empty tokens
    result = list(filter(lambda token: len(token[0]) > 0, result))
    return result
