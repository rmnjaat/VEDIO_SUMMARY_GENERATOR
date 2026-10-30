import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { AnimatedSubtitle } from "../components/AnimatedSubtitle";

interface TransitionSceneProps {
  narration: string;
  visualHint: string;
  section: string;
  durationFrames: number;
}

export const TransitionScene: React.FC<TransitionSceneProps> = ({
  narration,
  durationFrames,
}) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 20, durationFrames - 20, durationFrames], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const lineWidth = interpolate(frame, [0, 40], [0, 400], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#1a1a2e",
        justifyContent: "center",
        alignItems: "center",
        opacity,
      }}
    >
      {/* Animated accent line */}
      <div
        style={{
          width: lineWidth,
          height: 3,
          backgroundColor: "#638cff",
          marginBottom: 40,
          borderRadius: 2,
        }}
      />

      {/* Subtitle */}
      <AnimatedSubtitle text={narration} durationFrames={durationFrames} />
    </AbsoluteFill>
  );
};
