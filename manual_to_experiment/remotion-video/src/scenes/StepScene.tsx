import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { AnimatedSubtitle } from "../components/AnimatedSubtitle";
import { KenBurnsImage } from "../components/KenBurnsImage";
import { ProgressBar } from "../components/ProgressBar";

interface StepSceneProps {
  narration: string;
  visualHint: string;
  section: string;
  durationFrames: number;
  imageFile: string;
  stepNumber: number;
  totalSteps: number;
  stepIndex: number;
}

export const StepScene: React.FC<StepSceneProps> = ({
  narration,
  section,
  durationFrames,
  imageFile,
  stepNumber,
  totalSteps,
  stepIndex,
}) => {
  const frame = useCurrentFrame();

  const sectionOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill>
      <KenBurnsImage src={imageFile} durationFrames={durationFrames} />

      {/* Dark gradient overlay */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(rgba(0,0,0,0.3) 0%, transparent 30%, transparent 60%, rgba(0,0,0,0.85) 100%)",
        }}
      />

      {/* Section label (top-left) */}
      {section && (
        <div
          style={{
            position: "absolute",
            top: 40,
            left: 60,
            opacity: sectionOpacity,
            color: "#8fa8ff",
            fontSize: 28,
            fontFamily: "Helvetica Neue, Arial, sans-serif",
            fontWeight: 500,
            letterSpacing: 1,
          }}
        >
          {section.toUpperCase()}
        </div>
      )}

      {/* Step counter (top-right) */}
      {stepNumber > 0 && (
        <div
          style={{
            position: "absolute",
            top: 40,
            right: 60,
            color: "#ffffff",
            fontSize: 24,
            fontFamily: "Helvetica Neue, Arial, sans-serif",
            opacity: 0.8,
          }}
        >
          Step {stepNumber} of {totalSteps}
        </div>
      )}

      {/* Progress bar */}
      <ProgressBar current={stepIndex} total={totalSteps} />

      {/* Subtitle */}
      <AnimatedSubtitle text={narration} durationFrames={durationFrames} />
    </AbsoluteFill>
  );
};
