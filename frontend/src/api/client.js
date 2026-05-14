const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { "content-type": "application/json" }),
      ...(options.headers || {})
    }
  });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const message = typeof payload === "object" ? payload.detail || JSON.stringify(payload) : payload;
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return payload;
}

export const scrnaApi = {
  ingestDirectory(payload) {
    return request("/scrna/ingest-directory", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  uploadAndIngest({ files, projectName, datasetName, organism, diseaseContext, runsDir, uploadDir }) {
    const form = new FormData();
    Array.from(files || []).forEach((file) => form.append("files", file));
    form.append("project_name", projectName);
    if (datasetName) form.append("dataset_name", datasetName);
    form.append("organism", organism || "unknown");
    if (diseaseContext) form.append("disease_context", diseaseContext);
    if (runsDir) form.append("runs_dir", runsDir);
    if (uploadDir) form.append("upload_dir", uploadDir);
    return request("/scrna/upload-and-ingest", {
      method: "POST",
      body: form
    });
  },

  importMetadataDesign(payload) {
    return request("/scrna/metadata-design", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  evaluateDesign(payload) {
    return request("/scrna/evaluate-design", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  runQcClustering(payload) {
    return request("/scrna/qc-clustering", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }
};

export const platformApi = {
  getDataset(storeDir, datasetId) {
    return request(`/platform/datasets/${encodeURIComponent(datasetId)}?store_dir=${encodeURIComponent(storeDir)}`);
  },

  getMatrices(storeDir, datasetId) {
    return request(`/platform/datasets/${encodeURIComponent(datasetId)}/matrices?store_dir=${encodeURIComponent(storeDir)}`);
  },

  getSampleMetadata(storeDir, datasetId) {
    return request(`/platform/datasets/${encodeURIComponent(datasetId)}/sample-metadata?store_dir=${encodeURIComponent(storeDir)}`);
  },

  getRecommendations(storeDir, datasetId) {
    return request(`/platform/datasets/${encodeURIComponent(datasetId)}/analysis-recommendations?store_dir=${encodeURIComponent(storeDir)}`);
  },

  getConfidenceGates(storeDir, datasetId) {
    return request(`/platform/datasets/${encodeURIComponent(datasetId)}/confidence-gates?store_dir=${encodeURIComponent(storeDir)}`);
  },

  updateSampleMetadata(storeDir, datasetId, payload) {
    return request(`/platform/datasets/${encodeURIComponent(datasetId)}/sample-metadata?store_dir=${encodeURIComponent(storeDir)}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
  }
};

export const workflowApi = {
  listRuns(runsDir) {
    const suffix = runsDir ? `?runs_dir=${encodeURIComponent(runsDir)}` : "";
    return request(`/workflow-runs${suffix}`);
  },

  getRun(runId, runsDir) {
    const suffix = runsDir ? `?runs_dir=${encodeURIComponent(runsDir)}` : "";
    return request(`/workflow-runs/${encodeURIComponent(runId)}${suffix}`);
  },

  getOutputs(runId, runsDir) {
    const suffix = runsDir ? `?runs_dir=${encodeURIComponent(runsDir)}` : "";
    return request(`/workflow-runs/${encodeURIComponent(runId)}/outputs${suffix}`);
  },

  getOutput(runId, outputPath, runsDir) {
    const suffix = runsDir ? `?runs_dir=${encodeURIComponent(runsDir)}` : "";
    return request(`/workflow-runs/${encodeURIComponent(runId)}/outputs/${outputPath}${suffix}`);
  }
};

export const aiApi = {
  chat(payload) {
    return request("/ai/chat", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }
};
