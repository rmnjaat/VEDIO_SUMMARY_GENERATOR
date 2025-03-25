import { useState } from "react";

const SOURCE_TYPES = ["pdf", "url", "text"];

export default function InputForm({ onSubmit, disabled }) {
  const [sourceType, setSourceType] = useState("pdf");
  const [pdfFile, setPdfFile] = useState(null);
  const [url, setUrl] = useState("");
  const [rawText, setRawText] = useState("");

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

      <button
        type="submit"
        className="submit-btn"
        disabled={disabled || !canSubmit}
      >
        {disabled ? "Generating..." : "Generate Script"}
      </button>
    </form>
  );
}
