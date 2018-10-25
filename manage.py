#!/usr/bin/env python
import coverage
import signal
import sys

# Copyright (c) 2015 Ansible, Inc.
# All Rights Reserved.

cov = coverage.Coverage()
cov.start()
def stop_coverage(*args):
    cov.stop()
    cov.save()
    print("Saved Coverage Data")
    sys.exit()

# on sigterm, call "stop_coverage"
signal.signal(signal.SIGTERM, stop_coverage)

if __name__ == '__main__':
    from awx import manage
    try:
        manage()
    finally:
        stop_coverage()
