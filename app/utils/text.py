import html


def esc(value) -> str:
    """HTML-escape a value for safe interpolation into a parse_mode=HTML
    Telegram message.

    Now that the bot sends everything with parse_mode=HTML (see main.py's
    Defaults(parse_mode=ParseMode.HTML)) - needed for the <b>bold</b>/
    <i>italic</i> formatting on the screens - any dynamic text has to be
    escaped before going into a message, or Telegram's API rejects the
    whole send with "Can't parse entities" the moment it contains a
    stray '&', '<', or '>'. This bites in two very real, very common
    places: booking URLs (query strings are full of '&') and free-typed
    user input echoed back in an error message (e.g. an unrecognized
    airport code). Wrap any non-literal string in this before it goes
    into a message; it's a no-op on plain text so it's safe to apply
    everywhere, not just where it's strictly needed.
    """

    return html.escape(str(value))
