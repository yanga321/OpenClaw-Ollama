"""
Llama.cpp Integration Bridge for OpenClaw OTG AI Drive

This module provides Python bindings to llama.cpp for running GGUF quantized 
models directly on Android devices via the OTG drive.

Features:
- Dynamic model loading from OTG storage
- Memory-efficient inference with RAM optimization
- Battery-aware token generation throttling
- Support for Phi-3, Gemma, Mistral, TinyLlama models
"""

import os
import sys
import ctypes
import logging
from typing import Optional, Generator, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for llama.cpp model loading"""
    model_path: str
    n_ctx: int = 2048  # Context size
    n_batch: int = 512  # Batch size
    n_threads: int = 4  # CPU threads
    n_gpu_layers: int = 0  # GPU offloading (0 for CPU-only)
    use_mmap: bool = True  # Memory-map model
    use_mlock: bool = False  # Lock model in memory
    
    # Optimization settings
    flash_attn: bool = False  # Flash attention (if supported)
    rope_freq_base: float = 10000.0
    rope_freq_scale: float = 1.0


@dataclass
class InferenceParams:
    """Parameters for text generation"""
    max_tokens: int = 512
    temperature: float = 0.7
    top_k: int = 40
    top_p: float = 0.9
    repeat_penalty: float = 1.1
    stop_sequences: list = None
    
    def __post_init__(self):
        if self.stop_sequences is None:
            self.stop_sequences = ["</s>", "###", "\n\n"]


class LlamaCppBridge:
    """
    Python bridge to llama.cpp C library
    
    This class handles loading the llama.cpp shared library and providing
    high-level inference APIs for the OpenClaw AI Drive.
    """
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.ctx = None
        self.model = None
        self._lock = threading.Lock()
        self._is_loaded = False
        
        # Try to load llama.cpp library
        self.lib = self._load_library()
        
    def _load_library(self) -> Optional[ctypes.CDLL]:
        """Load llama.cpp shared library"""
        possible_paths = [
            "/data/data/com.openclaw.otglauncher/files/libllama.so",
            "/system/lib64/libllama.so",
            "./libllama.so",
            os.path.join(os.path.dirname(__file__), "libllama.so"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    lib = ctypes.CDLL(path)
                    logger.info(f"Loaded llama.cpp from {path}")
                    return lib
                except Exception as e:
                    logger.warning(f"Failed to load {path}: {e}")
        
        logger.warning("llama.cpp library not found - using mock mode")
        return None
    
    def load_model(self) -> bool:
        """Load GGUF model into memory"""
        if not os.path.exists(self.config.model_path):
            logger.error(f"Model file not found: {self.config.model_path}")
            return False
        
        if self.lib is None:
            # Mock mode for testing without llama.cpp
            logger.info("Loading model in mock mode")
            self._is_loaded = True
            return True
        
        try:
            # Initialize llama.cpp
            # Note: Actual FFI bindings would go here
            # This is a simplified example
            
            llama_backend_init = self.lib.llama_backend_init
            llama_backend_init.argtypes = []
            llama_backend_init.restype = None
            llama_backend_init()
            
            # Load model parameters
            params = self._create_model_params()
            
            # Load model
            llama_load_model_from_file = self.lib.llama_load_model_from_file
            llama_load_model_from_file.argtypes = [ctypes.c_char_p, type(params)]
            llama_load_model_from_file.restype = ctypes.c_void_p
            
            model_path_bytes = self.config.model_path.encode('utf-8')
            self.model = llama_load_model_from_file(model_path_bytes, params)
            
            if self.model is None:
                logger.error("Failed to load model")
                return False
            
            # Create context
            ctx_params = self._create_context_params()
            
            llama_new_context_with_model = self.lib.llama_new_context_with_model
            llama_new_context_with_model.argtypes = [ctypes.c_void_p, type(ctx_params)]
            llama_new_context_with_model.restype = ctypes.c_void_p
            
            self.ctx = llama_new_context_with_model(self.model, ctx_params)
            
            if self.ctx is None:
                logger.error("Failed to create context")
                return False
            
            self._is_loaded = True
            logger.info(f"Model loaded successfully: {self.config.model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def _create_model_params(self):
        """Create llama_model_params structure"""
        # This would need actual struct definition from llama.h
        # Simplified for example
        class LlamaModelParams(ctypes.Structure):
            _fields_ = [
                ("n_gpu_layers", ctypes.c_int),
                ("split_mode", ctypes.c_int),
                ("main_gpu", ctypes.c_int),
                ("tensor_split", ctypes.POINTER(ctypes.c_float)),
                ("progress_callback", ctypes.c_void_p),
                ("progress_callback_user_data", ctypes.c_void_p),
                ("vocab_only", ctypes.c_bool),
                ("use_mmap", ctypes.c_bool),
                ("use_mlock", ctypes.c_bool),
            ]
        
        params = LlamaModelParams()
        params.n_gpu_layers = self.config.n_gpu_layers
        params.use_mmap = self.config.use_mmap
        params.use_mlock = self.config.use_mlock
        params.vocab_only = False
        
        return params
    
    def _create_context_params(self):
        """Create llama_context_params structure"""
        class LlamaContextParams(ctypes.Structure):
            _fields_ = [
                ("n_ctx", ctypes.c_uint),
                ("n_batch", ctypes.c_uint),
                ("n_ubatch", ctypes.c_uint),
                ("n_seq_max", ctypes.c_uint),
                ("n_threads", ctypes.c_int),
                ("n_threads_batch", ctypes.c_int),
                ("rope_scaling_type", ctypes.c_int),
                ("pooling_type", ctypes.c_int),
                ("rope_freq_base", ctypes.c_float),
                ("rope_freq_scale", ctypes.c_float),
                ("yarn_ext_factor", ctypes.c_float),
                ("yarn_attn_factor", ctypes.c_float),
                ("yarn_beta_fast", ctypes.c_float),
                ("yarn_beta_slow", ctypes.c_float),
                ("yarn_orig_ctx", ctypes.c_uint),
                ("defrag_thold", ctypes.c_float),
                ("cb_eval", ctypes.c_void_p),
                ("cb_eval_user_data", ctypes.c_void_p),
                ("type_k", ctypes.c_int),
                ("type_v", ctypes.c_int),
                ("logits_all", ctypes.c_bool),
                ("embeddings", ctypes.c_bool),
                ("offload_kqv", ctypes.c_bool),
                ("flash_attn", ctypes.c_bool),
            ]
        
        params = LlamaContextParams()
        params.n_ctx = self.config.n_ctx
        params.n_batch = self.config.n_batch
        params.n_threads = self.config.n_threads
        params.n_threads_batch = self.config.n_threads
        params.rope_freq_base = self.config.rope_freq_base
        params.rope_freq_scale = self.config.rope_freq_scale
        params.flash_attn = self.config.flash_attn
        params.logits_all = False
        params.embeddings = False
        params.offload_kqv = True
        
        return params
    
    def generate(self, prompt: str, params: InferenceParams) -> Generator[str, None, None]:
        """
        Generate text token-by-token
        
        Yields generated tokens as they are produced for streaming response
        """
        if not self._is_loaded:
            raise RuntimeError("Model not loaded")
        
        with self._lock:
            if self.lib is None:
                # Mock generation for testing
                yield from self._mock_generate(prompt, params)
                return
            
            # Tokenize prompt
            tokens = self._tokenize(prompt)
            
            # Evaluate prompt
            self._eval_tokens(tokens)
            
            # Generate tokens
            generated_tokens = 0
            output = ""
            
            while generated_tokens < params.max_tokens:
                # Sample next token
                token_id = self._sample_token(params)
                
                # Convert token to text
                token_text = self._detokenize(token_id)
                
                # Check for stop sequences
                output += token_text
                if any(stop in output for stop in params.stop_sequences):
                    break
                
                yield token_text
                generated_tokens += 1
                
                # Yield control for responsive UI
                if generated_tokens % 4 == 0:
                    time.sleep(0.01)
    
    def _mock_generate(self, prompt: str, params: InferenceParams) -> Generator[str, None, None]:
        """Mock generation for testing without llama.cpp"""
        mock_responses = [
            "Hello! I'm your OpenClaw AI assistant running locally on your OTG drive. ",
            "I can help you with various tasks while keeping your data private. ",
            "How can I assist you today?",
        ]
        
        for response in mock_responses:
            for char in response:
                yield char
                time.sleep(0.02)
    
    def _tokenize(self, text: str) -> list:
        """Tokenize text into token IDs"""
        if self.lib is None:
            return list(range(len(text)))  # Mock tokenization
        
        # Actual tokenization using llama_tokenize
        pass
    
    def _eval_tokens(self, tokens: list) -> None:
        """Evaluate tokens through the model"""
        if self.lib is None:
            return
        
        # Actual evaluation using llama_decode
        pass
    
    def _sample_token(self, params: InferenceParams) -> int:
        """Sample next token using sampling parameters"""
        if self.lib is None:
            return ord(' ')  # Mock sampling
        
        # Actual sampling using llama_sampler_sample
        pass
    
    def _detokenize(self, token_id: int) -> str:
        """Convert token ID to text"""
        if self.lib is None:
            return chr(token_id % 128)  # Mock detokenization
        
        # Actual detokenization using llama_token_to_piece
        pass
    
    def unload(self) -> None:
        """Unload model and free resources"""
        with self._lock:
            if self.ctx is not None and self.lib is not None:
                llama_free = self.lib.llama_free
                llama_free.argtypes = [ctypes.c_void_p]
                llama_free(self.ctx)
                self.ctx = None
            
            if self.model is not None and self.lib is not None:
                llama_free_model = self.lib.llama_free_model
                llama_free_model.argtypes = [ctypes.c_void_p]
                llama_free_model(self.model)
                self.model = None
            
            if self.lib is not None:
                llama_backend_free = self.lib.llama_backend_free
                llama_backend_free.argtypes = []
                llama_backend_free()
            
            self._is_loaded = False
            logger.info("Model unloaded")


class AdaptiveInferenceEngine:
    """
    High-level inference engine with adaptive optimization
    
    Wraps LlamaCppBridge with battery-aware throttling,
    memory management, and dynamic quality adjustment.
    """
    
    def __init__(self, otg_models_dir: str):
        self.otg_models_dir = Path(otg_models_dir)
        self.current_bridge: Optional[LlamaCppBridge] = None
        self.current_model: Optional[str] = None
        self._battery_level = 100
        self._temperature = 35
    
    def select_best_model(self) -> Optional[Path]:
        """Select best model based on available RAM and battery"""
        if not self.otg_models_dir.exists():
            return None
        
        # Get available models
        gguf_files = list(self.otg_models_dir.glob("*.gguf"))
        
        if not gguf_files:
            return None
        
        # Simple selection: prefer smaller models when battery is low
        if self._battery_level < 30:
            # Sort by size, pick smallest
            gguf_files.sort(key=lambda f: f.stat().st_size)
            return gguf_files[0]
        else:
            # Pick first available (could implement smarter selection)
            return gguf_files[0]
    
    def load_model(self, model_path: Optional[str] = None) -> bool:
        """Load model with adaptive configuration"""
        if model_path is None:
            model_path = self.select_best_model()
            if model_path is None:
                logger.error("No models available")
                return False
            model_path = str(model_path)
        
        # Adaptive config based on system state
        config = self._create_adaptive_config(model_path)
        
        self.current_bridge = LlamaCppBridge(config)
        
        if not self.current_bridge.load_model():
            return False
        
        self.current_model = model_path
        logger.info(f"Loaded model: {model_path}")
        return True
    
    def _create_adaptive_config(self, model_path: str) -> ModelConfig:
        """Create model config optimized for current conditions"""
        model_size_gb = Path(model_path).stat().st_size / (1024**3)
        
        # Base configuration
        n_ctx = 2048
        n_threads = 4
        
        # Adjust for battery level
        if self._battery_level < 20:
            n_ctx = 1024
            n_threads = 2
        elif self._battery_level < 50:
            n_ctx = 1536
            n_threads = 3
        
        # Adjust for temperature
        if self._temperature > 45:
            n_threads = max(2, n_threads - 1)
        
        return ModelConfig(
            model_path=model_path,
            n_ctx=n_ctx,
            n_batch=min(512, n_ctx // 4),
            n_threads=n_threads,
            use_mmap=True,
            use_mlock=self._battery_level > 50,
        )
    
    def generate_stream(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        """Generate text with streaming output"""
        if self.current_bridge is None:
            raise RuntimeError("No model loaded")
        
        params = InferenceParams(**kwargs)
        yield from self.current_bridge.generate(prompt, params)
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate complete response"""
        tokens = list(self.generate_stream(prompt, **kwargs))
        return "".join(tokens)
    
    def update_system_state(self, battery_level: int, temperature: float) -> None:
        """Update system state for adaptive optimization"""
        self._battery_level = battery_level
        self._temperature = temperature
        
        # Potentially reload model with new config if conditions changed significantly
        if self.current_model is not None:
            old_battery = getattr(self, '_prev_battery', 100)
            if abs(battery_level - old_battery) > 30:
                logger.info("Battery changed significantly, consider reloading model")
                # Could trigger model reload here
        
        self._prev_battery = battery_level
    
    def unload(self) -> None:
        """Unload current model"""
        if self.current_bridge is not None:
            self.current_bridge.unload()
            self.current_bridge = None
            self.current_model = None


# Convenience function for quick usage
def create_engine(otg_path: str) -> AdaptiveInferenceEngine:
    """Create and initialize inference engine"""
    models_dir = os.path.join(otg_path, "models")
    engine = AdaptiveInferenceEngine(models_dir)
    return engine


if __name__ == "__main__":
    # Example usage
    import argparse
    
    parser = argparse.ArgumentParser(description="Llama.cpp Integration Test")
    parser.add_argument("--otg-path", default="/storage/usbStorage", help="OTG drive path")
    parser.add_argument("--prompt", default="Hello, how are you?", help="Prompt to generate")
    args = parser.parse_args()
    
    print("Initializing OpenClaw AI Engine...")
    engine = create_engine(args.otg_path)
    
    print("Loading model...")
    if not engine.load_model():
        print("Failed to load model")
        sys.exit(1)
    
    print(f"Generating response to: {args.prompt}")
    print("-" * 50)
    
    response = ""
    for token in engine.generate_stream(args.prompt, max_tokens=256):
        print(token, end="", flush=True)
        response += token
    
    print("\n" + "-" * 50)
    print(f"Generated {len(response)} characters")
    
    engine.unload()
