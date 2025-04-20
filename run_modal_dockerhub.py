import os
from pathlib import Path
import socket
import subprocess
import threading
import time

import modal

app = modal.App("ever", image=modal.Image.from_registry("halfpotato/ever:latest", add_python="3.12") 
    # GCloud
    #TODO: Install gcloud
    .run_commands("apt-get update && apt-get install -y curl gnupg && \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg && \
    echo \"deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main\" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && \
    apt-get update && apt-get install -y google-cloud-cli")
    .add_local_file(Path.home() / "gcs-tour-project-service-account-key.json", "/root/gcs-tour-project-service-account-key.json", copy=True)
    .run_commands(
        "gcloud auth activate-service-account --key-file=/root/gcs-tour-project-service-account-key.json",
        "gcloud config set project tour-project-442218",
        "gcloud storage ls"
    )
    .env({"GOOGLE_APPLICATION_CREDENTIALS": "/root/gcs-tour-project-service-account-key.json"})
    .run_commands("gcloud storage ls")
    # # Add the whole OpenHome repo to the image
    # .run_commands('git config --global url."https://${GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/" && git clone --recurse-submodules https://${GITHUB_TOKEN}@github.com/N-Demir/openhome /root/openhome', secrets=[modal.Secret.from_name("github-token")])
    # .workdir("/root/openhome")
    # # SSH server
    # .apt_install("openssh-server")
    # .run_commands(
    #     "mkdir -p /run/sshd" #, "echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config", "echo 'root: ' | chpasswd" #TODO: uncomment this if the key approach doesn't work
    # )
    # .add_local_file(Path.home() / ".ssh/id_rsa.pub", "/root/.ssh/authorized_keys", copy=True)
    # # VSCode
    # .run_commands("curl -fsSL https://code-server.dev/install.sh | sh")
    # # Add Conda (for some reason necessary for ssh-based code running)
    # .run_commands("conda init bash && echo 'conda activate base' >> ~/.bashrc")
    # # Fix Git
    # .run_commands("git config pull.rebase true")
    # .run_commands("git config --global user.name 'Nikita Demir'")
    # .run_commands("git config --global user.email 'nikitde1@gmail.com'")

    #! TODO: This may need to look a bit different
    # # Add Our Code
    # .workdir("/root/openhome/train/gsplat/")
    # .run_commands("git checkout main") # TODO: I'm not sure why we would need this, seems maybe like it's temporary
    # .run_commands("git pull --recurse-submodules") # This probably does nothing
    # .run_commands("git submodule update --init --recursive") # This is important!
    # .add_local_dir(Path(__file__).parent, "/root/openhome/train/gsplat")
)


LOCAL_PORT = 9090


def wait_for_port(host, port, q):
    start_time = time.monotonic()
    while True:
        try:
            with socket.create_connection(("localhost", 22), timeout=30.0):
                break
        except OSError as exc:
            time.sleep(0.01)
            if time.monotonic() - start_time >= 30.0:
                raise TimeoutError("Waited too long for port 22 to accept connections") from exc
        q.put((host, port))


@app.function(
    timeout=3600 * 24,
    gpu="T4",
    secrets=[modal.Secret.from_name("wandb-secret"), modal.Secret.from_name("github-token")],
)
def launch_ssh(q):
    with modal.forward(22, unencrypted=True) as tunnel:
        host, port = tunnel.tcp_socket
        threading.Thread(target=wait_for_port, args=(host, port, q)).start()

        # Added these commands to get the env variables that docker loads in through ENV to show up in my ssh
        subprocess.run("env | awk '{print \"export \" $1}' > ~/env_variables.sh", shell=True)
        subprocess.run("echo 'source ~/env_variables.sh' >> ~/.bashrc", shell=True)

        subprocess.run(["/usr/sbin/sshd", "-D"])  # TODO: I don't know why I need to start this here

@app.local_entrypoint()
def main():
    pass
    # import sshtunnel

    # with modal.Queue.ephemeral() as q:
    #     launch_ssh.spawn(q)
    #     host, port = q.get()
    #     print(f"SSH server running at {host}:{port}")

    #     server = sshtunnel.SSHTunnelForwarder(
    #         (host, port),
    #         ssh_username="root",
    #         ssh_password=" ",
    #         remote_bind_address=("127.0.0.1", 22),
    #         local_bind_address=("127.0.0.1", LOCAL_PORT),
    #         allow_agent=False,
    #     )

    #     try:
    #         server.start()
    #         print(f"SSH tunnel forwarded to localhost:{server.local_bind_port}")
    #         while True:
    #             time.sleep(1)
    #     except KeyboardInterrupt:
    #         print("\nShutting down SSH tunnel...")
    #     finally:
    #         server.stop()
