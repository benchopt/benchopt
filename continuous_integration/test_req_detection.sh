set -e

BENCHOPT_DIR=$(pwd)
SITE_PACKAGES=$(python -c "import sysconfig; print(sysconfig.get_path('purelib'))")

# Create a script to test requirements
echo 'from benchopt.utils.misc import get_benchopt_requirement;print(f"\"{get_benchopt_requirement()[0]}\"")' > get_requirement.py
CHECK_CMD="python -I $BENCHOPT_DIR/get_requirement.py"


#################################################################
# Check local install
pip install .
pip uninstall benchopt -y
echo "$($CHECK_CMD)"
test "$($CHECK_CMD)" = "\"-e $BENCHOPT_DIR\"" && echo 'OK pwd file'

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Change working directory, to avoid local package interferences
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
test -d test_req || mkdir test_req
cd test_req

#################################################################
# Check local install not editable
pip install ..
echo "$($CHECK_CMD)"
test "$($CHECK_CMD)" = "\"benchopt @ file://$BENCHOPT_DIR\"" && echo 'OK local install'

#################################################################
# Check local install not editable
pip install -e ..
echo "$($CHECK_CMD)"
test "$($CHECK_CMD)" = "\"-e $BENCHOPT_DIR\"" && echo 'OK editable'

#################################################################
# Check install from pypi

pip uninstall -y benchopt
pip install benchopt==1.2.0
# Test only the latest script
cp ../benchopt/utils/misc.py $SITE_PACKAGES/benchopt/utils/
echo "$($CHECK_CMD)"
test "$($CHECK_CMD)" = "\"benchopt==1.2.0\"" && echo 'OK pypi'

#################################################################
# Check install from github

pip uninstall -y benchopt
pip install git+https://github.com/benchopt/benchopt@main
# Test only the latest script
cp ../benchopt/utils/misc.py $SITE_PACKAGES/benchopt/utils/
echo "$($CHECK_CMD)"
if [[ "$($CHECK_CMD)" == "\"benchopt @ git+https://github.com/benchopt/benchopt@"* ]]
then
    echo 'OK github'
else
    false # Fails the test
fi