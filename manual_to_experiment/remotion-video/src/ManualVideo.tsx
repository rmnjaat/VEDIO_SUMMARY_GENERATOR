import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import { IntroScene } from "./scenes/IntroScene";
import { StepScene } from "./scenes/StepScene";
import { TransitionScene } from "./scenes/TransitionScene";
import { OutroScene } from "./scenes/OutroScene";

interface SceneData {
  scene_id: number;
  type: string;
  narration: string;
  visual_hint: string;
  section?: string;
  step_number?: number;
  estimated_duration_sec: number;
  real_duration_sec?: number;
}

interface ManualVideoProps {
  scenes: SceneData[];
}

const FPS = 30;
const TRANSITION_FRAMES = 15;

export const ManualVideo: React.FC<ManualVideoProps> = ({ scenes }) => {
  let currentFrame = 0;
  const totalSteps = scenes.filter((s) => s.type === "step").length;

  return (
    <AbsoluteFill style={{ backgroundColor: "#1a1a2e" }}>
      {scenes.map((scene, index) => {
        const duration = scene.real_duration_sec || scene.estimated_duration_sec || 8;
        const durationFrames = Math.ceil(duration * FPS);
        const startFrame = currentFrame;

        // Advance frame counter (with overlap for transitions)
        currentFrame += durationFrames;

        // Count which step this is (for progress bar)
        const stepIndex = scenes
          .slice(0, index + 1)
          .filter((s) => s.type === "step").length;

        const sceneProps = {
          narration: scene.narration,
          visualHint: scene.visual_hint,
          section: scene.section || "",
          durationFrames,
        };

        const audioFile = `audio/scene_${scene.scene_id}.wav`;
        const imageFile = `images/scene_${scene.scene_id}.png`;

        return (
          <Sequence
            key={scene.scene_id}
            from={startFrame}
            durationInFrames={durationFrames}
            name={`Scene ${scene.scene_id}: ${scene.type}`}
          >
            {/* Audio track */}
            <Audio src={staticFile(audioFile)} />

            {/* Visual based on scene type */}
            {scene.type === "intro" && (
              <IntroScene {...sceneProps} imageFile={staticFile(imageFile)} />
            )}
            {scene.type === "step" && (
              <StepScene
                {...sceneProps}
                imageFile={staticFile(imageFile)}
                stepNumber={scene.step_number || stepIndex}
                totalSteps={totalSteps}
                stepIndex={stepIndex}
              />
            )}
            {scene.type === "transition" && (
              <TransitionScene {...sceneProps} />
            )}
            {scene.type === "prerequisites" && (
              <StepScene
                {...sceneProps}
                imageFile={staticFile(imageFile)}
                stepNumber={0}
                totalSteps={totalSteps}
                stepIndex={0}
              />
            )}
            {scene.type === "outro" && (
              <OutroScene {...sceneProps} imageFile={staticFile(imageFile)} />
            )}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
