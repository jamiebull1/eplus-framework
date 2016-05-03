FROM nrel/energyplus:8.4

ENV ENERGYPLUS_VERSION=8.4.0
ADD . /eplusworker
WORKDIR /eplusworker

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

# Start the worker
ENTRYPOINT [ "python", "src/worker.py" ]
