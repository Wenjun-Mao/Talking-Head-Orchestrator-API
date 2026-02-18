# SoulX-FlashHead integration guide (s4-inference-engine)

This guide documents the exact setup required to run `s4-inference-engine` with SoulX-FlashHead and NVIDIA GPU acceleration.

## 1) Host prerequisites (Ubuntu, NVIDIA GPU)

### A. Install NVIDIA driver and verify host GPU
```bash
nvidia-smi
```

If this fails, install/repair the NVIDIA driver first.

### B. Install Docker Engine (apt package preferred)

Use Docker CE from Docker’s apt repo. Avoid Snap Docker for GPU workflows.

Check install source:
```bash
docker info | grep -i "Docker Root Dir\|Server Version"
snap list | grep docker || true
```

If Docker is from Snap and GPU access fails, migrate to Docker CE.

### C. Install NVIDIA Container Toolkit

`nvidia-container-toolkit` is not in default Ubuntu repos, so add NVIDIA repo first:

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Validate Docker GPU access:
```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

If this fails, do not proceed to service-level debugging until host/runtime is fixed.

## 2) Vendor SoulX-FlashHead source

From repo root:
```bash
cd services/s4-inference-engine/vendor
git clone <your SoulX-FlashHead fork or upstream URL> SoulX-FlashHead
```

Expected path:
- `services/s4-inference-engine/vendor/SoulX-FlashHead`

## 3) Place required model folders

Copy model folders into:
- `services/s4-inference-engine/vendor/SoulX-FlashHead/models/SoulX-FlashHead-1_3B`
- `services/s4-inference-engine/vendor/SoulX-FlashHead/models/wav2vec2-base-960h`

Compose mounts this path into the container as `/models`.

## 4) Ensure SoulX requirements are compatible

File:
- `services/s4-inference-engine/vendor/SoulX-FlashHead/requirements.txt`

Important detail for this project:
- Do not pin `nvidia-nccl-cu12` to an exact version in this environment.
- Keep it unpinned (`nvidia-nccl-cu12`) and keep pinned line removed or commented.

Current expected form in that file:
```txt
# nvidia-nccl-cu12==2.27.3
nvidia-nccl-cu12
```

## 5) Download FlashAttention wheel used by this repo

The wheel URL is tracked in:
- `services/s4-inference-engine/vendor/flash_attn_url.txt`

Download into `services/s4-inference-engine/vendor/`:
```bash
cd services/s4-inference-engine/vendor
wget -O flash_attn-2.8.0.post2+cu12torch2.7cxx11abiFALSE-cp310-cp310-linux_x86_64.whl \
  "$(cat flash_attn_url.txt)"
```

Expected wheel path:
- `services/s4-inference-engine/vendor/flash_attn-2.8.0.post2+cu12torch2.7cxx11abiFALSE-cp310-cp310-linux_x86_64.whl`

## 6) Optional condition image

Default expected image:
- `data/imgs/girl.png`

Configured by compose env:
- `S4_COND_IMAGE_PATH=/data/imgs/girl.png`

## 7) Build and run s4

From repo root:
```bash
docker compose -f infra/docker-compose/compose.yaml up -d --build s4-inference-engine
docker compose -f infra/docker-compose/compose.yaml logs -f --tail=200 s4-inference-engine
```

## 8) What “healthy enough” looks like

In logs, expect:
- worker startup and queue binding on `s4-inference-engine`
- SoulX runtime initialization
- optional startup prewarm logs (if enabled)

Warnings that are usually non-fatal:
- TorchInductor autotune warnings like “Not enough SMs to use max_autotune_gemm mode”

## 9) Common failure modes

### `could not select device driver "" with capabilities: [[gpu]]`
- Root cause: NVIDIA container runtime not configured for Docker.
- Fix: complete section 1C and re-test with CUDA `nvidia-smi` container.

### `Unable to locate package nvidia-container-toolkit`
- Root cause: NVIDIA apt repo not added.
- Fix: complete section 1C repo setup exactly.

### FlashAttention wheel install fails
- Verify wheel filename/path exactly matches Dockerfile install path.
- Ensure Python/CUDA/Torch ABI in wheel matches current image setup.

### s4 starts but model load fails
- Verify model folder names and mount path (`/models/...`) exactly match compose env variables.

## 10) Change checklist when updating SoulX/Torch

When bumping SoulX/Torch/CUDA stack:
- re-validate `vendor/SoulX-FlashHead/requirements.txt`
- refresh `vendor/flash_attn_url.txt` and wheel file
- rebuild `s4-inference-engine`
- verify runtime init + first inference job end-to-end