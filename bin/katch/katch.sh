#!/bin/bash

if [[ -n `type -p java` ]]; then
  _java=java
elif [[ -n "$JAVA_HOME" ]] && [[ -x "$JAVA_HOME/bin/java" ]];  then
  _java="$JAVA_HOME/bin/java"
else
  echo "No Java installation found in PATH or JAVA_HOME. Please install Java 8 or higher!"
  exit 1
fi

SCRIPT_PATH=$(dirname $(realpath -s $0))
file=$(realpath -s ${@:2})

cd $SCRIPT_PATH
"$_java" -Xss10m -Xmx128g -jar $SCRIPT_PATH/KATch-assembly-0.1.0-SNAPSHOT.jar $1 $file && rm -rf $SCRIPT_PATH/kat
