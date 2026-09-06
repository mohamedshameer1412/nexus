'use client';

import { useState, useEffect, useRef } from 'react';
import * as faceapi from 'face-api.js';

export default function FaceDetectionTest() {
    const [modelsLoaded, setModelsLoaded] = useState(false);
    const [faceDetected, setFaceDetected] = useState(false);
    const videoRef = useRef(null);

    useEffect(() => {
        loadModels();
    }, []);

    const loadModels = async () => {
        try {
            const MODEL_URL = '/models'; // We'll need to add models to public folder
            await faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL);
            setModelsLoaded(true);
            console.log('Face detection models loaded');
        } catch (err) {
            console.error('Failed to load models:', err);
        }
    };

    const startCamera = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                startFaceDetection();
            }
        } catch (err) {
            console.error('Camera error:', err);
        }
    };

    const startFaceDetection = () => {
        setInterval(async () => {
            if (videoRef.current && modelsLoaded) {
                const detections = await faceapi.detectSingleFace(
                    videoRef.current,
                    new faceapi.TinyFaceDetectorOptions()
                );
                setFaceDetected(!!detections);
            }
        }, 1000);
    };

    return (
        <div className="p-8">
            <h1>Face Detection Test</h1>
            <p>Models Loaded: {modelsLoaded ? 'Yes' : 'No'}</p>
            <p>Face Detected: {faceDetected ? 'Yes' : 'No'}</p>
            <button onClick={startCamera} className="px-4 py-2 bg-blue-500 text-white rounded">
                Start Camera
            </button>
            <video ref={videoRef} autoPlay muted width="640" height="480" className="mt-4" />
        </div>
    );
}
