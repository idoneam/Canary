FROM python:3.9-slim-buster

# Add testing to get newer SQLite (ugh)
RUN echo 'deb http://http.us.debian.org/debian/ testing non-free contrib main' >> /etc/apt/sources.list

# Install base apt dependencies
RUN apt-get update && apt-get install -y git

# Install auxiliary dependencies (for GL, Tex, etc.)
RUN apt-get install -y \
  libgl1-mesa-glx \
  texlive-latex-extra \
  texlive-lang-greek \
  dvipng \
  gcc

# Configure Git settings for update command
RUN git config --global user.name "Martlet"
RUN git config --global user.email "idoneam.collective@gmail.com"

# Install requirements with pip to use Docker cache independent of project metadata
COPY requirements.txt /mnt/
RUN pip install -r /mnt/requirements.txt

WORKDIR /mnt/canary
CMD ["python3.9", "Main.py"]
