"""
FounderOS — Gradio frontend entry point.

Run locally:
    python app.py

Deploy:
    - Hugging Face Spaces: this file + requirements.txt is all a Gradio
      Space needs; just push the gradio_app/ contents to the Space repo.
    - Render / Railway: start command `python app.py`; set the
      FOUNDEROS_BACKEND_URL env var if the backend isn't the default.
"""
import os

from ui import build_app

if __name__ == "__main__":
    demo = build_app()
    demo.queue()  # required for the generator-based loading experience
    demo.launch(
        server_name=os.environ.get("HOST", "0.0.0.0"),
        server_port=int(os.environ.get("PORT", 7860)),
    )
