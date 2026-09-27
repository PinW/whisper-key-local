# WinML vs DirectML: Current State (March 2026)

## 1. Is DirectML Deprecated?

**Not formally deprecated, but effectively superseded.** DirectML is in "maintenance mode" / "sustained engineering."

- The [DirectML GitHub repo](https://github.com/microsoft/DirectML) banner now reads: "DirectML is in maintenance mode"
- DirectML will remain a system DLL and ship with future Windows versions
- It will receive **security and compliance fixes only** -- no new features or performance improvements
- A [former DirectML developer confirmed](https://github.com/microsoft/onnxruntime/issues/23783) the entire DML team was "reshuffled elsewhere" and described it as "dead"
- Microsoft has not published a formal deprecation timeline or EOL date

**Bottom line:** DirectML is not going away (it's baked into Windows), but it is frozen. All new development goes to Windows ML.

## 2. What is Windows ML?

Windows ML (also called "Windows ML 2.0") is Microsoft's successor runtime for on-device ML inference on Windows. [Announced at Build 2025](https://blogs.windows.com/windowsdeveloper/2025/05/19/introducing-windows-ml-the-future-of-machine-learning-development-on-windows/), [GA in September 2025](https://blogs.windows.com/windowsdeveloper/2025/09/23/windows-ml-is-generally-available-empowering-developers-to-scale-local-ai-across-windows-devices/).

### Relationship to DirectML

- Windows ML is described as "an evolution of DirectML" -- it builds on DML's foundations
- It is NOT a thin wrapper around DirectML; it is a higher-level framework
- DirectML (the DX12-based compute layer) still exists as one of Windows ML's **built-in execution providers**
- Windows ML adds an **execution provider catalog** system that dynamically discovers, downloads, and registers vendor-optimized EPs based on detected hardware

### Architecture

Windows ML sits on top of ONNX Runtime and provides:
- A shared Windows-wide copy of ONNX Runtime
- Dynamic EP discovery and download via `ExecutionProviderCatalog` APIs
- Automatic hardware detection and optimal EP selection
- EP updates delivered via Windows Update

### Built-in EPs (ship with Windows ML)

| EP | Hardware |
|----|----------|
| CPU | All |
| DirectML | Any DirectX 12-capable GPU |

### Downloadable EPs (Win11 24H2+, delivered via Windows Update)

| EP Name | Vendor | Hardware |
|---------|--------|----------|
| MIGraphXExecutionProvider | AMD | AMD GPUs (specific driver required) |
| VitisAIExecutionProvider | AMD | AMD NPU/GPU/CPU (Ryzen AI) |
| NvTensorRtRtxExecutionProvider | NVIDIA | GeForce RTX 30XX+ |
| OpenVINOExecutionProvider | Intel | Intel 11th Gen+ CPU/GPU/NPU |
| QNNExecutionProvider | Qualcomm | Snapdragon X Elite/Plus NPU |

Source: [Supported execution providers in Windows ML](https://learn.microsoft.com/en-us/windows/ai/new-windows-ml/supported-execution-providers)

## 3. Windows ML Status

### Production Readiness

- **GA since September 2025** -- Microsoft says it is ready for production use
- Requires **Windows App SDK 1.8.1+**
- EP auto-download requires **Windows 11 version 24H2 (build 26100)** or later; some features require **25H2**
- The built-in DirectML EP works on older Windows versions

### Python Support

**Yes, Python is supported** but the setup is more complex than `pip install onnxruntime-directml`:

```powershell
pip install wasdk-Microsoft.Windows.AI.MachineLearning[all] wasdk-Microsoft.Windows.ApplicationModel.DynamicDependency.Bootstrap onnxruntime-windowsml
```

Key constraints:
- Python 3.10 to 3.13, x64 and ARM64
- Python must NOT be from Microsoft Store (use python.org or winget)
- Uses [pywinrt](https://github.com/pywinrt/pywinrt) bindings for Windows App SDK
- Only works for unpackaged apps (uses Dynamic Dependency API)
- Setup code is significantly more verbose than DirectML (singleton class, EP registration, etc.)

### onnxruntime-windowsml Package

- Latest stable: **1.23.3** (released Feb 11, 2026)
- Note: version 1.24.0 was released then **yanked** ("unintended release")
- Lags behind `onnxruntime-directml` which is at **1.24.3** (March 5, 2026)
- Status: Production/Stable on PyPI

### Does it work with ONNX Runtime?

Yes -- Windows ML IS an ONNX Runtime distribution. It provides the same ORT APIs. The `onnxruntime-windowsml` package is a special build of ONNX Runtime that includes WinML's EP catalog capabilities.

## 4. onnxruntime-directml Package Status

| Detail | Value |
|--------|-------|
| Latest version | **1.24.3** |
| Release date | **March 5, 2026** |
| Python support | 3.11, 3.12, 3.13, 3.14 |
| Deprecation notice | **None** |
| PyPI status | "5 - Production/Stable" |
| Maintenance | Still receiving regular updates in lockstep with onnxruntime releases |

The package is **not deprecated** and is still being actively published. The ONNX Runtime docs note that DirectML is in "sustained engineering" but the package continues to ship.

## 5. What Should Developers Use TODAY?

### For GPU-accelerated ML on Windows with AMD GPUs

**Recommendation depends on your constraints:**

#### Use `onnxruntime-directml` if:
- You need to support Windows 10
- You need to support older Windows 11 versions (pre-24H2)
- You want the simplest setup (`pip install onnxruntime-directml`)
- You need broad AMD GPU support (any DirectX 12-capable GPU: GCN, RDNA 1/2/3/4)
- You're using it from Python and want minimal boilerplate
- You need the latest ONNX Runtime version (currently 1.24.3 vs WinML's 1.23.3)

#### Use Windows ML (`onnxruntime-windowsml`) if:
- You're targeting Windows 11 24H2+ only
- You want automatic EP selection (MIGraphX for AMD GPU, TensorRT for NVIDIA, etc.)
- You want vendor-optimized EPs delivered and updated via Windows Update
- You're building a C#/C++ Windows App SDK application
- You want future-proof alignment with Microsoft's direction

#### Use ROCm/MIGraphX directly if:
- You're on Linux with AMD GPUs
- You need maximum AMD GPU performance

### For this project (whisper-key-local)

`onnxruntime-directml` remains the pragmatic choice because:
1. It supports Windows 10 and all Windows 11 versions
2. It supports ALL DirectX 12 AMD GPUs including RDNA 1 (RX 5700 XT)
3. Simple pip install, no Windows App SDK dependency
4. Still actively maintained and receiving updates
5. The WinML Python story is immature (complex setup, version lag, yanked releases)

## 6. Does WinML Support AMD GPUs?

**Yes**, through multiple paths:

| Path | AMD Hardware | Notes |
|------|-------------|-------|
| DirectML (built-in EP) | Any DX12 GPU (GCN, RDNA 1-4) | Same broad support as standalone DirectML |
| MIGraphX EP (downloadable) | AMD GPUs with specific driver (25.10.13.09) | Not supported for GenAI scenarios |
| VitisAI EP (downloadable) | Ryzen AI NPU/GPU/CPU | Requires specific Adrenalin driver range |

AMD has [published articles](https://www.amd.com/en/blogs/2025/empowering-ai-pcs-with-amd-and-windowsml.html) confirming full Windows ML support for Ryzen AI products.

**Important nuance:** The vendor-optimized EPs (MIGraphX, VitisAI) have **specific driver version requirements** and may not support all AMD GPU generations. The DirectML built-in EP remains the broadest compatibility option for AMD GPUs within Windows ML.

## Summary Table

| Aspect | DirectML | Windows ML |
|--------|----------|------------|
| Status | Maintenance mode | GA (Sept 2025) |
| New features | No | Yes |
| Python package | `onnxruntime-directml` (1.24.3) | `onnxruntime-windowsml` (1.23.3) |
| Setup complexity | `pip install` one package | 3 packages + boilerplate code |
| Windows 10 | Yes | No |
| Windows 11 pre-24H2 | Yes | Partial (no EP auto-download) |
| AMD GPU breadth | All DX12 GPUs | All DX12 (via built-in DML) + vendor EPs |
| Performance | Baseline | Up to 50% faster (vendor-optimized EPs) |
| Future investment | None | Active development |

---

*Researched 2026-03-17*

Sources:
- [DirectML GitHub (maintenance mode notice)](https://github.com/microsoft/DirectML)
- [Is DML being deprecated? - onnxruntime#23783](https://github.com/microsoft/onnxruntime/issues/23783)
- [Introducing Windows ML (Build 2025 blog)](https://blogs.windows.com/windowsdeveloper/2025/05/19/introducing-windows-ml-the-future-of-machine-learning-development-on-windows/)
- [Windows ML GA announcement (Sept 2025)](https://blogs.windows.com/windowsdeveloper/2025/09/23/windows-ml-is-generally-available-empowering-developers-to-scale-local-ai-across-windows-devices/)
- [Windows ML supported execution providers](https://learn.microsoft.com/en-us/windows/ai/new-windows-ml/supported-execution-providers)
- [Get started with Windows ML](https://learn.microsoft.com/en-us/windows/ai/new-windows-ml/get-started)
- [onnxruntime-directml on PyPI](https://pypi.org/project/onnxruntime-directml/)
- [onnxruntime-windowsml on PyPI](https://pypi.org/project/onnxruntime-windowsml/)
- [ONNX Runtime DirectML EP docs](https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html)
- [AMD + Windows ML blog](https://www.amd.com/en/blogs/2025/empowering-ai-pcs-with-amd-and-windowsml.html)
- [Microsoft Targets AI 'Holy Grail' With Windows ML 2.0 (The New Stack)](https://thenewstack.io/microsoft-targets-ai-holy-grail-with-windows-ml-2-0/)
