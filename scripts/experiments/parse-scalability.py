#!/usr/bin/python

import argparse
import os
import re
import sys

parser = argparse.ArgumentParser(description='Parse scalability client results.')
parser.add_argument('directory', help='the directory containing the output files')
args = parser.parse_args()

resultDir = args.directory
files = os.listdir(resultDir)

allStartTimes = []
allEndTimes = []
allResults = []

for filename in files:
    f = open(resultDir + "/" + filename, 'r')
    for line in f:
        match = re.match("^(\d+)\s+(\d+)\s+(\d)$", line)
        if match:
            startTime = int(match.group(1))
            endTime = int(match.group(2))
            committed = int(match.group(3))

            allStartTimes.append(startTime)
            allEndTimes.append(endTime)
            allResults.append(committed)

if len(files) == 0:
    print("No files to parse!")
    sys.exit()

print("Results span " + repr((max(allEndTimes) - min(allStartTimes)) / 1000) + " seconds");

timeLowerBound = min(allStartTimes) + (max(allEndTimes) - min(allStartTimes)) * (25.0 / 100.0)
timeUpperBound = min(allStartTimes) + (max(allEndTimes) - min(allStartTimes)) * (75.0 / 100.0)

startTimes = []
endTimes = []
results = []

for i in range(0, len(allStartTimes)):
    if allStartTimes[i] >= timeLowerBound and allEndTimes[i] <= timeUpperBound:
        startTimes.append(allStartTimes[i])
        endTimes.append(allEndTimes[i])
        results.append(allResults[i])

print("Selected " + repr(len(results)) + " of " + repr(len(allResults)) + " transactions")

numTxns = 0
numAborts = 0
sumTimes = 0
for i in range(0, len(startTimes)):
    numTxns += 1
    if results[i] == 1:
        sumTimes += (endTimes[i] - startTimes[i])
    else:
        numAborts += 1

numSuccessful = numTxns - numAborts
meanTime = float(sumTimes) / numSuccessful / 1000
abortRate = float(numAborts) / numTxns

print("Num transactions: " + repr(numTxns) + ", num aborts: " + repr(numAborts));
print("Avg. time (s): " + repr(meanTime))
print("Abort rate: " + repr(abortRate))