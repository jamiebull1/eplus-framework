# EnergyPlus Docker Client

The purpose of the Client module is to create jobs, pass them to a jobs queue,
and handle the results as they are returned.

Configuration happens in the client.cfg file.

Current job type is sensitivity analysis.

## Example

```
docker run -d eplus-client
```
