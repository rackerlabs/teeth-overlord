# Teeth Overlord

Teeth Overlord is the centralized control system for Teeth. It exposes REST
APIs for inventory and instance management, as well as a line-oriented JSON
protocol used to communicate with agents which run on servers which are in a
ready state, waiting to be deployed by a customer.

## Dependencies

The Teeth Overlord services depend on a Cassandra instance. By default, they
connect to localhost:9160.

Once Cassandra is running, sync our schema to it:

```bash

python sync_models.py
```

## teeth-agent-endpoint

Exposes an endpoint that teeth agents can connect to in order to make and
receive commands.

### Running the Service

```bash
twistd --pidfile agent-endpoint.pid --logfile agent-endpoint.log teeth-agent-endpoint
```

The agent-endpoint exposes an internal REST API, which other Teeth services can
use to communicate with agents. Agents which connect to the agent-endpoint
create an AgentConnection record which otehr services can use to locate agents.
AgentConnection records are uniquely identified by the primary MAC address of
the agent.


## teeth-public-api

Exposes REST APIs for inventory and instance management.

### Running the Service

```bash
twistd --pidfile public-api.pid --logfile public-api.log teeth-public-api
```

### REST API

```bash
# Create a Chassis
curl http://localhost:8080/v1.0/chassis -X POST

# List Chassis
curl http://localhost:8080/v1.0/chassis
[
    {
        "id": "7c52d47c-1313-4fdc-a680-ffb4bde3674e",
        "state": "READY",
        "primary_mac_address": "a:b:c:d"
    }
]

# Now the Chassis is in the READY state. To allocate, it, start the teeth-agent
# (currently we just hardcode the primary MAC address reported by the agent, so
# you can just run the agent anywhere), then run:
curl http://localhost:8080/v1.0/instances -X POST

# Now list instances
curl http://localhost:8080/v1.0/instances
[
    {
        "id": "6b3cac55-b077-495c-a3c6-8eb80650f281",
        "chassis_id": "7c52d47c-1313-4fdc-a680-ffb4bde3674e",
        "state": "ACTIVE"
    }
]

# Our instance has been created and is active. The chassis should also be shown
# as active:
curl http://localhost:8080/v1.0/chassis
[
    {
        "id": "7c52d47c-1313-4fdc-a680-ffb4bde3674e",
        "state": "ACTIVE",
        "primary_mac_address": "a:b:c:d"
    }
]


# The agent will have logged:

# 2013-09-20 10:54:45-0700 [AgentClientHandler,client] Preparing image image-123

# Because during instance creation we commanded the agent to prepare an image.
# We can easily add support for new RPC methods to the agent as necessary to
# support inventory management and instance creation.
```
