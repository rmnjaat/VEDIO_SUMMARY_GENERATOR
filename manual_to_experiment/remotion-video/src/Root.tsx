import { Composition, staticFile } from "remotion";
import { ManualVideo } from "./ManualVideo";
import sceneData from "./data/scene_script_final.json";

export const RemotionRoot: React.FC = () => {
  // Calculate total frames from scene durations (30fps)
  const FPS = 30;
  const TRANSITION_FRAMES = 15; // 0.5s fade between scenes

  const totalDuration = sceneData.reduce(
    (sum: number, scene: any) => sum + (scene.real_duration_sec || scene.estimated_duration_sec || 8),
    0
  );
  const totalFrames = Math.ceil(totalDuration * FPS) + (sceneData.length - 1) * TRANSITION_FRAMES;

  return (
    <>
      <Composition
        id="ManualVideo"
        component={ManualVideo}
        durationInFrames={totalFrames}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          scenes: sceneData,
        }}
      />
    </>
  );
};
