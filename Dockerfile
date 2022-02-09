# syntax=docker/dockerfile:1.3
FROM ubuntu:latest
EXPOSE 8501
WORKDIR /app
RUN mkdir /usr/src/app
COPY requirements.txt /usr/src/app/
RUN apt-get update                                      && \
    apt-get install software-properties-common -y       && \ 
    apt-add-repository ppa:ubuntugis/ubuntugis-unstable && \
    apt-get update && \
    apt-get install git curl python3 python3-pip gdal-bin libgdal-dev -y && \ 
    python3 -m pip install --upgrade pip                 && \
    python3 -m pip install GDAL==3.4.1                   && \  
    python3 -m pip install -r /usr/src/app/requirements.txt                       
COPY . /usr/src/app
RUN python3 -m pip install -e /usr/src/app
WORKDIR /usr/src/app
ENV PYTHONPATH "/usr/src/app:${PYTHONPATH}"
CMD ["dlsc", "--gui"]
