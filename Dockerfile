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

# Install requirements with pip to use Docker cache independent of project metadata
COPY requirements.txt /
RUN pip install -r /requirements.txt

# Copy code to the `canary` directory in the image and run the bot from there
COPY . /canary
WORKDIR /canary

# Notes:
#   Users will have to mount their config.ini in by hand
#   Users should mount a read/writable volume for /canary/data/runtime

CMD ["python3.10", "-m", "canary.main"]
