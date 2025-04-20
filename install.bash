#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

cp ever/new_files/*.py .
cp -r ever/new_files/notebooks .
cp ever/new_files/scene/* scene/
cp ever/new_files/gaussian_renderer/* gaussian_renderer/
cp ever/new_files/utils/* utils/


# Build splinetracer
mkdir ever/build
cd ever/build
# CXX=/usr/bin/g++-11 CC=/usr/bin/gcc-11 cmake -DOptiX_INSTALL_DIR=$OptiX_INSTALL_DIR -D_GLIBCXX_USE_CXX11_ABI=1 ..
# CXX=$CXX CC=$CC cmake -DOptiX_INSTALL_DIR=$OptiX_INSTALL_DIR ..
CXX=$CXX CC=$CC cmake -DOptiX_INSTALL_DIR=$OptiX_INSTALL_DIR -DCMAKE_CUDA_ARCHITECTURES="50;60;61;70;75;80;86" ..
make -j8
cd ../..

pip install -e submodules/simple-knn

#! SIBR Viewer seems broken. 
#! see for more info: https://github.com/half-potato/ever_training/issues/22
# # SIBR Viewer
# cd SIBR_viewers
# pwd
# git status
# git apply ../ever/new_files/sibr_patch.patch
# cmake -Bbuild . -DCMAKE_BUILD_TYPE=Release
# cmake --build build -j24 --target install
# cd ../..
