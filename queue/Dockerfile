FROM elyase/conda:2.7

ADD . /queue
WORKDIR /queue

# Force bash
RUN opkg-install bash
RUN rm /bin/sh && ln -s /bin/bash /bin/sh

# Set up and activate conda env and install required packages
RUN conda update --all && conda create -n queue python
RUN source activate queue && \
	pip install -r ./requirements.txt

EXPOSE 50000

CMD [ "python", "src/queue.py" ]
