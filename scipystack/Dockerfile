FROM ubuntu:14.04

# Force bash
RUN rm /bin/sh && ln -s /bin/bash /bin/sh

# Install required packages
# System packages 
RUN apt-get update && apt-get install -y \
    curl \
    python-pip

# Install miniconda to /miniconda
RUN curl -LO http://repo.continuum.io/miniconda/Miniconda-latest-Linux-x86_64.sh
RUN bash Miniconda-latest-Linux-x86_64.sh -p /miniconda -b
RUN rm Miniconda-latest-Linux-x86_64.sh
ENV PATH=/miniconda/bin:${PATH}
RUN conda update -y conda && conda create -n myenv python
RUN source activate myenv

# Python packages from conda
RUN conda install -y \
    numpy \
    scipy \
    matplotlib

# SALib from pip
RUN pip install SALib==0.7.1
