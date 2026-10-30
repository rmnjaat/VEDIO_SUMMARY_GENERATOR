import { AbsoluteFill, Img, useCurrentFrame, interpolate } from "remotion";

interface KenBurnsImageProps {
  src: string;
  durationFrames: number;
}

export const KenBurnsImage: React.FC<KenBurnsImageProps> = ({
  src,
  durationFrames,
}) => {
  const frame = useCurrentFrame();

  // Slow zoom in from 100% to 110% over the scene duration
  const scale = interpolate(frame, [0, durationFrames], [1.0, 1.1], {
    extrapolateRight: "clamp",
  });

  // Slight pan (moves 2% right over duration)
  const translateX = interpolate(frame, [0, durationFrames], [0, -20], {
    extrapolateRight: "clamp",
  });

  // Fade in at start
  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ overflow: "hidden", opacity }}>
      <Img
        src={src}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale}) translateX(${translateX}px)`,
        }}
      />
    </AbsoluteFill>
  );
};
