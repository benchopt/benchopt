set -e

BENCHOPT_DIR=$(pwd)
SITE_PACKAGES=$(python -c "import sysconfig; print(sysconfig.get_path('purelib'))")

# Create a script to test requirements
echo 'from benchopt.utils.misc import get_benchopt_requirement;print(f"\"{get_benchopt_requirement()[0]}\"")' > get_requirement.py
echo 'from benchopt.utils.misc import get_benchopt_requirement;print(get_benchopt_requirement(True)[0]);assert "benchopt[test]" in get_benchopt_requirement(True)[0]' > get_requirement_test.py
CHECK_CMD="python -I $BENCHOPT_DIR/get_requirement.py"
CHECK_TEST_CMD="python -I $BENCHOPT_DIR/get_requirement_test.py"


#################################################################
# Check local install
pip install . > /dev/null
echo "$($CHECK_CMD)"
test "$($CHECK_CMD)" = "\"-e $BENCHOPT_DIR\"" && echo 'OK pwd file'

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Change working directory, to avoid local package interferences
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
test -d test_req || mkdir test_req
cd test_req

#################################################################
# Check local install not editable
pip uninstall -y benchopt > /dev/null
pip install .. > /dev/null
echo "$($CHECK_CMD)"
test "$($CHECK_CMD)" = "\"benchopt @ file://$BENCHOPT_DIR\""
# Check that the get_benchopt_requirement(True) gives a valid requirement
echo "Test requirement: \"$($CHECK_TEST_CMD)\""
pip install "$($CHECK_TEST_CMD)" > /dev/null
echo 'OK local install'

#################################################################
# Check editable local install
pip uninstall -y benchopt > /dev/null
pip install -e .. > /dev/null
echo "$($CHECK_CMD)"
test "$($CHECK_CMD)" = "\"-e $BENCHOPT_DIR\""
# Check that the get_benchopt_requirement(True) gives a valid requirement
echo "Test requirement: \"$($CHECK_TEST_CMD)\""
pip install $($CHECK_TEST_CMD) > /dev/null
echo 'OK editable'

#################################################################
# Check install from pypi

pip uninstall -y benchopt > /dev/null
pip install benchopt==1.8.0 > /dev/null
# Test only the latest script
cp ../benchopt/utils/misc.py $SITE_PACKAGES/benchopt/utils/
echo "$($CHECK_CMD)"
test "$($CHECK_CMD)" = "\"benchopt==1.8.0\""
# Check that the get_benchopt_requirement(True) gives a valid requirement
echo "Test requirement: \"$($CHECK_TEST_CMD)\""
pip install "$($CHECK_TEST_CMD)" > /dev/null
echo 'OK pypi'

#################################################################
# Check install from github

pip uninstall -y benchopt > /dev/null
pip install git+https://github.com/benchopt/benchopt@main > /dev/null
# Test only the latest script
cp ../benchopt/utils/misc.py $SITE_PACKAGES/benchopt/utils/
echo "$($CHECK_CMD)"
if [[ "$($CHECK_CMD)" != "\"benchopt @ git+https://github.com/benchopt/benchopt@"* ]]
then
    false # Fails the test
fi
# Check that the get_benchopt_requirement(True) gives a valid requirement
echo "Test requirement: \"$($CHECK_TEST_CMD)\""
pip install "$($CHECK_TEST_CMD)" > /dev/null
echo 'OK github'
