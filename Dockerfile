FROM python:3.6-slim-buster

# Install base apt dependencies
RUN apt-get update && apt-get install -y git

# Install auxiliary dependencies (for GL, Tex, etc.)
RUN apt-get install -y \
  libgl1-mesa-glx \
  texlive-latex-extra \
  texlive-lang-greek \
  dvipng

# Install Poetry (Python dependency manager)
RUN pip install poetry

# Trying to fix Travis CI issues
RUN pip freeze > requirements1.txt
RUN pip install pytest aiohttp beautifulsoup4 discord.py feedparser iniconfig mpmath numpy opencv_python pluggy py
RUN pip freeze > requirements2.txt
RUN diff requirements.txt requirements1.txt
RUN diff requirements1.txt requirements2.txt

# Configure Git settings for update command
RUN git config --global user.name "Martlet"
RUN git config --global user.email "idoneam.collective@gmail.com"

# Install requirements with pip to use Docker cache independent of project metadata
COPY requirements.txt /mnt/
RUN pip install -r /mnt/requirements.txt

WORKDIR /mnt/canary
CMD ["python", "Main.py"]
