'use client';

import { useState, useEffect, useRef } from 'react';
import { proctoringAPI } from '@/lib/api';
import { Camera, AlertTriangle, EyeOff } from 'lucide-react';

// Dynamic import for face-api.js (client-side only)
let faceapi = null;

if (typeof window !== 'undefined') {
    import('face-api.js').then(module => {
        faceapi = module;
    });
}

export default function ProctoringMonitor({ sessionId, onPermissionStatus, onViolation }) {
    const videoRef = useRef(null);
    const [stream, setStream] = useState(null);
    const [permissionGranted, setPermissionGranted] = useState(false);
    const [error, setError] = useState(null);
    const [warnings, setWarnings] = useState([]);
    const [tabSwitchCount, setTabSwitchCount] = useState(0);

    // Face detection state
    const [faceDetector, setFaceDetector] = useState(null);
    const [noFaceStartTime, setNoFaceStartTime] = useState(null);
    const [faceDetectionActive, setFaceDetectionActive] = useState(false);
    const detectionIntervalRef = useRef(null);

    // removed parent status change
    useEffect(() => {
        if (onPermissionStatus) {
            onPermissionStatus(permissionGranted);
        }
    }, [permissionGranted, onPermissionStatus]);

    // 1. Request Camera AND Microphone Access
    useEffect(() => {
        let mounted = true;

        const startCamera = async () => {
            try {
                // Request BOTH camera and microphone - this will trigger browser permission prompts
                const mediaStream = await navigator.mediaDevices.getUserMedia({
                    video: true,
                    audio: true  // Request microphone as well
                });

                if (mounted) {
                    setStream(mediaStream);
                    setPermissionGranted(true);
                    console.log('✅ Camera/Microphone access granted');
                }
            } catch (err) {
                console.error("Camera/Microphone Error:", err);
                if (mounted) {
                    let errorMessage = "Camera and microphone access required for proctoring.";

                    if (err.name === 'NotFoundError') {
                        errorMessage = "No camera or microphone found. Please connect these devices to continue.";
                    } else if (err.name === 'NotAllowedError') {
                        errorMessage = "Permission denied. Please click the lock icon in your browser's address bar and allow camera and microphone access.";
                    } else if (err.name === 'NotReadableError') {
                        errorMessage = "Camera or microphone is already in use by another application. Please close other apps and refresh.";
                    }

                    setError(errorMessage);
                    setPermissionGranted(false);
                }
            }
        };

        startCamera();

        return () => {
            mounted = false;
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
        };
    }, []);

    // Attach stream to video element when ready
    useEffect(() => {
        let mounted = true;
        
        if (stream && videoRef.current && permissionGranted) {
            const video = videoRef.current;
            
            // Only attach if not already attached to avoid interruptions
            if (video.srcObject !== stream) {
                console.log('📹 Attaching stream to video element...');
                video.srcObject = stream;
            }

            const playVideo = async () => {
                try {
                    if (video.paused && mounted) {
                        await video.play();
                        console.log('✅ Video playing successfully!');
                    }
                } catch (err) {
                    // Ignore AbortError caused by rapid state changes
                    if (err.name !== 'AbortError') {
                        console.error('❌ Video play failed:', err);
                    }
                }
            };

            playVideo();
        }
        
        return () => { mounted = false; };
    }, [stream, permissionGranted]);

    // Initialize Face Detection Model
    useEffect(() => {
        if (!permissionGranted || !faceapi) return;

        const initFaceDetection = async () => {
            try {
                console.log('🎯 Initializing face detection...');

                // Load models from CDN
                const MODEL_URL = '/models'; // We'll need to add model files to public folder
                await faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL);

                setFaceDetectionActive(true);
                console.log('✅ Face detection initialized');
            } catch (err) {
                console.error('Face detection initialization failed:', err);
                console.log('⚠️ Continuing without face detection');
            }
        };

        // Delay initialization to ensure video is ready
        setTimeout(initFaceDetection, 2000);
    }, [permissionGranted]);

    // Face Detection Loop
    useEffect(() => {
        if (!faceDetectionActive || !videoRef.current || !faceapi) return;

        const detectFaces = async () => {
            try {
                const video = videoRef.current;
                if (!video || video.readyState !== 4) return; // Wait for video to be ready

                // Detect faces using tiny face detector (faster)
                const detections = await faceapi.detectAllFaces(
                    video,
                    new faceapi.TinyFaceDetectorOptions()
                );

                const now = Date.now();
                const faceCount = detections.length;

                if (faceCount === 0) {
                    // No face detected
                    if (!noFaceStartTime) {
                        setNoFaceStartTime(now);
                    } else {
                        const duration = (now - noFaceStartTime) / 1000; // seconds

                        if (duration >= 5 && duration < 6) {
                            // 5 second warning
                            addWarning('⚠️ No face detected! Please look at the camera.');
                            logSuspiciousEvent('no_face_detected', { duration: Math.floor(duration) });
                        } else if (duration >= 10) {
                            // 10+ second violation
                            logSuspiciousEvent('looking_away_violation', { duration: Math.floor(duration) });
                            if (onViolation) {
                                onViolation('looking_away', Math.floor(duration / 10));
                            }
                            addWarning(`🚨 Looking away for ${Math.floor(duration)}s - Violation logged!`);
                        }
                    }
                } else if (faceCount > 1) {
                    // Multiple faces detected
                    logSuspiciousEvent('multiple_faces', { count: faceCount });
                    if (onViolation) {
                        onViolation('multiple_faces', faceCount);
                    }
                    addWarning(`🚨 Multiple faces detected (${faceCount})! Only one person allowed.`);
                    setNoFaceStartTime(null);
                } else {
                    // Exactly 1 face - all good
                    setNoFaceStartTime(null);
                }
            } catch (err) {
                console.error('Face detection error:', err);
            }
        };

        // Run detection every 1 second
        detectionIntervalRef.current = setInterval(detectFaces, 1000);

        return () => {
            if (detectionIntervalRef.current) {
                clearInterval(detectionIntervalRef.current);
            }
        };
    }, [faceDetectionActive, noFaceStartTime]);

    // 2. Monitor Tab Switching
    useEffect(() => {
        if (!sessionId) return;

        const handleVisibilityChange = () => {
            if (document.hidden) {
                logSuspiciousEvent('tab_switch', { reason: 'User switched tab or minimized window' });
                addWarning("Tab switch detected! This event has been logged.");
            }
        };

        const handleBlur = () => {
            // Window lost focus (could be alt-tab, or clicking another app)
            // Some browsers trigger this on tab switch too.
            // We use a small timeout to differentiate/debounce if needed, but for strict proctoring, logging blur is okay.
            // However, visibilityState is more reliable for "Hidden".
            // Blur might happen if they click an extension popup.
            // Let's stick to visibilityChange for substantial violations.
            // But 'blur' catches side-by-side windows focus switch.
            // We can log it as 'looking_away' or 'focus_lost'.
            logSuspiciousEvent('window_blur', { reason: 'Window lost focus' });
        };

        document.addEventListener("visibilitychange", handleVisibilityChange);
        window.addEventListener("blur", handleBlur);

        return () => {
            document.removeEventListener("visibilitychange", handleVisibilityChange);
            window.removeEventListener("blur", handleBlur);
        };
    }, [sessionId]);

    const logSuspiciousEvent = async (type, details) => {
        try {
            // Capture Snapshot if needed (optional implementation using canvas)
            let evidence = null;
            if (videoRef.current && permissionGranted) {
                const canvas = document.createElement('canvas');
                canvas.width = videoRef.current.videoWidth;
                canvas.height = videoRef.current.videoHeight;
                canvas.getContext('2d').drawImage(videoRef.current, 0, 0);
                // Convert to blob
                // evidence = await new Promise(r => canvas.toBlob(r, 'image/jpeg'));
            }

            await proctoringAPI.logEvent({
                session: sessionId,
                event_type: (() => {
                    if (type === 'window_blur') return 'tab_switch';
                    if (type === 'looking_away_violation') return 'looking_away';
                    if (type === 'no_face_detected') return 'face_not_visible';
                    return type;
                })(), // Map to model choices
                details: details,
                // evidence_image: evidence // Sending blob requires more handling, skipping for simple log now
            });
            console.log(`✅ Logged proctoring event: ${type}`);
        } catch (err) {
            console.warn(`⚠️ Failed to log proctoring event (${type}):`, err.message);
            if (err.response) {
                console.warn('Server response:', err.response.data);
            }
            // Don't break the app if logging fails
        }
    };

    const addWarning = (msg) => {
        const id = Date.now();
        setWarnings(prev => [...prev, { id, msg }]);
        setTimeout(() => {
            setWarnings(prev => prev.filter(w => w.id !== id));
        }, 5000);
    };

    if (error) {
        return (
            <div className="bg-red-500/10 border border-red-500/50 p-4 rounded-lg text-red-500 flex items-center gap-2">
                <p>{error}</p>
            </div>
        );
    }

    return (
        <div className="fixed bottom-4 right-4 z-50 flex flex-col items-end gap-2 pointer-events-none">
            {/* Warnings Container */}
            <div className="flex flex-col gap-2 items-end mb-2">
                {warnings.map(w => (
                    <div key={w.id} className="bg-yellow-500 text-black px-4 py-2 rounded-lg shadow-lg font-bold animate-in slide-in-from-right flex items-center gap-2">
                        <AlertTriangle className="w-5 h-5" />
                        {w.msg}
                    </div>
                ))}
            </div>

            {/* Webcam Feed */}
            {permissionGranted && (
                <div className="relative w-48 rounded-lg overflow-hidden border-2 border-primary shadow-2xl bg-black pointer-events-auto">
                    <video
                        ref={videoRef}
                        autoPlay
                        muted
                        playsInline
                        className="w-full min-h-[144px] object-cover transform scale-x-[-1]" 
                    />
                    <div className="absolute top-2 left-2">
                        <div className="flex items-center gap-1 bg-black/50 px-2 py-1 rounded text-xs text-white font-mono">
                            <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
                            REC
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
