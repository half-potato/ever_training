# Use an NVIDIA CUDA base image that includes development libraries
FROM nvidia/cuda:12.2.0-devel-ubuntu22.04

# Non-interactive mode for apt-get
ENV DEBIAN_FRONTEND=noninteractive


# Set an environment variable for OptiX installation.
# Adjust this to wherever you've placed OptiX inside the container or mount at runtime:
ENV OptiX_INSTALL_DIR=/opt/OptiX_7.4

# ------------------------------------------------------
# 1) Install System Dependencies
# ------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    git \
    cmake \
    unzip \
    build-essential \
    libglew-dev \
    libassimp-dev \
    libboost-all-dev \
    libgtk-3-dev \
    libopencv-dev \
    libglfw3-dev \
    libavdevice-dev \
    libavcodec-dev \
    libeigen3-dev \
    libxxf86vm-dev \
    libembree-dev \
    # libabsl-dev \
    libcgal-dev \
    libglm-dev \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------
# 2) Install a Miniconda / Conda environment
#    - We use Miniconda3 as an example here.
# ------------------------------------------------------
RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    bash Miniconda3-latest-Linux-x86_64.sh -b -p /opt/conda && \
    rm Miniconda3-latest-Linux-x86_64.sh

# Make conda available and create environment
ENV PATH="/opt/conda/bin:${PATH}"
RUN conda update -n base -c defaults conda && \
    conda create -n ever python=3.10 -y && \
    conda clean -ya

# By default, we activate conda env inside container with a script or using ENV:
SHELL ["/bin/bash", "-c"]
RUN echo "conda activate ever" >> ~/.bashrc

# ------------------------------------------------------
# 3) (Optional) Install Slang
#    Replace this section with the correct steps to install or build Slang from source if needed.
# ------------------------------------------------------
# RUN git clone --recursive https://github.com/shader-slang/slang.git /opt/slang && \
#     cd /opt/slang && \
#     # Example: build from source; replace with actual Slang build instructions
#     mkdir build && cd build && \
#     cmake -DCMAKE_BUILD_TYPE=Release .. && \
#     make -j"$(nproc)" && \
#     make install

RUN wget https://github.com/shader-slang/slang/releases/download/v2025.6.1/slang-2025.6.1-linux-x86_64.zip && \
    mkdir slang_install && \
    cd slang_install && \
    unzip ../slang-2025.6.1-linux-x86_64.zip && \
    cp bin/* /usr/bin/

# Clone, build, and install abseil-cpp.
RUN git clone https://github.com/abseil/abseil-cpp.git /tmp/abseil-cpp && \
    cd /tmp/abseil-cpp && \
    mkdir build && cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON .. && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    rm -rf /tmp/abseil-cpp

# ------------------------------------------------------
# 4) Install Python packages (within the 'ever' env)
# ------------------------------------------------------
RUN source activate ever && \
    # Adjust the PyTorch install line for your specific CUDA version if needed
    pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126 && \
    pip3 install --no-cache-dir cmake

# ------------------------------------------------------
# 5) Final Container Setup
# ------------------------------------------------------
# We'll define /ever_training as our working directory but
# won't copy any code here. We'll rely on runtime mounting.
WORKDIR /

COPY ./requirements.txt /

RUN cd / && \
    source activate ever && \
    pip install -r requirements.txt

COPY optix/ /opt/OptiX_7.4
COPY . /ever_training

RUN ls /opt/OptiX_7.4

ENV TORCH_CUDA_ARCH_LIST="5.0;6.0;6.1;7.0;7.5;8.0;8.6"
ENV CUDAARCHS="50 60 61 70 75 80 86"
ENV LD_LIBRARY_PATH="/slang_install/lib/"

WORKDIR /ever_training
RUN source activate ever && \
    rm -rf ever/build && \
    bash install.bash

# Expose any ports needed for training or viewer
EXPOSE 6009

# By default, just start a shell in the 'ever' environment
CMD ["/bin/bash", "-c", "source activate ever && exec bash"]

