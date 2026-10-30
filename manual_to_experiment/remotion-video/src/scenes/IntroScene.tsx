import { AbsoluteFill, Img, useCurrentFrame, interpolate } from "remotion";
import { AnimatedSubtitle } from "../components/AnimatedSubtitle";
import { KenBurnsImage } from "../components/KenBurnsImage";

interface IntroSceneProps {
  narration: string;
  visualHint: string;
  section: string;
  durationFrames: number;
  imageFile: string;
}

export const IntroScene: React.FC<IntroSceneProps> = ({
  narration,
  durationFrames,
  imageFile,
}) => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateRight: "clamp",
  });

  const titleY = interpolate(frame, [0, 30], [40, 0], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill>
      <KenBurnsImage src={imageFile} durationFrames={durationFrames} />

      {/* Dark overlay for text readability */}
      <AbsoluteFill
        style={{
          background: "linear-gradient(transparent 40%, rgba(0,0,0,0.8) 100%)",
        }}
      />

      {/* Subtitle at bottom */}
      <AnimatedSubtitle text={narration} durationFrames={durationFrames} />
    </AbsoluteFill>
  );
};
