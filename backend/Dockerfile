FROM python:3.10

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.hf-cache \
    PIP_DEFAULT_TIMEOUT=300

WORKDIR /app/backend/web_system

COPY backend/requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && grep -vE '^(torch|torchvision|torchaudio)==' /tmp/requirements.txt > /tmp/requirements-no-torch.txt \
    && python -m pip install --no-cache-dir --retries 20 \
       -i https://pypi.tuna.tsinghua.edu.cn/simple \
       --trusted-host pypi.tuna.tsinghua.edu.cn \
       -r /tmp/requirements-no-torch.txt \
    && python -m pip install --no-cache-dir --retries 20 \
       --index-url https://download.pytorch.org/whl/cpu \
       torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0

COPY backend /app/backend
RUN mkdir -p /app/data/uploads /app/data/processed /app/.hf-cache

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
