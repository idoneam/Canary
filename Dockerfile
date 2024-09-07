FROM python:3.11-slim-bookworm

# Install base apt dependencies + auxiliary dependencies (for GL, Tex, etc.)
RUN apt-get update && \
    apt-get install -y  \
      git \
      sqlite3 \
      libgl1-mesa-glx \
      texlive-latex-extra \
      texlive-fonts-extra \
      texlive-lang-greek \
      dvipng \
      ffmpeg \
      gcc && \
    rm -rf /var/lib/apt/lists/*

# Update pip, install poetry
RUN pip install --no-cache-dir -U pip; \
    pip install --no-cache-dir poetry==1.8.3

WORKDIR /app

COPY LICENSE.txt .
COPY pyproject.toml .
COPY poetry.lock .

# Install dependencies (minus package) to cache this layer
RUN poetry config virtualenvs.create false && \
    poetry --no-cache install --no-root --without dev

# Copy code and pre-made data to the /app directory, where the bot will be run from
COPY canary canary
COPY data data

# Install the package locally
RUN poetry install --without dev

# Notes:
#   Users will have to configure their instance using environment variables, described by the Pydantic settings object
#     in /app/canary/config/config.py
#   Users should mount a read/writable volume for /app/data/runtime

CMD ["poetry", "run", "canary"]
