from app.services.markdown import render_markdown


def test_script_tags_stripped() -> None:
    html = render_markdown("<script>alert(1)</script>Bonjour")
    assert "<script>" not in html.lower()


def test_markdown_bold_kept() -> None:
    html = render_markdown("Salut **toi**")
    assert "toi" in html
    assert "<strong>" in html or "<b>" in html
