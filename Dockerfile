FROM ubuntu:22.04

RUN apt update && \
    apt install -yq tzdata && \
    ln -fs /usr/share/zoneinfo/Europe/Moscow /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata && \
    apt install python3 -y && \
    apt install python3-pip -y && \
    apt install r-base -y && \
    rm -rf /var/lib/apt/lists/*

WORKDIR app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
COPY . .

CMD python3 manage.py runserver