set -e
SRC_DIR=./benchopt_liblinear

git clone https://github.com/cjlin1/liblinear.git $SRC_DIR
cd $SRC_DIR
make
cd ..
mv $SRC_DIR/train ${1:-.}/bin/
rm -rf $SRC_DIR
