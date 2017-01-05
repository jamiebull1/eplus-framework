# EnergyPlus Docker Queue Server

This project simply manages a queue to distribute jobs from a jobs creator to 
worker instances and another queue to receive results to pass back to a job 
creator instance.

## Example

```
docker run -d -p 50000:50000 eplus-queue-server
```
