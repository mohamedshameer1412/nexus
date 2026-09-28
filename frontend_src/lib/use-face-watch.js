"use client";
import { useEffect, useRef, useState } from "react";

// Face check for an Assessment. The camera picture is looked at inside this browser tab only: it is never uploaded or saved.
// Rules: no face for NO_FACE_MS, or more than one face for MANY_MS, ends the assessment. The first GRACE_MS are ignored while the camera warms up.
const E2E = process.env.NEXT_PUBLIC_E2E === "1";
const override = (key, fallback) => {
  if (!E2E) return fallback; // the override exists only in the test build
  try { return Number(localStorage.getItem(key)) || fallback; } catch { return fallback; }
};

export function useFaceWatch({ on, onViolation }) {
  const videoRef = useRef(null);
  const violation = useRef(onViolation);
  violation.current = onViolation;
  const [status, setStatus] = useState("off"); // off | starting | ready | error
  const [faces, setFaces] = useState(null);
  const [secondsLeft, setSecondsLeft] = useState(null); // countdown shown while a rule is close to being broken
  const [problem, setProblem] = useState("");

  useEffect(() => {
    if (!on) return undefined;
    const NO_FACE_MS = override("nexus.test.noFaceMs", 6000);
    const MANY_MS = override("nexus.test.manyFacesMs", 3000);
    const GRACE_MS = override("nexus.test.graceMs", 2500);
    let stopped = false, stream, detector, timer;

    (async () => {
      try {
        setStatus("starting");
        stream = await navigator.mediaDevices.getUserMedia({ video: { width: 320, height: 240, facingMode: "user" }, audio: false });
        if (stopped) return;
        stream.getVideoTracks()[0]?.addEventListener("ended", () => !stopped && violation.current("camera_off"));
        const video = videoRef.current;
        video.srcObject = stream;
        await video.play();
        const { FaceDetector, FilesetResolver } = await import("@mediapipe/tasks-vision");
        const fileset = await FilesetResolver.forVisionTasks("/mediapipe/wasm");
        detector = await FaceDetector.createFromOptions(fileset, {
          baseOptions: { modelAssetPath: "/mediapipe/blaze_face_short_range.tflite" }, runningMode: "VIDEO", minDetectionConfidence: 0.5,
        });
        if (stopped) return;
        setStatus("ready");
        const armedAt = Date.now() + GRACE_MS;
        let noFaceSince = null, manySince = null, okFrames = 0, noFrames = 0, manyFrames = 0;
        const tick = () => {
          if (stopped) return;
          let n;
          try {
            n = detector.detectForVideo(video, performance.now()).detections.length;
          } catch (e) {
            console.error("face check failed:", e); // fail closed: without a working face check the assessment cannot continue
            setProblem("The face check stopped working.");
            return violation.current("camera_off");
          }
          if (E2E) {
            const forced = localStorage.getItem("nexus.test.forceFaces"); // the test camera is a moving pattern: let tests simulate an empty room / two people
            if (forced !== null && forced !== "") n = Number(forced);
          }
          const now = Date.now();
          setFaces(n);
          // A rule counts as "broken" from the first frame that breaks it and is cleared only after about a second (3 frames) of the opposite,
          // so one wrong frame in either direction neither hides an empty room nor ends the assessment.
          okFrames = n === 1 ? okFrames + 1 : 0;
          noFrames = n === 0 ? noFrames + 1 : 0;
          manyFrames = n > 1 ? manyFrames + 1 : 0;
          if (now >= armedAt) {
            if (n === 0) noFaceSince = noFaceSince ?? now; else if (okFrames >= 3 || manyFrames > 0) noFaceSince = null;
            if (n > 1) manySince = manySince ?? now; else if (okFrames >= 3 || noFrames >= 3) manySince = null;
            if (noFaceSince && now - noFaceSince >= NO_FACE_MS) return violation.current("no_face");
            if (manySince && now - manySince >= MANY_MS) return violation.current("multiple_faces");
            setSecondsLeft(noFaceSince ? Math.ceil((NO_FACE_MS - (now - noFaceSince)) / 1000) : manySince ? Math.ceil((MANY_MS - (now - manySince)) / 1000) : null);
          }
          timer = setTimeout(tick, 350);
        };
        tick();
      } catch (e) {
        if (stopped) return;
        setStatus("error");
        setProblem(e?.name === "NotAllowedError" ? "The camera is blocked for this site." : "The camera or face check could not start.");
        violation.current("camera_off");
      }
    })();

    return () => {
      stopped = true;
      clearTimeout(timer);
      try { detector?.close(); } catch {}
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, [on]);

  return { videoRef, status, faces, secondsLeft, problem };
}
