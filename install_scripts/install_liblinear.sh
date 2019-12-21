git clone git@github.com:cjlin1/liblinear.git benchopt_liblinear
cd benchopt_liblinear
make
mv train ../${1:-.venv/lasso}/bin
cd ..
rm -rf benchopt_liblinear
