export default function ScriptResults({ scenes, changelog }) {
  if (!scenes || scenes.length === 0) return null;

  const totalDuration = scenes.reduce(
    (sum, s) => sum + (s.real_duration_sec || s.estimated_duration_sec || 0),
    0
  );
  const minutes = Math.floor(totalDuration / 60);
  const seconds = Math.round(totalDuration % 60);

  return (
    <div className="results-card">
      <h2>
        Generated Script — {scenes.length} scenes, ~{minutes}:{String(seconds).padStart(2, "0")} total
      </h2>

      <div className="scene-list">
        {scenes.map((scene, i) => (
          <div className="scene-item" key={scene.scene_id ?? i}>
            <div className="scene-header">
              <span className={`scene-badge ${scene.type || "step"}`}>
                {scene.type || "step"}
                {scene.step_number != null ? ` ${scene.step_number}` : ""}
              </span>
              <span className="scene-duration">
                {scene.real_duration_sec
                  ? `${scene.real_duration_sec.toFixed(1)}s`
                  : `~${scene.estimated_duration_sec || "?"}s`}
              </span>
            </div>
            <div className="scene-narration">{scene.narration}</div>
            {scene.visual_hint && (
              <div className="scene-visual">Visual: {scene.visual_hint}</div>
            )}
          </div>
        ))}
      </div>

      {changelog && changelog.length > 0 && (
        <div className="changelog">
          <h3>Review Changes ({changelog.length})</h3>
          <ul>
            {changelog.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
