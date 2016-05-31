FROM jamiebull1/eppy:eplus8.4_eppy_DEV

ADD . /worker
WORKDIR /worker

# Start the worker
ENTRYPOINT [ "python", "src/worker.py" ]
