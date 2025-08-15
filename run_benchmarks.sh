#!/usr/bin/env bash

usage="Usage: $0 -t NUMBER (NUMBER must be bigger than 0) {scenario1|scenario2|scenario2-subset}"

# Default thread number is 1
threads=1

# Parse flags
while getopts "t:" opt; do
    case "$opt" in
        t) threads="$OPTARG" ;;
        *)
            echo $usage
            exit 1
            ;;
    esac
done

# Shift so that positional arguments are in $1, $2, ...
shift $((OPTIND - 1))

# Check if threads variable is set
if [[ -z "$threads" ]]; then
    echo "Error: You must provide a number with -t"
    echo $usage
    exit 1
fi

# Validate that threads is an integer >= 1
if ! [[ "$threads" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: Number of threads must be 1 or larger"
    exit 1
fi

# Ensure exactly one argument is passed
if [[ $# -ne 1 ]]; then
    echo $usage
    exit 1
fi

scenario="$1"

echo "Using $threads threads."

# Validate and act based on the argument
case "$scenario" in
    scenario1)
        inputDir=./benchmarks/scenario1
        expectedRuns=244
        echo "Benchmarking using scenario 1..."
        ;;
    scenario2)
        inputDir=./benchmarks/scenario2
        expectedRuns=10
        echo "Benchmarking using scenario 2..."
        ;;
    scenario2-subset)
        inputDir=./benchmarks/scenario2-subset
        expectedRuns=8
        echo "Benchmarking using scenario 2, excluding networks with diameter 9 and 10..."
        ;;
    *)
        echo "Error: Invalid scenario '$scenario'"
        echo "Valid options are: scenario1, scenario2, scenario2-subset"
        exit 1
        ;;
esac

logDir=./output_log
mkdir $logDir
fileNo=$(find $inputDir -type f | wc -l)
filesProcessed=0

for file in $inputDir/*
do
  let "filesProcessed+=1"
  echo "Progress: $filesProcessed/$fileNo"
  fileName=${file##*/}
  fileNameNoExt=${fileName%.*}
  outputFile=$"log_$fileNameNoExt.txt"
  python3 main.py -d 10 -t $threads -s pbfs -v $file ./benchmarks/properties.json >$logDir/$outputFile 2>&1
done

# Finally, verify that we have results for all files
runs=$(cat ./output/final_stats.csv | wc -l)
if [[ $runs -ne $expectedRuns ]]; then
  echo "Unsuccessful benchmark!"
  echo "The 'final_stats.csv' file does not contain the expected number of lines! Perhaps the output folder was not removed before running the benchmark?"
  exit 1
fi

echo "Benchmark finished successfully!"
echo "Ploting the results in ./output/${scenario}-plots"

mkdir ./output/${scenario}-plots
cd ./benchmarks/ploting
python3 main.py --scenario-type $scenario ../../output/final_stats.csv ../../output/${scenario}-plots
echo "Done"
