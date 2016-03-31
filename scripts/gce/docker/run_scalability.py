#!/usr/bin/python

import argparse
import os
import random
import subprocess
import sys

SRC_HOST = "diamond-client-a1o6"
WORKING_DIR = "~/"

COPY_CMD = "rsync " + SRC_HOST + ":diamond-src/"
CONFIG_DIR = "platform/test/"
CONFIG_PREFIX = "gce.frontend"
KEY_DIR = "scripts/experiments/"
KEY_FILE = "keys.txt"
NUM_KEYS = "1000"
NUM_SECONDS = "120"
OUTPUT_DEST = "scripts/experiments/scalability/"
NUM_CLIENTS = 10
NUM_FRONTENDS = 10

os.system(COPY_CMD + "apps/benchmarks/build/scalability" + " " + WORKING_DIR)
os.system(COPY_CMD + "platform/build/libdiamond.so" + " " + WORKING_DIR)

# Copy config files
for i in range(0, NUM_FRONTENDS):
    configFile = CONFIG_PREFIX + repr(i)
    os.system(COPY_CMD + CONFIG_DIR + configFile + ".config" + " " + WORKING_DIR)
os.system(COPY_CMD + KEY_DIR + KEY_FILE + " " + WORKING_DIR)

# Run binary
processes = []
outputFiles = []
for i in range(0, NUM_CLIENTS):
    outputFile = "scalability-out-" + repr(random.randint(0, sys.maxint))
    configFile = CONFIG_PREFIX + repr(i % NUM_FRONTENDS)
    cmd = WORKING_DIR + "/scalability --config " + WORKING_DIR + configFile + " --keys " + WORKING_DIR + KEY_FILE + " --numkeys " + NUM_KEYS + " --time " + NUM_SECONDS + " > " + WORKING_DIR + outputFile
    processes.append(subprocess.Popen(cmd, shell=True))
    outputFiles.append(outputFile)

for process in processes:
    process.wait()

# Copy output back to client
for outputFile in outputFiles:
    os.system("rsync " + WORKING_DIR + outputFile + " " + SRC_HOST + ":diamond-src/" + OUTPUT_DEST)
