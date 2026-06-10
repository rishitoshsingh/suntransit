#!/bin/bash

docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
