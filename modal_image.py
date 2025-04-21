import modal

# Define the Modal image by translating Dockerfile steps
image = (
    modal.Image.from_registry("nvidia/cuda:12.2.0-devel-ubuntu22.04", add_python="3.10")
    .env({
        "DEBIAN_FRONTEND": "noninteractive",
        "OptiX_INSTALL_DIR": "/opt/OptiX_7.4",
        "TORCH_CUDA_ARCH_LIST": "5.0;6.0;6.1;7.0;7.5;8.0;8.6",
        "CUDAARCHS": "50 60 61 70 75 80 86",
        "LD_LIBRARY_PATH": "/slang_install/lib/", # From Dockerfile, check if slang install path matches
    })
    # Install system dependencies
    .apt_install(
        "wget", "git", "cmake", "unzip", "build-essential", "libglew-dev",
        "libassimp-dev", "libboost-all-dev", "libgtk-3-dev", "libopencv-dev",
        "libglfw3-dev", "libavdevice-dev", "libavcodec-dev", "libeigen3-dev",
        "libxxf86vm-dev", "libembree-dev", "libcgal-dev", "libglm-dev",
    )
    # Install Miniconda and create the 'ever' environment
    .run_commands(
        "wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh",
        "bash miniconda.sh -b -p /opt/conda",
        "rm miniconda.sh",
        "/opt/conda/bin/conda init bash", # Initialize conda for bash shell
        "/opt/conda/bin/conda update -n base -c defaults conda -y",
        "/opt/conda/bin/conda create -n ever python=3.10 -y",
        "/opt/conda/bin/conda clean -ya",
    )
    # Install Slang
    .run_commands(
        "wget https://github.com/shader-slang/slang/releases/download/v2025.6.4/slang-2025.6.4-linux-x86_64.zip",
        "mkdir /slang_install",
        "unzip slang-2025.6.4-linux-x86_64.zip -d /slang_install",
        "cp /slang_install/bin/* /usr/bin/", # Copy binaries to standard location
        "rm slang-2025.6.4-linux-x86_64.zip",
    )
    # Install abseil-cpp from source
    .run_commands(
        "git clone https://github.com/abseil/abseil-cpp.git /tmp/abseil-cpp",
        # Build and install abseil using bash for command chaining and subshells
        "bash -c 'cd /tmp/abseil-cpp && mkdir build && cd build && cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON .. && make -j$(nproc) && make install && ldconfig'",
        "rm -rf /tmp/abseil-cpp", # Clean up source directory
    )
    # Install core Python packages (PyTorch, cmake) into the 'ever' env using pip via conda run
    .run_commands(
         # Ensure PyTorch is installed for the correct CUDA version
         "/opt/conda/bin/conda run -n ever pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126",
         # Install cmake via pip (as in Dockerfile)
         "/opt/conda/bin/conda run -n ever pip install --no-cache-dir 'cmake<4'",
    )
    # Add requirements.txt and install dependencies into the 'ever' env, forcing build with copy=True
    .add_local_file(local_path="requirements.txt", remote_path="/requirements.txt", copy=True)
    .run_commands(
        # Install packages from requirements.txt within the 'ever' environment
        "/opt/conda/bin/conda run -n ever pip install -r /requirements.txt",
    )
    # Add OptiX SDK and project code into the image, forcing build with copy=True
    .add_local_dir(local_path="optix", remote_path="/opt/OptiX_7.4", copy=True)
    .add_local_dir(local_path=".", remote_path="/ever_training", copy=True, ignore=modal.FilePatternMatcher.from_file(".dockerignore"))
    .run_commands("sh ignore_me.sh") # TODO: Remove, just for testing to see if changes to this file are causing the above line to rerun (they are! despite it being ignored)
    # Set the working directory for subsequent commands and function execution
    .workdir("/ever_training")
    # Run the project's install script within the 'ever' env
    .run_commands(
        # Execute install.bash using conda run to ensure correct environment activation
        "/opt/conda/bin/conda run -n ever bash install.bash", gpu="T4"
    )
)

# Example of how to use this image with a Modal Stub
# Needs `modal` imported if used in a separate file or context.
#
# stub = modal.Stub(name="ever-training-stub", image=image)
#
# @stub.function(gpu="any") # Request GPU if needed by the function
# def train():
#     """Runs the training process inside the Modal container."""
#     import subprocess
#     # Example: Run a command assuming the working directory and environment are set
#     result = subprocess.run(["python", "train_script.py"], capture_output=True, text=True)
#     print(result.stdout)
#     print(result.stderr)
#     if result.returncode != 0:
#         raise Exception("Training script failed")
#
# @stub.local_entrypoint()
# def main():
#     train.remote()
