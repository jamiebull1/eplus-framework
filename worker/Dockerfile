FROM ubuntu:14.04

ADD . /eplusworker
WORKDIR /eplusworker

RUN apt-get update && apt-get install -y curl ca-certificates 

# Force bash
RUN rm /bin/sh && ln -s /bin/bash /bin/sh

# Set up and activate conda env and install required packages
# Install miniconda to /miniconda
RUN curl -LO http://repo.continuum.io/miniconda/Miniconda-latest-Linux-x86_64.sh
RUN bash Miniconda-latest-Linux-x86_64.sh -p /miniconda -b
RUN rm Miniconda-latest-Linux-x86_64.sh
ENV PATH=/miniconda/bin:${PATH}
RUN conda update -y conda
RUN conda create -n worker python
RUN source activate worker && \
	pip install -r ./requirements.txt

# This is not ideal. The tarballs are not named nicely and EnergyPlus versioning is strange
ENV ENERGYPLUS_VERSION 8.4.0
ENV ENERGYPLUS_TAG v8.4.0
ENV ENERGYPLUS_SHA 832e4bb9cb

# This should be x.y.z, but EnergyPlus convention is x-y-z
ENV ENERGYPLUS_INSTALL_VERSION 8-4-0

# Downloading from Github
# e.g. https://github.com/NREL/EnergyPlus/releases/download/v8.3.0/EnergyPlus-8.3.0-6d97d074ea-Linux-x86_64.sh
ENV ENERGYPLUS_DOWNLOAD_BASE_URL https://github.com/NREL/EnergyPlus/releases/download/$ENERGYPLUS_TAG
ENV ENERGYPLUS_DOWNLOAD_FILENAME EnergyPlus-$ENERGYPLUS_VERSION-$ENERGYPLUS_SHA-Linux-x86_64.sh
ENV ENERGYPLUS_DOWNLOAD_URL $ENERGYPLUS_DOWNLOAD_BASE_URL/$ENERGYPLUS_DOWNLOAD_FILENAME

# Collapse the update of packages, download and installation into one command
# to make the container smaller & remove a bunch of the auxiliary apps/files
# that are not needed in the container
RUN rm -rf /var/lib/apt/lists/* \
    && curl -SLO $ENERGYPLUS_DOWNLOAD_URL \
    && chmod +x $ENERGYPLUS_DOWNLOAD_FILENAME \
    && echo "y\r" | ./$ENERGYPLUS_DOWNLOAD_FILENAME \
    && rm $ENERGYPLUS_DOWNLOAD_FILENAME \
    && cd /usr/local/EnergyPlus-$ENERGYPLUS_INSTALL_VERSION \
    && rm -rf DataSets Documentation ExampleFiles WeatherData MacroDataSets PostProcess/convertESOMTRpgm \
    PostProcess/EP-Compare PreProcess/FMUParser PreProcess/ParametricPreProcessor PreProcess/IDFVersionUpdater

# Remove the broken symlinks
RUN cd /usr/local/bin \
    && find -L . -type l -delete

# Start the worker
ENTRYPOINT [ "python", "src/worker.py" ]
