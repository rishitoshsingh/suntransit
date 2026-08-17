#!/bin/bash
# Downloads static GTFS files from S3 to ./data/static_gtfs/ so Spark jobs
# read them locally instead of hitting S3 on every hourly run.
# Run once to bootstrap, then weekly via cron to pick up GTFS schedule updates.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCAL_DIR="$SCRIPT_DIR/data/static_gtfs"
VENV="/tmp/gtfs-sync-venv"

source "$SCRIPT_DIR/credentials.env"

echo "[$(date)] Syncing static GTFS from S3 to $LOCAL_DIR ..."

# Bootstrap venv if needed
if [ ! -f "$VENV/bin/python3" ]; then
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install boto3 -q
fi

AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
"$VENV/bin/python3" << PYEOF
import boto3, os, pathlib

s3 = boto3.client('s3',
    aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
    region_name='us-east-2',
)

LOCAL_BASE = pathlib.Path('$LOCAL_DIR')
paginator = s3.get_paginator('list_objects_v2')

for page in paginator.paginate(Bucket='suntransit', Prefix='static_gtfs/'):
    for obj in page.get('Contents', []):
        key = obj['Key']
        if key.endswith('/'):
            continue
        rel = '/'.join(key.split('/')[1:])
        local_path = LOCAL_BASE / rel
        local_path.parent.mkdir(parents=True, exist_ok=True)
        size_mb = obj['Size'] / 1024 / 1024
        print(f'  {rel} ({size_mb:.1f} MB)')
        s3.download_file('suntransit', key, str(local_path))

print('[done] static GTFS sync complete.')
PYEOF

echo "[$(date)] Sync complete."
