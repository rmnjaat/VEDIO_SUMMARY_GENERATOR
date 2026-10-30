import { useState, useEffect } from "react";

const SOURCE_TYPES = ["pdf", "url", "text"];
const API_URL = "http://localhost:8000";

export default function InputForm({ onSubmit, disabled }) {
  const [sourceType, setSourceType] = useState("pdf");
  const [pdfFile, setPdfFile] = useState(null);
  const [url, setUrl] = useState("");
  const [rawText, setRawText] = useState("");

  // Provider selection
  const [providers, setProviders] = useState({ tts: [], image: [], video: [] });
  const [selectedTts, setSelectedTts] = useState("");
  const [selectedImage, setSelectedImage] = useState("");
  const [selectedVideo, setSelectedVideo] = useState("");

  // Fetch available providers on mount
  useEffect(() => {
    fetch(`${API_URL}/api/providers`)
      .then((res) => res.json())
      .then((data) => {
        setProviders(data);
        if (data.tts.length) setSelectedTts(data.tts[0]);
        if (data.image.length) setSelectedImage(data.image[0]);
        if (data.video.length) setSelectedVideo(data.video[0]);
      })
      .catch(() => {});
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();

    const formData = new FormData();

    if (sourceType === "pdf" && pdfFile) {
      formData.append("pdf", pdfFile);
    } else if (sourceType === "url") {
      formData.append("url", url);
    } else if (sourceType === "text") {
      formData.append("raw_text", rawText);
    }

    // Append provider choices
    formData.append("tts_provider", selectedTts);
    formData.append("image_provider", selectedImage);
    formData.append("video_provider", selectedVideo);

    onSubmit(formData);
  };

  const canSubmit =
    (sourceType === "pdf" && pdfFile) ||
    (sourceType === "url" && url.trim()) ||
    (sourceType === "text" && rawText.trim());

  return (
    <form className="form-card" onSubmit={handleSubmit}>
      {/* Source type toggle */}
      <div className="source-toggle">
        {SOURCE_TYPES.map((t) => (
          <button
            key={t}
            type="button"
            className={sourceType === t ? "active" : ""}
            onClick={() => setSourceType(t)}
          >
            {t === "pdf" ? "Upload PDF" : t === "url" ? "Paste URL" : "Raw Text"}
          </button>
        ))}
      </div>

      {/* Source input */}
      {sourceType === "pdf" && (
        <div className="input-group">
          <label>PDF Manual</label>
          <div className="file-input-wrapper">
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => setPdfFile(e.target.files[0])}
            />
          </div>
          {pdfFile && <div className="file-name">{pdfFile.name}</div>}
        </div>
      )}

      {sourceType === "url" && (
        <div className="input-group">
          <label>Manual URL</label>
          <input
            type="url"
            placeholder="https://example.com/product-manual"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </div>
      )}

      {sourceType === "text" && (
        <div className="input-group">
          <label>Product Description / Manual Text</label>
          <textarea
            placeholder="Paste the manual text or product description here..."
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
          />
        </div>
      )}

      {/* Provider selection */}
      <div className="provider-row">
        {providers.image.length > 0 && (
          <div className="input-group">
            <label>Image Provider</label>
            <select value={selectedImage} onChange={(e) => setSelectedImage(e.target.value)}>
              {providers.image.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>
        )}
        {providers.tts.length > 0 && (
          <div className="input-group">
            <label>TTS Provider</label>
            <select value={selectedTts} onChange={(e) => setSelectedTts(e.target.value)}>
              {providers.tts.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>
        )}
        {providers.video.length > 0 && (
          <div className="input-group">
            <label>Video Provider</label>
            <select value={selectedVideo} onChange={(e) => setSelectedVideo(e.target.value)}>
              {providers.video.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      <button
        type="submit"
        className="submit-btn"
        disabled={disabled || !canSubmit}
      >
        {disabled ? "Generating..." : "Generate Video"}
      </button>
    </form>
  );
}
