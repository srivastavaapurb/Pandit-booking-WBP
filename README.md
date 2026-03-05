---
title: Puja Booking Assistant (WB, 100 Pandits)
colorFrom: yellow
colorTo: red
sdk: gradio
app_file: app.py
pinned: false
license: mit
---

Supports **Text & Voice**, auto **Puja Samagri** and **Puja Instructions** sections.

### Deploy
1. Create a Hugging Face Space (SDK = Gradio).
2. Upload `app.py`, `requirements.txt`, and `runtime.txt` (optional).
3. In **Settings → Variables and secrets**, add:
   - `OPENAI_API_KEY` = your rotated OpenAI key (do **not** hardcode).

### How it ranks
Specialization → Proximity (tiers & distance) → Time-window match → Weekday availability → Budget gap → Ratings → Experience → Fee (asc).

The link is publicly deployed at https://huggingface.co/spaces/AS2004/puja_book_new
