FROM python:3.6-slim-buster

RUN apt update && apt install -y git
RUN pip install poetry

# Configure Git settings for update command
RUN git config --global user.name "Martlet"
RUN git config --global user.email "idoneam.collective@gmail.com" 

# Install requirements with pip to use Docker cache independent of project metadata
COPY requirements.txt /mnt/
RUN pip3 install -r /mnt/requirements.txt

WORKDIR /mnt/canary
CMD  python Main.py
