#!/bin/bash

source /nrgpackages/scripts/groovy_setup.sh
#source /data/hcpdb/ftp/staging.mdh/OpenAccess/packaging-scripts/PackageQ2/PackageQ2_vars.sh
SCRIPTDIR="$( cd "$( dirname "$0" )" && pwd )"
PackagerHome=$SCRIPTDIR/download-packager
ResourcePath=$PackagerHome/resources
CLASSPATH=$PackagerHome:$PackagerHome/src/main/resources:$PackagerHome/src/main/groovy:$PackagerHome/target/dependency/fast-md5-2.7.1.jar:$PackagerHome/target/dependency/commons-cli-1.2.jar:$PackagerHome/target/dependency/hamcrest-core-1.1.jar:$CLASSPATH

if [ $# -lt 1 ]; then
    echo "$0 <verification target>"
    echo "A target folder must be specified"
    exit 1
fi
VerificationTarget=$1

groovy -cp $CLASSPATH $PackagerHome/package-verifier.groovy -d $VerificationTarget

