FROM jamiebull1/eppy:eplus8.5_eppy_DEV

ADD . /worker
WORKDIR /worker

# Start the worker
ENTRYPOINT [ "python", "src/worker.py" ]
