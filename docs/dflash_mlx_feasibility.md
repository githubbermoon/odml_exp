# DFlash / MLX Feasibility Note

As of May 7, 2026, DFlash-style speculative decoding on MLX appears implementable as an experimental research path, but it should not be the default EdgePulse demo path.

Current signals:

- Google announced Gemma 4 MTP drafters and explicitly positioned them for low-latency edge and workstation inference, including LiteRT-LM and MLX support.
- The DFlash paper describes block diffusion drafting for speculative decoding and reports strong acceleration in research settings.
- Public GitHub projects have appeared for DFlash on MLX, including `Aryagm/dflash-mlx`.

Engineering assessment:

- Feasible for a research branch on Apple Silicon.
- Not yet appropriate as the core meetup demo dependency because model compatibility, conversion paths, acceptance-rate tuning, and runtime stability are likely to dominate implementation time.
- EdgePulse should first integrate official Gemma MTP drafter support through LiteRT-LM or MLX where available.
- The current prototype deliberately implements speculative UX behavior, not true DFlash or true speculative decoding internals.

Suggested future branch:

```text
edgepulse/reasoning/mlx_dflash_experimental.py
```

Scope:

- MLX backend adapter
- draft/verify metrics in dashboard
- acceptance-rate telemetry
- fallback to LiteRT-LM when DFlash model assets are unavailable

References:

- Google Gemma 4 MTP announcement: https://blog.google/innovation-and-ai/technology/developers-tools/multi-token-prediction-gemma-4/
- DFlash paper page: https://huggingface.co/papers/2602.06036
- MLX DFlash implementation signal: https://github.com/Aryagm/dflash-mlx
