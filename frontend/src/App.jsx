import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  Bot,
  CheckCircle2,
  Database,
  FileJson,
  FileSpreadsheet,
  FolderOpen,
  Home,
  Loader2,
  MessageSquare,
  Play,
  RefreshCw,
  Search,
  Send,
  Table2,
  UploadCloud
} from "lucide-react";
import { aiApi, platformApi, scrnaApi, workflowApi } from "./api/client.js";

const pages = [
  { id: "overview", label: "概览", icon: Home },
  { id: "upload", label: "数据上传", icon: UploadCloud },
  { id: "results", label: "结果展示", icon: FileJson },
  { id: "assistant", label: "AI问答", icon: Bot }
];

const defaultState = {
  runsDir: "",
  storeDir: "",
  datasetId: "",
  ingestRunId: "",
  metadataRunId: "",
  qcRunId: "",
  latestRunId: ""
};

const WORKSPACE_STORAGE_KEY = "omics-ia-workspace";

function loadStoredWorkspace() {
  try {
    const stored = localStorage.getItem(WORKSPACE_STORAGE_KEY);
    return stored ? { ...defaultState, ...JSON.parse(stored) } : defaultState;
  } catch {
    return defaultState;
  }
}

export default function App() {
  const [activePage, setActivePage] = useState("overview");
  const [workspace, setWorkspace] = useState(loadStoredWorkspace);
  const [dataset, setDataset] = useState(null);
  const [metadataRows, setMetadataRows] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [confidenceGates, setConfidenceGates] = useState([]);
  const [latestRun, setLatestRun] = useState(null);
  const [status, setStatus] = useState({ type: "idle", message: "等待数据接入" });

  const updateWorkspace = (patch) => {
    setWorkspace((current) => ({ ...current, ...patch }));
  };

  useEffect(() => {
    localStorage.setItem(WORKSPACE_STORAGE_KEY, JSON.stringify(workspace));
  }, [workspace]);

  const refreshContext = async (override = {}) => {
    const next = { ...workspace, ...override };
    if (!next.storeDir || !next.datasetId) return;
    try {
      setStatus({ type: "loading", message: "正在刷新项目上下文" });
      const [datasetPayload, sampleMetadata, recommendationPayload, gatePayload] = await Promise.all([
        platformApi.getDataset(next.storeDir, next.datasetId),
        platformApi.getSampleMetadata(next.storeDir, next.datasetId),
        platformApi.getRecommendations(next.storeDir, next.datasetId),
        platformApi.getConfidenceGates(next.storeDir, next.datasetId)
      ]);
      setDataset(datasetPayload);
      setMetadataRows(sampleMetadata);
      setRecommendations(recommendationPayload);
      setConfidenceGates(gatePayload);
      if (next.latestRunId) {
        setLatestRun(await workflowApi.getRun(next.latestRunId, next.runsDir || undefined));
      }
      setStatus({ type: "success", message: "项目上下文已刷新" });
    } catch (caught) {
      setStatus({ type: "error", message: caught.message });
    }
  };

  useEffect(() => {
    refreshContext();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const context = {
    workspace,
    updateWorkspace,
    dataset,
    metadataRows,
    recommendations,
    confidenceGates,
    latestRun,
    status,
    setStatus,
    refreshContext
  };

  return (
    <main className="min-h-screen bg-[#f5f7fb] text-slate-950">
      <Shell activePage={activePage} setActivePage={setActivePage} status={status}>
        {activePage === "overview" && <OverviewPage {...context} />}
        {activePage === "upload" && <UploadPage {...context} />}
        {activePage === "results" && <ResultsPage {...context} />}
        {activePage === "assistant" && <AssistantPage {...context} />}
      </Shell>
    </main>
  );
}

function Shell({ activePage, setActivePage, status, children }) {
  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-72 shrink-0 border-r border-slate-200 bg-white px-4 py-5 lg:block">
        <div className="flex items-center gap-3 px-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-600 text-white">
            <Activity className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm font-semibold">Omics IA</div>
            <div className="text-xs text-slate-500">scRNA Phase 1</div>
          </div>
        </div>
        <nav className="mt-8 space-y-1">
          {pages.map((page) => {
            const Icon = page.icon;
            const active = page.id === activePage;
            return (
              <button
                key={page.id}
                type="button"
                onClick={() => setActivePage(page.id)}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition ${
                  active ? "bg-slate-950 text-white" : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                }`}
              >
                <Icon className={`h-4 w-4 ${active ? "text-emerald-300" : "text-slate-400"}`} />
                {page.label}
              </button>
            );
          })}
        </nav>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur lg:px-8">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <nav className="flex gap-2 overflow-x-auto lg:hidden">
              {pages.map((page) => (
                <button
                  key={page.id}
                  type="button"
                  onClick={() => setActivePage(page.id)}
                  className={`shrink-0 rounded-lg px-3 py-2 text-sm font-medium ${
                    page.id === activePage ? "bg-slate-950 text-white" : "bg-slate-100 text-slate-700"
                  }`}
                >
                  {page.label}
                </button>
              ))}
            </nav>
            <div>
              <h1 className="text-xl font-semibold tracking-normal">单细胞智能分析工作台</h1>
              <p className="mt-1 text-sm text-slate-500">数据接入、metadata 识别、分析模式推荐与结果追踪</p>
            </div>
            <StatusPill status={status} />
          </div>
        </header>
        <div className="mx-auto w-full max-w-7xl px-4 py-6 lg:px-8">{children}</div>
      </section>
    </div>
  );
}

function OverviewPage({ workspace, dataset, metadataRows, recommendations, confidenceGates, latestRun, refreshContext, status }) {
  const latestRecommendation = recommendations.at(-1);
  const latestGate = confidenceGates.at(-1);
  return (
    <div className="space-y-5">
      <SectionTitle icon={Home} title="概览" action={<RefreshButton onClick={() => refreshContext()} loading={status.type === "loading"} />} />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Metric label="Dataset" value={dataset?.dataset_name || "未加载"} icon={Database} />
        <Metric label="样本数" value={dataset?.sample_count ?? "-"} icon={Table2} />
        <Metric label="矩阵数" value={dataset?.matrix_count ?? "-"} icon={FileSpreadsheet} />
        <Metric label="Metadata" value={dataset?.metadata_status || "-"} icon={CheckCircle2} />
      </div>
      <Panel>
        <div className="grid gap-5 lg:grid-cols-[1fr_1fr]">
          <KeyValueList
            title="当前上下文"
            rows={[
              ["store_dir", workspace.storeDir || "未设置"],
              ["dataset_id", workspace.datasetId || "未设置"],
              ["runs_dir", workspace.runsDir || "默认 runs"],
              ["latest_run", workspace.latestRunId || "无"]
            ]}
          />
          <KeyValueList
            title="推荐状态"
            rows={[
              ["recommended_mode", latestRecommendation?.recommended_mode || "等待评估"],
              ["confidence", latestRecommendation?.result_confidence || "-"],
              ["gate_passed", latestGate ? String(latestGate.passed) : "-"],
              ["metadata_rows", String(metadataRows.length || 0)]
            ]}
          />
        </div>
      </Panel>
      {latestRun && <JsonBlock title="最近 Workflow Manifest" data={latestRun} />}
    </div>
  );
}

function UploadPage({ workspace, updateWorkspace, refreshContext, setStatus, status }) {
  const [localForm, setLocalForm] = useState({
    matrixDirectory: "data/GSE183904_RAW",
    projectName: "GSE183904 gastric cancer scRNA analysis",
    datasetName: "",
    organism: "human",
    diseaseContext: "gastric cancer",
    runsDir: ""
  });
  const [metadataForm, setMetadataForm] = useState({ metadataTable: "", datasetId: "", platformStore: "" });
  const [qcForm, setQcForm] = useState({
    minGenes: "200",
    maxGenes: "",
    minCounts: "0",
    maxCounts: "",
    maxMitoPct: "20",
    maxCellsPerSample: "2000",
    clusterCount: "4"
  });
  const [selectedFiles, setSelectedFiles] = useState([]);

  const runLocalIngest = async () => {
    try {
      setStatus({ type: "loading", message: "正在执行目录接入 workflow" });
      const result = await scrnaApi.ingestDirectory({
        matrix_directory: localForm.matrixDirectory,
        project_name: localForm.projectName,
        dataset_name: localForm.datasetName || null,
        organism: localForm.organism,
        disease_context: localForm.diseaseContext,
        runs_dir: localForm.runsDir || null
      });
      const patch = {
        runsDir: localForm.runsDir,
        storeDir: result.metrics.platform_store,
        datasetId: result.metrics.dataset_id,
        ingestRunId: result.run_id,
        latestRunId: result.run_id
      };
      updateWorkspace(patch);
      setMetadataForm((current) => ({ ...current, datasetId: patch.datasetId, platformStore: patch.storeDir }));
      await refreshContext(patch);
      setStatus({ type: "success", message: "目录接入完成" });
    } catch (caught) {
      setStatus({ type: "error", message: caught.message });
    }
  };

  const runUploadIngest = async () => {
    if (!selectedFiles.length) {
      setStatus({ type: "error", message: "请先选择文件" });
      return;
    }
    try {
      setStatus({ type: "loading", message: "正在上传并接入数据" });
      const result = await scrnaApi.uploadAndIngest({
        files: selectedFiles,
        projectName: localForm.projectName,
        datasetName: localForm.datasetName,
        organism: localForm.organism,
        diseaseContext: localForm.diseaseContext,
        runsDir: localForm.runsDir
      });
      const patch = {
        runsDir: localForm.runsDir,
        storeDir: result.metrics.platform_store,
        datasetId: result.metrics.dataset_id,
        ingestRunId: result.run_id,
        latestRunId: result.run_id
      };
      updateWorkspace(patch);
      setMetadataForm((current) => ({ ...current, datasetId: patch.datasetId, platformStore: patch.storeDir }));
      await refreshContext(patch);
      setStatus({ type: "success", message: "上传接入完成" });
    } catch (caught) {
      setStatus({ type: "error", message: caught.message });
    }
  };

  const runMetadataDesign = async () => {
    try {
      setStatus({ type: "loading", message: "正在导入 metadata 并评估实验设计" });
      const result = await scrnaApi.importMetadataDesign({
        platform_store: metadataForm.platformStore || workspace.storeDir,
        metadata_table: metadataForm.metadataTable,
        dataset_id: metadataForm.datasetId || workspace.datasetId,
        runs_dir: workspace.runsDir || null
      });
      const patch = {
        storeDir: result.metrics.platform_store,
        datasetId: metadataForm.datasetId || workspace.datasetId,
        metadataRunId: result.run_id,
        latestRunId: result.run_id
      };
      updateWorkspace(patch);
      await refreshContext(patch);
      setStatus({ type: "success", message: "实验设计评估完成" });
    } catch (caught) {
      setStatus({ type: "error", message: caught.message });
    }
  };

  const runQcClustering = async () => {
    if (!workspace.storeDir || !workspace.datasetId) {
      setStatus({ type: "error", message: "缂哄皯 storeDir 鎴?datasetId锛屾棤娉曞惎鍔?QC workflow" });
      return;
    }
    try {
      setStatus({ type: "loading", message: "姝ｅ湪鎵ц QC / clustering workflow" });
      const result = await scrnaApi.runQcClustering({
        platform_store: workspace.storeDir,
        dataset_id: workspace.datasetId,
        min_genes: Number(qcForm.minGenes || 0),
        max_genes: qcForm.maxGenes ? Number(qcForm.maxGenes) : null,
        min_counts: Number(qcForm.minCounts || 0),
        max_counts: qcForm.maxCounts ? Number(qcForm.maxCounts) : null,
        max_mito_pct: Number(qcForm.maxMitoPct || 20),
        max_cells_per_sample: Number(qcForm.maxCellsPerSample || 2000),
        cluster_count: Number(qcForm.clusterCount || 4),
        runs_dir: workspace.runsDir || null
      });
      const patch = {
        qcRunId: result.run_id,
        latestRunId: result.run_id
      };
      updateWorkspace(patch);
      await refreshContext(patch);
      setStatus({ type: "success", message: "QC / clustering workflow 瀹屾垚" });
    } catch (caught) {
      setStatus({ type: "error", message: caught.message });
    }
  };

  return (
    <div className="space-y-5">
      <SectionTitle icon={UploadCloud} title="数据上传与分析准备" />
      <Panel>
        <div className="grid gap-4 lg:grid-cols-2">
          <TextInput label="矩阵目录" value={localForm.matrixDirectory} onChange={(value) => setLocalForm({ ...localForm, matrixDirectory: value })} />
          <TextInput label="runs_dir" value={localForm.runsDir} onChange={(value) => setLocalForm({ ...localForm, runsDir: value })} placeholder="留空使用后端默认 runs" />
          <TextInput label="项目名称" value={localForm.projectName} onChange={(value) => setLocalForm({ ...localForm, projectName: value })} />
          <TextInput label="数据集名称" value={localForm.datasetName} onChange={(value) => setLocalForm({ ...localForm, datasetName: value })} placeholder="可选" />
          <TextInput label="物种" value={localForm.organism} onChange={(value) => setLocalForm({ ...localForm, organism: value })} />
          <TextInput label="疾病背景" value={localForm.diseaseContext} onChange={(value) => setLocalForm({ ...localForm, diseaseContext: value })} />
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          <CommandButton icon={FolderOpen} onClick={runLocalIngest} loading={status.type === "loading"}>
            本地路径接入
          </CommandButton>
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
            <UploadCloud className="h-4 w-4" />
            选择矩阵文件
            <input type="file" multiple className="hidden" onChange={(event) => setSelectedFiles(Array.from(event.target.files || []))} />
          </label>
          <CommandButton icon={UploadCloud} onClick={runUploadIngest} loading={status.type === "loading"}>
            上传并接入
          </CommandButton>
        </div>
        {selectedFiles.length > 0 && <div className="mt-3 text-sm text-slate-500">已选择 {selectedFiles.length} 个文件</div>}
      </Panel>

      <Panel>
        <div className="grid gap-4 lg:grid-cols-3">
          <TextInput label="platform_store" value={metadataForm.platformStore || workspace.storeDir} onChange={(value) => setMetadataForm({ ...metadataForm, platformStore: value })} />
          <TextInput label="dataset_id" value={metadataForm.datasetId || workspace.datasetId} onChange={(value) => setMetadataForm({ ...metadataForm, datasetId: value })} />
          <TextInput label="metadata CSV/TSV 路径" value={metadataForm.metadataTable} onChange={(value) => setMetadataForm({ ...metadataForm, metadataTable: value })} placeholder="data/processed/GSE183904_metadata.csv" />
        </div>
        <div className="mt-4">
          <CommandButton icon={Play} onClick={runMetadataDesign} loading={status.type === "loading"}>
            导入 metadata 并推荐分析模式
          </CommandButton>
        </div>
      </Panel>

      <Panel>
        <div className="grid gap-4 lg:grid-cols-4">
          <TextInput label="min_genes" value={qcForm.minGenes} onChange={(value) => setQcForm({ ...qcForm, minGenes: value })} />
          <TextInput label="max_genes" value={qcForm.maxGenes} onChange={(value) => setQcForm({ ...qcForm, maxGenes: value })} placeholder="optional" />
          <TextInput label="min_counts" value={qcForm.minCounts} onChange={(value) => setQcForm({ ...qcForm, minCounts: value })} />
          <TextInput label="max_counts" value={qcForm.maxCounts} onChange={(value) => setQcForm({ ...qcForm, maxCounts: value })} placeholder="optional" />
          <TextInput label="max_mito_pct" value={qcForm.maxMitoPct} onChange={(value) => setQcForm({ ...qcForm, maxMitoPct: value })} />
          <TextInput label="max_cells_per_sample" value={qcForm.maxCellsPerSample} onChange={(value) => setQcForm({ ...qcForm, maxCellsPerSample: value })} />
          <TextInput label="cluster_count" value={qcForm.clusterCount} onChange={(value) => setQcForm({ ...qcForm, clusterCount: value })} />
        </div>
        <div className="mt-4">
          <CommandButton icon={Activity} onClick={runQcClustering} loading={status.type === "loading"}>
            Run QC / clustering
          </CommandButton>
        </div>
      </Panel>
    </div>
  );
}

function ResultsPage({ workspace, metadataRows, recommendations, confidenceGates, latestRun, refreshContext, status, setStatus }) {
  const [outputPath, setOutputPath] = useState("reports/data_readiness_report.json");
  const [outputJson, setOutputJson] = useState(null);
  const commonOutputs = [
    "reports/data_readiness_report.json",
    "reports/analysis_mode_recommendation.json",
    "reports/qc_clustering_report.json",
    "figures/umap_plot_data.json",
    "figures/qc_violin_plot_data.json",
    "tables/umap_embedding.json"
  ];

  const loadOutput = async () => {
    if (!workspace.latestRunId) return;
    try {
      const data = await workflowApi.getOutput(workspace.latestRunId, outputPath, workspace.runsDir || undefined);
      setOutputJson(data);
    } catch (caught) {
      setStatus({ type: "error", message: caught.message });
    }
  };

  return (
    <div className="space-y-5">
      <SectionTitle icon={FileJson} title="结果展示" action={<RefreshButton onClick={() => refreshContext()} loading={status.type === "loading"} />} />
      <Panel>
        <div className="mb-4 flex flex-wrap gap-2">
          {commonOutputs.map((path) => (
            <button
              key={path}
              type="button"
              onClick={() => setOutputPath(path)}
              className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
            >
              {path}
            </button>
          ))}
        </div>
        <div className="grid gap-4 lg:grid-cols-[1fr_auto]">
          <TextInput label="输出 JSON 路径" value={outputPath} onChange={setOutputPath} />
          <div className="flex items-end">
            <CommandButton icon={Search} onClick={loadOutput}>读取输出</CommandButton>
          </div>
        </div>
      </Panel>
      <div className="grid gap-5 xl:grid-cols-2">
        <JsonBlock title="最新运行" data={latestRun || { message: "暂无 run" }} />
        <JsonBlock title="输出 JSON" data={outputJson || { message: "选择输出路径后读取" }} />
      </div>
      <Panel>
        <h2 className="text-base font-semibold">Metadata 在线编辑</h2>
        <MetadataEditor rows={metadataRows} workspace={workspace} refreshContext={refreshContext} setStatus={setStatus} />
      </Panel>
      <div className="grid gap-5 xl:grid-cols-2">
        <JsonBlock title="分析模式推荐" data={recommendations.at(-1) || { message: "等待 metadata design" }} />
        <JsonBlock title="可信度门控" data={confidenceGates.at(-1) || { message: "等待 metadata design" }} />
      </div>
    </div>
  );
}

function MetadataEditor({ rows, workspace, refreshContext, setStatus }) {
  const editableRows = rows.slice(0, 40);
  const [draftRows, setDraftRows] = useState(editableRows);

  useEffect(() => {
    setDraftRows(editableRows);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(editableRows)]);

  const updateCell = (sampleId, field, value) => {
    setDraftRows((current) =>
      current.map((row) => (row.sample_id === sampleId ? { ...row, [field]: value } : row))
    );
  };

  const save = async () => {
    if (!workspace.storeDir || !workspace.datasetId) {
      setStatus({ type: "error", message: "缺少 storeDir 或 datasetId，无法保存 metadata" });
      return;
    }
    const updates = {};
    for (const row of draftRows) {
      updates[row.sample_id] = {
        condition: row.condition,
        patient_id: row.patient_id,
        batch: row.batch,
        tissue: row.tissue,
        disease: row.disease
      };
    }
    try {
      setStatus({ type: "loading", message: "正在保存 metadata 并重新评估设计" });
      await platformApi.updateSampleMetadata(workspace.storeDir, workspace.datasetId, {
        updates_by_sample_id: updates,
        evaluate: true
      });
      await refreshContext();
      setStatus({ type: "success", message: "metadata 已保存" });
    } catch (caught) {
      setStatus({ type: "error", message: caught.message });
    }
  };

  if (!rows.length) {
    return <div className="mt-3 rounded-lg border border-dashed border-slate-300 p-6 text-sm text-slate-500">暂无 metadata 行</div>;
  }

  return (
    <div className="mt-3">
      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="w-full min-w-[980px] text-left text-sm">
          <thead className="bg-slate-100 text-xs font-semibold uppercase text-slate-600">
            <tr>
              {["sample_id", "file_name", "condition", "patient_id", "batch", "tissue", "disease"].map((column) => (
                <th key={column} className="px-3 py-2">{column}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {draftRows.map((row) => (
              <tr key={row.sample_id}>
                <td className="px-3 py-2 font-medium text-slate-700">{row.sample_id}</td>
                <td className="max-w-[220px] truncate px-3 py-2 text-slate-600">{row.file_name}</td>
                {["condition", "patient_id", "batch", "tissue", "disease"].map((field) => (
                  <td key={field} className="px-2 py-2">
                    <input
                      value={row[field] || ""}
                      onChange={(event) => updateCell(row.sample_id, field, event.target.value)}
                      className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm outline-none focus:border-emerald-500"
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-3 flex items-center justify-between gap-3">
        <div className="text-sm text-slate-500">当前显示前 {draftRows.length} 行；保存后会重新计算分析模式推荐。</div>
        <CommandButton icon={CheckCircle2} onClick={save}>保存 metadata</CommandButton>
      </div>
    </div>
  );
}

function AssistantPage({ dataset, recommendations, confidenceGates, latestRun }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const contextSummary = useMemo(() => ({
    dataset,
    latestRecommendation: recommendations.at(-1) || null,
    latestConfidenceGate: confidenceGates.at(-1) || null,
    latestRunId: latestRun?.run_id || null
  }), [dataset, recommendations, confidenceGates, latestRun]);

  const ask = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setError("");
    try {
      const result = await aiApi.chat({ question, context: contextSummary });
      setAnswer(result.answer);
    } catch (caught) {
      setError(caught.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      <SectionTitle icon={MessageSquare} title="AI问答" />
      <Panel>
        <div className="grid gap-5 lg:grid-cols-[1fr_380px]">
          <div>
            <label className="text-sm font-medium text-slate-700">问题</label>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              className="mt-2 min-h-36 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
              placeholder="例如：当前数据是否适合做正式 pseudobulk 差异分析？"
            />
            <button
              type="button"
              onClick={ask}
              disabled={loading || !question.trim()}
              className="mt-3 inline-flex items-center gap-2 rounded-lg bg-slate-950 px-3 py-2 text-sm font-semibold text-white opacity-70"
              title="通过后端代理调用 LLM"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              发送
            </button>
            <p className="mt-3 text-sm leading-6 text-slate-500">
              AI 问答通过后端代理调用 LLM，并从环境变量读取密钥，避免浏览器暴露访问凭证。
            </p>
            {error && <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
            {answer && <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-800 whitespace-pre-wrap">{answer}</div>}
          </div>
          <JsonBlock title="可用上下文" data={contextSummary} compact />
        </div>
      </Panel>
    </div>
  );
}

function SectionTitle({ icon: Icon, title, action }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-2">
        <Icon className="h-5 w-5 text-emerald-600" />
        <h2 className="text-lg font-semibold tracking-normal">{title}</h2>
      </div>
      {action}
    </div>
  );
}

function Panel({ children }) {
  return <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">{children}</section>;
}

function Metric({ label, value, icon: Icon }) {
  return (
    <Panel>
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Icon className="h-4 w-4 text-indigo-600" />
        {label}
      </div>
      <div className="mt-2 break-words text-2xl font-semibold">{value}</div>
    </Panel>
  );
}

function TextInput({ label, value, onChange, placeholder }) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <input
        value={value || ""}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
      />
    </label>
  );
}

function CommandButton({ icon: Icon, onClick, loading, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      className="inline-flex items-center gap-2 rounded-lg bg-slate-950 px-3 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-wait disabled:opacity-60"
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Icon className="h-4 w-4" />}
      {children}
    </button>
  );
}

function RefreshButton({ onClick, loading }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
    >
      <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
      刷新
    </button>
  );
}

function StatusPill({ status }) {
  const styles = {
    idle: "border-slate-200 bg-slate-100 text-slate-600",
    loading: "border-indigo-200 bg-indigo-50 text-indigo-700",
    success: "border-emerald-200 bg-emerald-50 text-emerald-700",
    error: "border-rose-200 bg-rose-50 text-rose-700"
  };
  return (
    <span className={`inline-flex w-fit items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium ${styles[status.type] || styles.idle}`}>
      {status.type === "loading" ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
      {status.message}
    </span>
  );
}

function KeyValueList({ title, rows }) {
  return (
    <div>
      <h2 className="text-base font-semibold">{title}</h2>
      <dl className="mt-3 divide-y divide-slate-100 rounded-lg border border-slate-200">
        {rows.map(([key, value]) => (
          <div key={key} className="grid gap-2 px-3 py-2 text-sm sm:grid-cols-[160px_1fr]">
            <dt className="font-medium text-slate-500">{key}</dt>
            <dd className="break-words text-slate-900">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function JsonBlock({ title, data, compact }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold">{title}</h2>
      <pre className={`mt-3 overflow-auto rounded-lg bg-slate-950 p-4 text-xs leading-5 text-emerald-200 ${compact ? "max-h-96" : "max-h-[520px]"}`}>
        {JSON.stringify(data, null, 2)}
      </pre>
    </section>
  );
}

function DataTable({ rows }) {
  if (!rows.length) {
    return <div className="mt-3 rounded-lg border border-dashed border-slate-300 p-6 text-sm text-slate-500">暂无 metadata 行</div>;
  }
  const columns = Object.keys(rows[0]).slice(0, 8);
  return (
    <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200">
      <table className="w-full min-w-[760px] text-left text-sm">
        <thead className="bg-slate-100 text-xs font-semibold uppercase text-slate-600">
          <tr>
            {columns.map((column) => (
              <th key={column} className="px-3 py-2">{column}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {rows.map((row, index) => (
            <tr key={row.sample_metadata_id || index}>
              {columns.map((column) => (
                <td key={column} className="max-w-[240px] truncate px-3 py-2 text-slate-700">{String(row[column] ?? "")}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
