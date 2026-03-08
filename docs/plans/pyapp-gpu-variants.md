# PyApp GPU Variants Plan

Separate GPU-accelerated builds for pyapp distribution. Depends on core pyapp migration being complete first.

## Steps

- [ ] Research: can CUDA deps (cuDNN, etc.) be pip-installed automatically?
- [ ] Research: publish custom ROCm ctranslate2 wheel to PyPI
- [ ] Determine if we need separate pyapp builds per GPU variant or if one binary can detect and install the right deps
- [ ] Test CUDA variant end-to-end
- [ ] Test ROCm variant end-to-end

## Open Questions

- Single binary with runtime GPU detection vs separate builds per variant?
- How to handle users switching GPUs or driver updates?
- Size impact of bundling CUDA/ROCm deps via pip?
