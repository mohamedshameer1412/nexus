# Face Detection Models Setup

## Download Required Models

The face-api.js library requires pre-trained models. Download them from:
https://github.com/justadudewhohacks/face-api.js/tree/master/weights

### Required Models for Tiny Face Detector:
1. `tiny_face_detector_model-weights_manifest.json`
2. `tiny_face_detector_model-shard1`

### Steps:
1. Download the above files
2. Place them in `frontend/public/models/` directory
3. The app will load them from `/models/` path

### Alternative (CDN):
You can also load models from CDN:
```javascript
const MODEL_URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api/model';
```

## Current Setup:
- Models directory: `frontend/public/models/`
- Loading path in code: `/models/`
