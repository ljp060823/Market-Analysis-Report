FROM python:3.12-slim

WORKDIR /app

# RUN pip install --no-cache-dir gradio httpx

COPY frontend/gradio_app.py /app/gradio_app.py

CMD ["python", "gradio_app.py"]
