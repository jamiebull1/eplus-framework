# EnergyPlus Docker Worker

This project is based around the latest Dockerfile for EnergyPlus and Eppy.

There are stubs in `src/worker.py` to be completed in order to build, run,
and post-process EnergyPlus jobs. Jobs and results queues are handled by an 
instance of EnergyPlus Docker Server.

## Example

```
docker run -d eplus-worker <host ip-address>
```
