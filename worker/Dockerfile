FROM jamiebull1/eppy:8.4_0.5.1

ADD . /worker
WORKDIR /worker

# Start the worker
ENTRYPOINT [ "python", "src/worker.py" ]
