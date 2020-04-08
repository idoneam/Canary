FROM python:3.6-slim-buster

RUN apt update && apt install -y git
RUN pip install poetry

# Configure Git settings for update command
RUN git config --global user.name "Martlet"
RUN git config --global user.email "idoneam.collective@gmail.com" 

# Freeze and install requirements with pip to use Docker cache.
COPY pyproject.toml /mnt/
COPY poetry.lock /mnt/
RUN cd /mnt && poetry export -f requirements.txt > requirements.txt
RUN pip3 install -r /mnt/requirements.txt

WORKDIR /mnt/canary
CMD  python Main.py
