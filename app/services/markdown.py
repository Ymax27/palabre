import nh3
from markdown_it import MarkdownIt

_md = MarkdownIt("commonmark", {"html": False})


def render_markdown(source: str) -> str:
    html = _md.render(source)
    return nh3.clean(html)


def sanitize_headline(html: str) -> str:
    return nh3.clean(html, tags={"mark", "b", "em", "strong"})
