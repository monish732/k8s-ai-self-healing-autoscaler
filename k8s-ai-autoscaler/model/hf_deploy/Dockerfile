FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir \
fastapi uvicorn torch numpy scikit-learn pandas \
kubernetes huggingface_hub requests

CMD ["uvicorn","predictor:app","--host","0.0.0.0","--port","8000"]
