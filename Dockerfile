FROM python:3.6-slim-buster

# Install base apt dependencies
RUN apt-get update && apt-get install -y git

# Install auxiliary dependencies (for GL, Tex, etc.)
RUN apt-get install -y \
  libgl1-mesa-glx \
  texlive-latex-extra \
  texlive-lang-greek \
  dvipng

# Install Poetry (Python dependency manager) and YAPF (Google's Python autoformatter)
RUN pip install poetry yapf

# Fix issues with Travis CI
RUN pip freeze > /mnt/requirements.txt

# Configure Git settings for update command
RUN git config --global user.name "Martlet"
RUN git config --global user.email "idoneam.collective@gmail.com"

# Install requirements with pip to use Docker cache independent of project metadata
RUN pip install -r /mnt/requirements.txt

WORKDIR /mnt/canary
CMD ["python", "Main.py"]
