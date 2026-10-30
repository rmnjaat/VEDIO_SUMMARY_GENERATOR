const STAGES = [
  { key: "stage1", label: "Input Preparation" },
  { key: "stage2", label: "Content Extraction" },
  { key: "stage2_5", label: "Verification & Grounding" },
  { key: "stage2_7", label: "Enrichment" },
  { key: "stage3", label: "Script Generation" },
  { key: "stage3_5", label: "Script Review & Polish" },
  { key: "stage4", label: "Image Generation" },
  { key: "stage5", label: "Audio Generation (TTS)" },
  { key: "stage6", label: "Video Assembly" },
];

function getStageStatus(stageKey, progress) {
  const doneKey = stageKey + "_done";
  if (progress[doneKey]) return "done";
  if (progress[stageKey]) return "active";
  return "pending";
}

function getDetail(stageKey, progress) {
  const doneKey = stageKey + "_done";
  if (progress[doneKey]) return progress[doneKey];
  if (progress[stageKey]) return progress[stageKey];
  return "";
}

export default function ProgressTracker({ progress }) {
  return (
    <div className="progress-card">
      <h2>Pipeline Progress</h2>
      {STAGES.map(({ key, label }) => {
        const status = getStageStatus(key, progress);
        const detail = getDetail(key, progress);

        return (
          <div className="progress-step" key={key}>
            <div className={`progress-icon ${status}`}>
              {status === "done" ? "\u2713" : status === "active" ? "\u25CB" : "\u2022"}
            </div>
            <div className="progress-text">
              <div className="stage-name">{label}</div>
              {detail && <div className="stage-detail">{detail}</div>}
            </div>
          </div>
        );
      })}
    </div>
  );
}
