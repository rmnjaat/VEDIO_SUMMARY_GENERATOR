import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { AnimatedSubtitle } from "../components/AnimatedSubtitle";
import { KenBurnsImage } from "../components/KenBurnsImage";

interface OutroSceneProps {
  narration: string;
  visualHint: string;
  section: string;
  durationFrames: number;
  imageFile: string;
}

export const OutroScene: React.FC<OutroSceneProps> = ({
  narration,
  durationFrames,
  imageFile,
}) => {
  const frame = useCurrentFrame();

  const fadeOut = interpolate(
    frame,
    [durationFrames - 45, durationFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ opacity: fadeOut }}>
      <KenBurnsImage src={imageFile} durationFrames={durationFrames} />

      {/* Dark overlay */}
      <AbsoluteFill
        style={{
          background: "linear-gradient(transparent 30%, rgba(0,0,0,0.85) 100%)",
        }}
      />

      {/* Subtitle */}
      <AnimatedSubtitle text={narration} durationFrames={durationFrames} />
    </AbsoluteFill>
  );
};
