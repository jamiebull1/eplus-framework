FROM nrel/energyplus:8.4

ENV ENERGYPLUS_VERSION=8.4.0

RUN apt-get update && apt-get install -y \
  python-dev \
  python-pip \
  python-numpy \
  git \
  && pip install esoreader

# Currently we need to use a custom build of eppy since the master branch is
# not working properly with reading an IDF in from a file path.
RUN pip install git+https://github.com/jamiebull1/eppy.git@develop