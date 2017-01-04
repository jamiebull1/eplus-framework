FROM nrel/energyplus:latest

ENV ENERGYPLUS_VERSION=8.5.0

RUN apt-get update && apt-get install -y \
  python-dev \
  python-pip \
  python-shapely  \
  python-numpy \
  pkg-config \
  libfreetype6-dev \
  libpng-dev \
  git \
  && pip install -U setuptools \
  && pip install \
  python-dateutil \
  sqlalchemy \
  pandas
# Currently we use geomeppy which allows us to build geometry and run models.
RUN pip install geomeppy