# PRD: MeetingNote Phase 1

## Product Goal

Build a Windows 11 offline meeting text workstation that converts audio/video into transcripts, supports full-document Chinese-English translation, generates meeting summaries, and exports reusable files.

## Phase 1 Priorities

1. Offline transcription
2. Full-document translation, not sentence-by-sentence translation
3. Meeting summaries
4. Local model management
5. History and export

## Explicitly Not Included in Phase 1

Self-media content generation is not included in Phase 1. No voiceover script, social-media article, video script, platform template, or auto-publishing feature will be built in the first release.

## Core Workflow

```text
Audio/Video -> Preprocess -> Offline ASR -> Edit Transcript -> Full Translation -> Summary -> Export/Archive
```

## Translation Requirement

Translation must be presented as a complete document-level translation. Internally, long transcripts may be split for context limits, but the system must preserve global terminology, speaker context, tone, and document coherence.

## Model Strategy

The application must support replaceable local models. Phase 1 should prioritize GGUF-based local LLMs such as Qwen3 for summary and translation. Gemma 4 and TranslateGemma should be treated as optional future-compatible providers after local inference compatibility is verified.
