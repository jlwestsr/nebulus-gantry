# Model Switching

Complete guide to hot-swapping LLM models in Gantry using TabbyAPI integration for dynamic model management without restarting services.

---

## Overview

**Model Switching** allows administrators to change the active LLM without restarting Gantry or interrupting user sessions:

- **Hot-swap models** - Switch between models in seconds
- **No downtime** - Chat interface remains available
- **Zero config** - Automatic detection of available models
- **TabbyAPI integration** - Full TabbyAPI model management support
- **Multi-model support** - Switch between any models in TabbyAPI's library

**Benefits:**

- Test different models for specific tasks
- Match model to workload (coding, creative writing, analysis)
- Upgrade models without redeployment
- Free VRAM when not in use

**Requirements:**

- TabbyAPI as LLM backend
- Multiple models in TabbyAPI's `models/` directory
- Admin role access

---

## TabbyAPI Integration

### Why TabbyAPI?

**TabbyAPI** is the recommended LLM backend for Gantry because it provides:

- **OpenAI-compatible API** - Drop-in replacement for OpenAI
- **Model management endpoints** - Load/unload models via API
- **ExLlamaV2 engine** - Fast inference with GPU acceleration
- **Streaming support** - Real-time response generation
- **Multiple quantizations** - Q4, Q5, Q8 for memory optimization

**Alternatives** (without hot-swap):

- Ollama - Must restart to change model
- vLLM - Requires container restart
- LM Studio - Manual GUI interaction

### TabbyAPI Setup

**Install TabbyAPI:**

```bash
git clone https://github.com/theroyallab/tabbyAPI.git
cd tabbyAPI
pip install -r requirements.txt
```

**Directory structure:**

```text
tabbyAPI/
├── main.py
├── models/
│   ├── Qwen2.5-Coder-7B-Instruct/
│   ├── Llama-3.1-8B-Instruct/
│   ├── Mistral-7B-Instruct-v0.3/
│   └── DeepSeek-Coder-6.7B/
└── config.yml
```

**Download models:**

```bash
# Example: Download Qwen2.5-Coder-7B-Instruct
huggingface-cli download TheBloke/Qwen2.5-Coder-7B-Instruct-GGUF \
  --local-dir models/Qwen2.5-Coder-7B-Instruct
```

**Start TabbyAPI:**

```bash
python main.py --host 0.0.0.0 --port 5000
```

**Configure Gantry:**

```bash
# .env
TABBY_HOST=http://tabbyapi:5000
```

### TabbyAPI Endpoints

**Gantry uses these TabbyAPI endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/models` | GET | List available models |
| `/v1/model` | GET | Get currently loaded model |
| `/v1/model/load` | POST | Load a new model |
| `/v1/model/unload` | POST | Unload current model |
| `/v1/chat/completions` | POST | Generate chat response (streaming) |

**Test TabbyAPI manually:**

```bash
# List models
curl http://localhost:5000/v1/models

# Get active model
curl http://localhost:5000/v1/model

# Load model
curl -X POST http://localhost:5000/v1/model/load \
  -H "Content-Type: application/json" \
  -d '{"model_name": "Llama-3.1-8B-Instruct"}'

