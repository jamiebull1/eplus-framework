FROM jamiebull1/eppy:8.4_develop

ADD . /worker
WORKDIR /worker

# Start the worker
ENTRYPOINT [ "python", "src/worker.py" ]
