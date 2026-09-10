# @hyperframes/producer

Full HTML-to-video rendering pipeline: capture frames with Chrome's BeginFrame API, encode with FFmpeg, mix audio — all in one call.

## Install

```bash
npm install @hyperframes/producer
```

**Requirements:** Node.js >= 22, Chrome/Chromium (auto-downloaded), FFmpeg

## Usage

### Render a video

```typescript
import { createRenderJob, executeRenderJob } from "@hyperframes/producer";

const job = createRenderJob({
  inputPath: "./my-composition.html",
  outputPath: "./output.mp4",
  width: 1920,
  height: 1080,
  fps: 30,
});

const result = await executeRenderJob(job, (progress) => {
  console.log(`${Math.round(progress.percent * 100)}%`);
});

console.log(result.outputPath); // ./output.mp4
```

### Run as an HTTP server

The producer can also run as a render server, accepting render requests over HTTP:

```typescript
import { startServer } from "@hyperframes/producer";

await startServer({ port: 8080 });
// POST /render with a RenderConfig body
```

### Configuration

`RenderConfig` controls the render pipeline:

| Option       | Default      | Description                                        |
| ------------ | ------------ | -------------------------------------------------- |
| `inputPath`  | —            | Path to the HTML composition                       |
| `outputPath` | —            | Output video file path                             |
| `width`      | 1920         | Frame width in pixels                              |
| `height`     | 1080         | Frame height in pixels                             |
| `fps`        | 30           | Frames per second (24, 30, or 60)                  |
| `quality`    | `"standard"` | Encoder preset (`"draft"`, `"standard"`, `"high"`) |

## How it works

1. **Serve** — spins up a local file server for the HTML composition
2. **Capture** — opens the page in headless Chrome, seeks frame-by-frame via `HeadlessExperimental.beginFrame`, captures screenshots
3. **Encode** — pipes frames through FFmpeg (with GPU encoder detection and chunked concat)
4. **Mix** — extracts `<audio>` elements and mixes them into the final video
5. **Finalize** — applies faststart for streaming-friendly MP4

## Documentation

Full documentation: [hyperframes.heygen.com/packages/producer](https://hyperframes.heygen.com/packages/producer)

## Related packages

- [`@hyperframes/core`](../core) — types, parsers, frame adapters
- [`@hyperframes/engine`](../engine) — lower-level capture and encode primitives
- [`hyperframes`](../cli) — CLI
