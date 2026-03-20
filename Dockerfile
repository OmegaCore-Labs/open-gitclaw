FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv sync --frozen

COPY . .

# Build Tree-sitter languages (python only for now)
RUN mkdir -p build && \
    git clone https://github.com/tree-sitter/tree-sitter-python.git && \
    python -c "from tree_sitter import Language; Language.build_library('build/my-languages.so', ['tree-sitter-python'])" && \
    rm -rf tree-sitter-python

VOLUME /app/data

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
