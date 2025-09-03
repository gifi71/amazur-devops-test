#!/bin/sh
: "${POSTGRES_USER:=postgres}"
pg_isready -U "$POSTGRES_USER"
