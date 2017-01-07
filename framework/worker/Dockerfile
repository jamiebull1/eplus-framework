FROM jamiebull1/geomeppy:latest

ADD . /worker
WORKDIR /worker

# Start the worker
ENTRYPOINT [ "python", "src/worker.py" ]
