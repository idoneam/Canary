FROM python:3.10-slim-bullseye

# Install base apt dependencies
RUN apt-get update && apt-get install -y git sqlite3

# Install auxiliary dependencies (for GL, Tex, etc.)
RUN apt-get install -y \
  libgl1-mesa-glx \
  texlive-latex-extra \
  texlive-fonts-extra \
  texlive-lang-greek \
  dvipng \
  ffmpeg \
  gcc

WORKDIR /canary

# Install poetry
RUN pip install poetry==1.2.2

# Copy over files which specify dependencies first, to improve Docker caching
COPY pyproject.toml pyproject.toml
COPY poetry.lock poetry.lock
COPY poetry.toml poetry.toml

# Install dependencies without installing canary module
RUN poetry install --no-root

# Copy code to the `canary` directory in the image and run the bot from there
COPY . .

# Install canary module
RUN poetry install

# Notes:
#   Users will have to mount their config.ini in by hand
#   Users should mount a read/writable volume for /canary/data/runtime

CMD ["python3.10", "-m", "canary.main"]
