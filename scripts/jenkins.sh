#!/bin/bash
#
# One stop script for running tests in jenkins. 
#

make env
. .ve/bin/activate
make unit
