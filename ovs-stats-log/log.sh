#!/bin/bash

set -ex
FILENAME=`date +%Y%m%d%H%M`.log
DIR="/home/wide/camp17-docker-nfv/ovs-stats-log"

ovs-ofctl dump-flows vswitch0     > ${DIR}/dump-flows/${FILENAME}
ovs-ofctl dump-ports vswitch0     > ${DIR}/dump-ports/${FILENAME}
ovs-ofctl dump-aggregate vswitch0 > ${DIR}/dump-aggregate/${FILENAME}
sh -c "vmstat | tail -1"          > ${DIR}/vmstat/${FILENAME}
