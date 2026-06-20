# Login Showcase Images

Place future login/register background images in this folder, then add them to `manifest.json` so the auth page can pick them up for random selection and rotation.

Recommended:
- landscape images
- 1600px+ width
- aspect ratio near 16:10, 3:2, or 16:9
- webp, jpg, png, or avif

Example:
```json
{
  "scenes": [
    {
      "id": "work-01",
      "image": "/auth/showcase/work-01.webp",
      "preview": "/auth/showcase/work-01-blur.webp",
      "poster": "",
      "label": "Work 01"
    }
  ]
}
```

`preview` and `poster` are optional. If `manifest.json` is empty, the page keeps using the current built-in 2Bis image.
