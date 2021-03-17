# Make sure R_HOME is never passed down to subprocesses
# as it might lead to trying to load packages from the
# wrong distribution.
unset R_HOME