# Unload model
curl -X POST http://localhost:5000/v1/model/unload
```

---

## Using Model Switching

### Access Model Management

1. **Log in as admin**
2. **Click profile icon** (top-right)
3. **Select "Admin Dashboard"**
4. **Click "Models" tab**

### View Available Models

**Models page shows:**

```text
Available Models:
┌─────────────────────────────────────┬────────┐
│ Model                               │ Status │
├─────────────────────────────────────┼────────┤
│ ✓ Qwen2.5-Coder-7B-Instruct        │ Active │
│   Llama-3.1-8B-Instruct            │        │
│   Mistral-7B-Instruct-v0.3         │        │
│   DeepSeek-Coder-6.7B              │        │
└─────────────────────────────────────┴────────┘
```

**Model information:**

- Model ID (directory name in TabbyAPI)
- Active status (✓ if currently loaded)
- Actions (Switch, Unload)

### Switch to Different Model

1. **Click "Switch" button** next to desired model
2. **Confirm action** in dialog
3. **Wait for loading** (progress indicator shows status)
4. **Model switched!** New model now handles all chat requests

**Switching process:**

```text
Step 1: Unloading current model...        [####----] 40%
Step 2: Loading Llama-3.1-8B-Instruct... [########] 100%
✓ Model switched successfully!
```

**Timing:**

| Operation | Duration |
|-----------|----------|
| Unload model | 2-5 seconds |
| Load 3B model | 5-10 seconds |
| Load 7B model | 10-30 seconds |
| Load 13B model | 30-60 seconds |
| Load 34B+ model | 60-120+ seconds |

**During switch:**

- ✅ Chat interface stays open
- ✅ Existing conversations preserved
- ✅ New messages queued
- ✅ Users see "Model loading..." message
- ✅ Streaming resumes when ready

### Unload Current Model

**Free VRAM without loading a new model:**

1. **Click "Unload Model" button**
2. **Confirm action**
3. **Model removed from VRAM**

**Use cases:**

- Free GPU memory for other tasks
- Troubleshoot model issues
- Prepare for manual model change

**Impact:**

- Chat unavailable until new model loaded
- Users see "Model not available" message
- All conversations and data preserved

---

## Model Selection Strategy

### Choose the Right Model

**By task type:**

**Coding tasks:**

- Qwen2.5-Coder-7B-Instruct (best)
- DeepSeek-Coder-6.7B (good)
- Llama-3.1-8B-Instruct (acceptable)

**Creative writing:**

- Mistral-7B-Instruct-v0.3 (best)
- Llama-3.1-8B-Instruct (good)

**General chat:**

- Llama-3.1-8B-Instruct (best balance)
- Qwen2.5-7B-Instruct (good)

**Analysis/reasoning:**

- Llama-3.1-8B-Instruct (best)
- Qwen2.5-7B-Instruct (good)

### Model Size Trade-offs

**Small models (3B-7B):**

- ✅ Fast inference (20-50 tokens/sec)
- ✅ Low VRAM usage (4-8 GB)
- ✅ Quick loading (5-15 seconds)
- ❌ Less capable on complex tasks
- ❌ Shorter context awareness

**Medium models (13B-20B):**

- ✅ Better reasoning
- ✅ More nuanced responses
- ❌ Slower inference (10-20 tokens/sec)
- ❌ Higher VRAM (12-20 GB)
- ❌ Longer loading (30-60 seconds)

**Large models (30B-70B):**

- ✅ Excellent capabilities
- ✅ Strong reasoning
- ❌ Slow inference (5-10 tokens/sec)
- ❌ High VRAM (24-48 GB)
- ❌ Very long loading (60-120+ seconds)

### Quantization Levels

**Balance quality vs. memory:**

| Quantization | VRAM (7B model) | Quality | Speed |
|--------------|-----------------|---------|-------|
| Q8 | 8 GB | Excellent | Slow |
| Q6 | 6 GB | Very Good | Medium |
| Q5 | 5 GB | Good | Medium |
| Q4 | 4 GB | Acceptable | Fast |
| Q3 | 3 GB | Poor | Fast |

**Recommendation:** Q5 or Q6 for best balance

---

## Model Management

### Add New Models

**To add models to TabbyAPI:**

1. **Download model** from Hugging Face:

```bash
cd tabbyAPI/models
huggingface-cli download TheBloke/ModelName-GGUF \
  --local-dir ModelName
```

2. **Verify model files:**

```text
models/ModelName/
├── config.json
├── tokenizer.json
├── model-Q5_K_M.gguf
└── ...
```

3. **Restart TabbyAPI** (or wait for auto-detection)

4. **Refresh Gantry admin dashboard**

5. **New model appears** in available models list

**Supported formats:**

- GGUF (recommended)
- Safetensors
- PyTorch checkpoints

### Remove Models

**To free disk space:**

1. **Stop TabbyAPI**

```bash
# Stop TabbyAPI process
```

2. **Delete model directory:**

```bash
cd tabbyAPI/models
rm -rf ModelName
```

3. **Restart TabbyAPI**

4. **Model removed** from Gantry's list

### Update Models

**To update a model to newer version:**

1. **Download new version** with different name:

```bash
huggingface-cli download TheBloke/ModelName-v2-GGUF \
  --local-dir ModelName-v2
```

2. **Switch to new model** in Gantry

3. **Test new model**

4. **Delete old version** if satisfied

**Note:** Keep old version until new one proven stable

---

## Advanced Configuration

### TabbyAPI Config

**Optimize TabbyAPI for model switching:**

Edit `tabbyAPI/config.yml`:

```yaml
# Model loading settings
model:
  max_seq_len: 4096  # Context window
  gpu_split_auto: true  # Automatic GPU memory allocation
  cache_mode: "q4"  # KV cache quantization (saves VRAM)

# Performance
performance:
  max_batch_size: 128
  cache_size: 2048
```

**Key settings:**

- `max_seq_len`: Larger = more context but slower loading
- `gpu_split_auto`: Multi-GPU support
- `cache_mode`: Lower = faster switching but less quality

### Gantry Integration Config

**Backend configuration:**

No changes needed - Gantry auto-detects TabbyAPI capabilities.

**Environment variables:**

```bash
# .env
TABBY_HOST=http://tabbyapi:5000  # TabbyAPI endpoint
```

**Timeouts:**

Edit `backend/services/model_service.py`:

```python
# Model switch timeout (seconds)
SWITCH_TIMEOUT = 30  # Default: 30, increase for large models

# Model list refresh interval (seconds)
REFRESH_INTERVAL = 60  # Default: 60
```

---

## Troubleshooting

### Model Switch Fails

**Error:** "Failed to switch model"

**Checks:**

```bash
# 1. Verify TabbyAPI is responding
curl http://localhost:5000/v1/models

# 2. Check if model exists in TabbyAPI
ls -la tabbyAPI/models/

# 3. Test manual model load
curl -X POST http://localhost:5000/v1/model/load \
  -H "Content-Type: application/json" \
  -d '{"model_name": "ModelName"}'

# 4. Check TabbyAPI logs
tail -f tabbyAPI/logs/tabby.log
```

**Common causes:**

- **Insufficient VRAM:** Model too large for GPU
- **Invalid model name:** Typo or directory mismatch
- **Corrupted model files:** Re-download model
- **TabbyAPI crash:** Restart TabbyAPI

### Slow Model Loading

**Issue:** Model takes several minutes to load.

**Causes:**

- **Large model size:** 34B+ models inherently slow
- **Limited VRAM:** Offloading to CPU
- **Slow disk:** Model loading from HDD instead of SSD
- **Network loading:** Model on NFS/network storage

**Solutions:**

- Use smaller/quantized models (Q4 instead of Q8)
- Upgrade to more VRAM
- Move models to SSD
- Pre-load models to local disk

### Model Not Appearing

**Issue:** New model not in Gantry's list.

**Fixes:**

```bash
# 1. Verify model in TabbyAPI directory
ls -la tabbyAPI/models/ModelName

# 2. Restart TabbyAPI
# Stop and restart TabbyAPI process

# 3. Check TabbyAPI can see model
curl http://localhost:5000/v1/models

# 4. Refresh Gantry admin page
# Hard refresh: Ctrl+Shift+R (or Cmd+Shift+R)
```

### GPU Memory Errors

**Error:** "CUDA out of memory"

**Causes:**

- Model too large for available VRAM
- Previous model not fully unloaded
- Memory leak

**Solutions:**

```bash
# 1. Unload current model first
curl -X POST http://localhost:5000/v1/model/unload

# 2. Wait 10 seconds for memory to clear

# 3. Load smaller model or lower quantization

# 4. If persistent, restart TabbyAPI
```

**VRAM requirements:**

| Model Size | Q4 VRAM | Q8 VRAM |
|------------|---------|---------|
| 3B | 3 GB | 5 GB |
| 7B | 5 GB | 8 GB |
| 13B | 10 GB | 16 GB |
| 30B | 20 GB | 32 GB |
| 70B | 40 GB | 70 GB |

---

## API Usage

### Switch Model via API

**Endpoint:** `POST /api/admin/models/switch`

**Headers:**

```text
Cookie: session_id=<admin-session>
Content-Type: application/json
```

**Body:**

```json
{
  "model_id": "Llama-3.1-8B-Instruct"
}
```

**Example (curl):**

```bash
curl -X POST http://localhost:8000/api/admin/models/switch \
  -H "Cookie: session_id=abc123" \
  -H "Content-Type: application/json" \
  -d '{"model_id": "Llama-3.1-8B-Instruct"}'
```

**Response (success):**

```json
{
  "message": "Model switched to Llama-3.1-8B-Instruct",
  "model_id": "Llama-3.1-8B-Instruct"
}
```

**Response (error):**

```json
{
  "detail": "Failed to switch model. Is TabbyAPI available?"
}
```

### List Models via API

**Endpoint:** `GET /api/admin/models`

**Example:**

```bash
curl http://localhost:8000/api/admin/models \
  -H "Cookie: session_id=abc123"
```

**Response:**

```json
{
  "models": [
    {
      "id": "Qwen2.5-Coder-7B-Instruct",
      "name": "Qwen2.5-Coder-7B-Instruct",
      "active": true
    },
    {
      "id": "Llama-3.1-8B-Instruct",
      "name": "Llama-3.1-8B-Instruct",
      "active": false
    }
  ]
}
```

### Unload Model via API

**Endpoint:** `POST /api/admin/models/unload`

**Example:**

```bash
curl -X POST http://localhost:8000/api/admin/models/unload \
  -H "Cookie: session_id=abc123"
```

**Response:**

```json
{
  "message": "Model unloaded successfully"
}
```

---

## Best Practices

### Naming Conventions

**Model directory names:**

- Use descriptive names: `Qwen2.5-Coder-7B-Instruct-Q5`
- Include version: `Llama-3.1-8B-Instruct`
- Include quantization: `Mistral-7B-Q5_K_M`

**Avoid:**

- Generic names: `model1`, `llm`, `test`
- Special characters: `Llama-3.1 (8B)` → `Llama-3.1-8B`
- Spaces: `My Model` → `My-Model`

### Testing New Models

**Before switching in production:**

1. **Load model in TabbyAPI** manually
2. **Test inference** with curl:

```bash
curl http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "new-model",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
```

3. **Verify response quality**
4. **Check performance** (tokens/sec)
5. **Switch in Gantry** if satisfied

### Model Lifecycle

**Recommended workflow:**

```text
1. Download model → Test locally
2. Add to TabbyAPI → Verify detection
3. Switch in Gantry → Test with users
4. Monitor performance → Collect feedback
5. Keep or remove → Based on results
```

### Backup Strategy

**Before major model changes:**

```bash
# Backup model list
curl http://localhost:5000/v1/models > models-backup.json

# Backup TabbyAPI config
cp tabbyAPI/config.yml config.yml.backup
```

---

## Next Steps

- **[Admin Dashboard](Admin-Dashboard)** - Full admin control plane guide
- **[Configuration](Configuration)** - Environment variable tuning
- **[Production Checklist](Production-Checklist)** - Production deployment

---

**[← Back to Home](Home)** | **[Docker Deployment →](Docker-Deployment)**
