FROM elyase/conda:2.7

ADD . /eplusclient
WORKDIR /eplusclient

# Force bash
RUN opkg-install bash
RUN rm /bin/sh && ln -s /bin/bash /bin/sh

# Set up and activate conda env and install required packages
RUN conda update --all && conda create -n client python
RUN source activate client && \
	pip install -r ./requirements.txt

# Start the client
ENTRYPOINT [ "python", "src/client.py" ]
