FROM python:3.12-alpine

WORKDIR /app

# 安裝 uv
RUN pip install uv --no-cache-dir

# 複製依賴設定
COPY pyproject.toml uv.lock ./

# 安裝依賴（不安裝開發工具，只裝 production 套件）
RUN uv sync --frozen --no-dev

# 複製應用程式碼
COPY main.py .

EXPOSE 8000

CMD ["uv", "run", "fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]
