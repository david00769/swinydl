# Third-Party Notices

This repository's [MIT license](LICENSE) applies to the source code in this repository unless a file states otherwise.

Separately staged model artifacts under `vendor/` are third-party assets and are not covered by the repository MIT license. Those assets are downloaded locally with `swinydl bootstrap-models` and remain subject to their upstream licenses and terms.

## Codebase Lineage

- Original Echo360 downloader project lineage:
  - repository history derived from the earlier `swinydl` project by Tin Lai (`@soraxas`)
  - the original MIT notice is preserved in [LICENSE](LICENSE)

## Runtime Dependencies

The project depends on third-party libraries installed through Python packaging, including:

- `requests`
- `selenium`
- `truststore`
- `yt-dlp`
- `huggingface-hub`

Those libraries are distributed under their own licenses through the Python ecosystem. See the package metadata in [pyproject.toml](pyproject.toml) and the resolved versions in [uv.lock](uv.lock).

## Staged CoreML Model Bundles

### ASR Bundle

- Preferred staged CoreML source:
  - [FluidInference/parakeet-tdt-0.6b-v3-coreml](https://huggingface.co/FluidInference/parakeet-tdt-0.6b-v3-coreml)
- Canonical upstream base model:
  - [nvidia/parakeet-tdt-0.6b-v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)
- Intended local staging path:
  - `vendor/parakeet-tdt-0.6b-v3-coreml`

License note:
- Check the current Hugging Face model card before redistributing or repackaging the model bundle.

### Speaker Diarization Bundle

- Preferred staged CoreML source:
  - [FluidInference/speaker-diarization-coreml](https://huggingface.co/FluidInference/speaker-diarization-coreml)
- Canonical upstream pipeline:
  - [pyannote/speaker-diarization-community-1](https://huggingface.co/pyannote/speaker-diarization-community-1)
- Related upstream components:
  - [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)
  - [pyannote/wespeaker-voxceleb-resnet34-LM](https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM)
- Intended local staging path:
  - `vendor/speaker-diarization-coreml`

License note:
- The current upstream diarization pipeline is published under `CC-BY-4.0` on its model card. Attribution and any other applicable upstream terms should be preserved when the bundle is used or redistributed.

## Distribution Guidance

- Do not assume the repository MIT license applies to downloaded model bundles.
- Do not commit or redistribute staged `vendor/` model directories unless you have verified the upstream license terms and any attribution requirements.
- When in doubt, treat the public upstream model cards as the authoritative source for current model-license information.
