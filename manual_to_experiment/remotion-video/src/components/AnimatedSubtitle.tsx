import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";

interface AnimatedSubtitleProps {
  text: string;
  durationFrames: number;
}

export const AnimatedSubtitle: React.FC<AnimatedSubtitleProps> = ({
  text,
  durationFrames,
}) => {
  const frame = useCurrentFrame();

  // Fade in
  const opacity = interpolate(frame, [5, 25], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Slide up slightly
  const translateY = interpolate(frame, [5, 25], [20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        bottom: 60,
        left: 80,
        right: 80,
        opacity,
        transform: `translateY(${translateY}px)`,
      }}
    >
      {/* Background pill for readability */}
      <div
        style={{
          backgroundColor: "rgba(0, 0, 0, 0.65)",
          borderRadius: 12,
          padding: "20px 32px",
          backdropFilter: "blur(8px)",
        }}
      >
        <p
          style={{
            color: "#ffffff",
            fontSize: 32,
            fontFamily: "Helvetica Neue, Arial, sans-serif",
            lineHeight: 1.5,
            margin: 0,
            textAlign: "center",
            fontWeight: 400,
          }}
        >
          {text}
        </p>
      </div>
    </div>
  );
};
