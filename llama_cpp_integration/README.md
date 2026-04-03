# Llama.cpp Integration Guide

## Overview

This directory contains the Python bridge to llama.cpp for running GGUF quantized models on Android devices via the OTG drive.

## Architecture

```
llama_bridge.py
├── LlamaCppBridge          # Low-level C FFI bindings
└── AdaptiveInferenceEngine # High-level adaptive inference
```

## Quick Start

### 1. Build llama.cpp for Android

```bash
# Clone llama.cpp
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp

# Build for Android ARM64
export ANDROID_NDK=/path/to/android-ndk-r26
mkdir build-android && cd build-android

cmake .. \
  -DCMAKE_TOOLCHAIN_FILE=$ANDROID_NDK/build/cmake/android.toolchain.cmake \
  -DANDROID_ABI=arm64-v8a \
  -DANDROID_PLATFORM=android-26 \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLAMA_BUILD_SERVER=OFF \
  -DLLAMA_BUILD_TESTS=OFF

make -j8

# Copy library to APK assets
cp libllama.so /workspace/host-apk/app/src/main/jniLibs/arm64-v8a/
```

### 2. Download GGUF Models

Place models in OTG drive:
```bash
mkdir -p /mnt/otg/models

# Example: Phi-3 Mini (2GB)
wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4_k_m.gguf \
  -O /mnt/otg/models/phi3-mini.gguf

# Example: Gemma 2B (1.5GB)
wget https://huggingface.co/google/gemma-2b-it-GGUF/resolve/main/gemma-2b-it-q4_k_m.gguf \
  -O /mnt/otg/models/gemma-2b.gguf
```

### 3. Test Integration

```bash
cd /workspace/llama_cpp_integration

# Run test
python llama_bridge.py --otg-path /mnt/otg --prompt "Hello, who are you?"
```

## API Reference

### ModelConfig

```python
@dataclass
class ModelConfig:
    model_path: str        # Path to GGUF file
    n_ctx: int = 2048      # Context window size
    n_batch: int = 512     # Batch size for prompt processing
    n_threads: int = 4     # CPU threads
    n_gpu_layers: int = 0  # GPU offloading layers
    use_mmap: bool = True  # Memory-map model file
    use_mlock: bool = False # Lock model in RAM
```

### InferenceParams

```python
@dataclass
class InferenceParams:
    max_tokens: int = 512       # Max tokens to generate
    temperature: float = 0.7    # Sampling temperature
    top_k: int = 40            # Top-k sampling
    top_p: float = 0.9         # Nucleus sampling
    repeat_penalty: float = 1.1 # Repetition penalty
    stop_sequences: list = None # Stop generation strings
```

### Usage Examples

#### Basic Generation

```python
from llama_bridge import create_engine

engine = create_engine("/mnt/otg")
engine.load_model()

response = engine.generate("What is quantum computing?")
print(response)

engine.unload()
```

#### Streaming Generation

```python
for token in engine.generate_stream(
    "Explain black holes",
    max_tokens=256,
    temperature=0.8
):
    print(token, end="", flush=True)
```

#### Adaptive Loading

```python
# Automatically selects best model based on battery/RAM
engine = create_engine("/mnt/otg")
engine.update_system_state(battery_level=45, temperature=38)
engine.load_model()  # Will choose smaller model for low battery
```

## Performance Optimization

### Battery-Aware Throttling

The `AdaptiveInferenceEngine` automatically adjusts:
- Context size (1024-2048 tokens)
- Thread count (2-4 threads)
- Model selection (prefers smaller models when battery < 30%)

### Memory Management

- Uses memory-mapped I/O (`use_mmap=True`) to reduce RAM usage
- Optional memory locking (`use_mlock`) for faster access when battery > 50%
- Automatic model unloading on low memory warnings

### Recommended Settings by Device

| Device RAM | Model Size | Context | Threads | Expected Speed |
|------------|-----------|---------|---------|----------------|
| 2GB        | ≤1GB      | 1024    | 2       | 8-12 tok/s     |
| 3GB        | ≤2GB      | 1536    | 3       | 12-18 tok/s    |
| 4GB+       | ≤3GB      | 2048    | 4       | 18-25 tok/s    |

## Supported Models

Tested and verified:
- ✅ Phi-3 Mini (3.8B) - Q4_K_M
- ✅ Gemma 2B - Q4_K_M
- ✅ TinyLlama 1.1B - Q4_K_M
- ✅ Mistral 7B - Q3_K_S (high-end devices)
- ✅ StableLM 2 Zephyr - Q4_K_M

## Troubleshooting

### Model Loading Fails

1. Check file path is correct
2. Verify GGUF format (v3 recommended)
3. Ensure sufficient free RAM (model size × 1.2)

### Slow Inference

1. Reduce context size (`n_ctx`)
2. Lower thread count if overheating
3. Use smaller quantization (Q3_K_S vs Q4_K_M)

### Out of Memory

1. Enable `use_mmap=True`
2. Close background apps
3. Use smaller model

## Building llama.cpp from Source

For custom builds with optimizations:

```bash
cd llama.cpp

# Build with NEON optimizations (ARM)
make -j8 LLAMA_NEON=1

# Build with custom BLAS
make -j8 LLAMA_BLAS=1 LLAMA_BLAS_VENDOR=OpenBLAS

# Strip binary for smaller size
strip -s libllama.so
```

## Next Steps

1. Integrate with Host APK via PySide6 or Chaquopy
2. Add GPU acceleration via Vulkan backend
3. Implement speculative decoding for faster inference
4. Add LoRA adapter support for fine-tuned models

## References

- [llama.cpp GitHub](https://github.com/ggerganov/llama.cpp)
- [GGUF Format Spec](https://github.com/ggerganov/ggml/blob/master/docs/gguf.md)
- [HuggingFace GGUF Models](https://huggingface.co/models?library=gguf)
