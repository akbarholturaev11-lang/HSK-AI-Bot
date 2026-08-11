# HSK AI Desktop — Third-Party Notices

HSK AI Desktop can use the following optional local-AI components. The model is
downloaded only after the user explicitly starts AI Pack installation. The
llama.cpp runtime is bundled with release installers.

## Qwen3-4B-GGUF

- Project: Qwen3-4B-GGUF
- Repository: <https://huggingface.co/Qwen/Qwen3-4B-GGUF>
- Pinned revision: `a9a60d009fa7ff9606305047c2bf77ac25dbec49`
- Pinned file: `Qwen3-4B-Q4_K_M.gguf`
- License: Apache License 2.0

The complete Apache License 2.0 text is bundled as
`licenses/LICENSE-QWEN-APACHE-2.0.txt`.

## llama.cpp

- Project: llama.cpp
- Repository: <https://github.com/ggml-org/llama.cpp>
- Pinned release: `b10223`
- Pinned commit: `11924d4c17abc27383376a1ac6a24fa3e36c1c0c`
- License: MIT

The complete MIT license text is bundled as
`licenses/LICENSE-LLAMA.CPP-MIT.txt`.

## Hanzi Writer

- Project: Hanzi Writer
- Repository: <https://github.com/chanind/hanzi-writer>
- Vendored version: `3.7.3`
- License: MIT

Vendored as `ui/vendor/hanzi-writer.js` so the dictionary can animate stroke
order offline. Character data is bundled in `ui/data/strokes.js`; the upstream
CDN loader is never used.

The complete MIT license text is bundled as
`licenses/LICENSE-HANZI-WRITER-MIT.txt`.

## Giant Panda Photo

- Asset: `ui/assets/panda-real.webp`
- Source: <https://commons.wikimedia.org/wiki/File:Giant_panda_(1).jpg>
- Author: Stolz Gary M, U.S. Fish and Wildlife Service
- License: Public domain

The source photo was cropped, resized and compressed to WebP for desktop UI
mascot use.

The upstream projects are not affiliated with and do not endorse HSK AI.
