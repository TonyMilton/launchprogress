FROM python:3.13-slim

RUN pip install uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY launchprogress/ launchprogress/
COPY timer.py ./

EXPOSE 8000

CMD ["uv", "run", "timer.py", "--serve"]
