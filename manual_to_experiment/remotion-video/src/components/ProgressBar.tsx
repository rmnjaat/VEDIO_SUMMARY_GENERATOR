import { useCurrentFrame, interpolate } from "remotion";

interface ProgressBarProps {
  current: number;
  total: number;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  current,
  total,
}) => {
  const frame = useCurrentFrame();

  if (total <= 0) return null;

  const progress = current / total;

  // Animate the fill width
  const fillWidth = interpolate(frame, [0, 20], [0, progress * 100], {
    extrapolateRight: "clamp",
  });

  const opacity = interpolate(frame, [0, 15], [0, 0.9], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        bottom: 0,
        left: 0,
        right: 0,
        height: 4,
        backgroundColor: "rgba(255, 255, 255, 0.15)",
        opacity,
      }}
    >
      <div
        style={{
          height: "100%",
          width: `${fillWidth}%`,
          backgroundColor: "#638cff",
          borderRadius: "0 2px 2px 0",
          transition: "width 0.3s ease",
        }}
      />
    </div>
  );
};
