FROM python:3.12-slim
WORKDIR /app
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
COPY langgraph-agent/ /app/
COPY shared/ /app/shared/
RUN pip install --no-cache-dir --default-timeout=1000 .
EXPOSE 8004
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
