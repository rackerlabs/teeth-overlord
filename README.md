# Teeth Overlord

Teeth Overlord is the centralized control system for Teeth. It exposes REST
APIs for inventory and instance management, as well as a line-oriented JSON
protocol used to communicate with agents which run on servers which are in a
ready state, waiting to be deployed by a customer.

## Dependencies

### Cassandra 2.0

By default, Overlord connects to localhost:9160.

### Marconi

By default, Overlord connects to http://localhost:8888.

To run Marconi locally:

```bash
git clone git@github.com:openstack/marconi.git
cd marconi
virtualenv --no-site-packages .
. bin/activate
pip install -e .
marconi-server
```

## Preparing a Dev Environment

With Cassandra and Marconi running, run the following from the root of the
`teeth-overlord` repository:

```bash
# Create a Dev Environment
tox -e devenv

# Activate the Dev Environment
. devenv/bin/activate

# Synchronize Schema
teeth-sync-models
```

Now start `teeth-public-api` and `teeth-job-executor`. To load development
fixtures, run `teeth-prepare-dev-environment`.

## Builders

Teeth Overlord master: https://jenkins.t.k1k.me/job/teeth-overlord-master/
Teeth Overlord PRs: https://jenkins.t.k1k.me/job/teeth-overlord-pr/
hi
hi
