git clone git@github.com:cjlin1/liblinear.git
cd liblinear
make
mv train ../${1:-.venv/lasso}/bin
cd ..
rm -rf liblinear
