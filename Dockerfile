FROM python:3.6-slim-buster
RUN apt update && apt install -y git
RUN pip install poetry
RUN git config --global user.name "Martlet"
RUN git config --global user.email "idoneam.collective@gmail.com" 
COPY pyproject.toml /mnt/
COPY poetry.lock /mnt/
RUN cd /mnt && poetry export -f requirements.txt > requirements.txt
RUN pip3 install -r /mnt/requirements.txt
WORKDIR /mnt/canary

CMD  python Main.py
