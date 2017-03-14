#!/bin/sh

### YA GOTTA HAVE PYTHON 3 INSTALLED ###
export FLASK_DEBUG=1

# do cleanup on exit
#cleanup()
#{
#    unset FLASK_DEBUG
#}
#
#trap cleanup EXIT

python3 --version
echo "===STARTING LEGIS==="
python3 legis_data/tastydata.py &
echo "===STARTED DATA SERVICE==="
python3 legis_view/legis.py &
echo "===STARTED VIEW==="
wait