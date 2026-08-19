from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_app_renders_initial_state():
    app_path = (
        Path(__file__).resolve().parents[1]
        / "streamlit_app.py"
    )

    app = AppTest.from_file(
        app_path
    ).run(timeout=30)

    assert not app.exception
    assert app.title[0].value == "ProjectPulse AI"
    assert len(app.chat_input) == 1
    assert len(app.slider) == 1
