"use client";
import { useState } from "react";
import { Camera, CameraOff } from "lucide-react";
import { useFaceWatch } from "@/lib/use-face-watch";
import { Button } from "@/components/ui/primitives";

const noop = () => {};

/** Lets the student see, before an assessment, what the camera check sees. Nothing is sent or saved. */
export function CameraCheck() {
  const [on, setOn] = useState(false);
  const face = useFaceWatch({ on, onViolation: noop });
  const text = face.status === "error" ? face.problem || "The camera could not start."
    : face.status !== "ready" ? "Starting the camera…"
    : face.faces === 1 ? "One face detected. This is what an assessment needs."
    : face.faces === 0 ? "No face detected. Move into the light and face the camera."
    : "More than one face detected. Only you should be in view.";
  const good = on && face.status === "ready" && face.faces === 1;
  return (
    <div className="mt-3">
      <Button type="button" variant="secondary" size="sm" onClick={() => setOn((v) => !v)} aria-pressed={on}>
        {on ? <CameraOff className="h-4 w-4" aria-hidden="true" /> : <Camera className="h-4 w-4" aria-hidden="true" />} {on ? "Stop the camera test" : "Test my camera"}
      </Button>
      {on && (
        <div className="mt-2 flex items-center gap-3">
          <video ref={face.videoRef} muted playsInline aria-hidden="true" className="aspect-[4/3] w-40 -scale-x-100 rounded-lg border border-border object-cover shadow-card" />
          <p role="status" aria-live="polite" className={`text-sm font-semibold ${good ? "text-strong" : "text-weak"}`}>{text}</p>
        </div>
      )}
    </div>
  );
}
