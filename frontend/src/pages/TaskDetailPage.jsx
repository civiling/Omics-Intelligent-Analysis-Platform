import { useState } from "react";
import {
  Activity,
  AlertCircle,
  BarChart3,
  CheckCircle2,
  ChevronRight,
  CircleDot,
  ClipboardList,
  Clock3,
  Cpu,
  Database,
  Dna,
  FileText,
  Gauge,
  Home,
  Layers3,
  Loader2,
  Play,
  ServerCog,
  Sparkles,
  TerminalSquare
} from "lucide-react";

const task = {
  id: "RNA-DEG-20260514-0842",
  createdAt: "2026-05-14 09:18:32",
  status: "Running",
  workflow: "Transcriptomics differential expression",
  progress: 68,
  eta: "00:17:42"
};

const parameters = [
  ["Reference Genome", "GRCh38.p14"],
  ["Aligner", "HISAT2"],
  ["Annotation", "GENCODE v44"],
  ["Thread count", "24"],
  ["FDR threshold", "0.05"],
  ["Input samples", "12 RNA-seq FASTQ pairs"]
];

const runtimeLogs = [
  "[INFO] FastQC completed for submitted samples",
  "[INFO] Adapter trimming finished, waiting for mapping summary",
  "[INFO] HISAT2 alignment process is running",
  "[INFO] FeatureCounts stage is queued"
];

const pipelineSteps = [
  {
    id: "preprocess",
    name: "数据预处理",
    subtitle: "FastQC 质控与接头切除",
    status: "Success",
    progress: 100,
    icon: Gauge,
    metrics: [
      ["Stage", "Completed"],
      ["QC report", "Generated"],
      ["Output", "Clean FASTQ"]
    ],
    logs: [
      "[INFO] Quality control completed",
      "[INFO] Adapter trimming completed",
      "[INFO] QC artifacts registered"
    ]
  },
  {
    id: "mapping",
    name: "序列比对",
    subtitle: "HISAT2 / STAR 比对过程",
    status: "Processing",
    progress: 68,
    icon: Dna,
    metrics: [
      ["Stage", "Running"],
      ["Current tool", "HISAT2"],
      ["Output", "Sorted BAM"]
    ],
    logs: [
      "[INFO] Splice-aware mapping started",
      "[INFO] Alignment job is processing",
      "[INFO] BAM sorting will run after alignment"
    ]
  },
  {
    id: "counts",
    name: "特征计数",
    subtitle: "表达量矩阵计算",
    status: "Pending",
    progress: 0,
    icon: Database,
    metrics: [
      ["Stage", "Waiting"],
      ["Current tool", "featureCounts"],
      ["Output", "Gene count matrix"]
    ],
    logs: [
      "[PENDING] Waiting for mapping outputs",
      "[PENDING] Annotation file is ready",
      "[PENDING] Count matrix has not been generated"
    ]
  }
];

const navItems = [
  { href: "#overview", label: "概览", icon: Home },
  { href: "#pipeline", label: "流程", icon: Layers3 },
  { href: "#parameters", label: "参数", icon: ServerCog },
  { href: "#logs", label: "日志", icon: TerminalSquare },
  { href: "#results", label: "结果", icon: BarChart3 }
];

const statusStyles = {
  Pending: "border-slate-200 bg-slate-100 text-slate-600",
  Processing: "border-indigo-200 bg-indigo-50 text-indigo-700",
  Success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  Failed: "border-rose-200 bg-rose-50 text-rose-700",
  Running: "border-emerald-200 bg-emerald-50 text-emerald-700"
};

function Badge({ status }) {
  const Icon = status === "Success" ? CheckCircle2 : status === "Processing" || status === "Running" ? Loader2 : status === "Failed" ? AlertCircle : CircleDot;

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${statusStyles[status]}`}>
      <Icon className={`h-3.5 w-3.5 ${status === "Processing" || status === "Running" ? "animate-spin" : ""}`} />
      {status}
    </span>
  );
}

function SideNavigation() {
  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-slate-200 bg-slate-950 px-4 py-5 text-white lg:block">
        <div className="flex items-center gap-3 rounded-lg bg-white/5 px-3 py-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-500 text-white">
            <Dna className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-semibold">Omics IA</div>
            <div className="truncate text-xs text-slate-400">Analysis Platform</div>
          </div>
        </div>

        <nav className="mt-8 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <a key={item.href} href={item.href} className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-300 transition hover:bg-white/10 hover:text-white">
                <Icon className="h-4 w-4 text-emerald-300" />
                {item.label}
              </a>
            );
          })}
        </nav>

        <div className="absolute bottom-5 left-4 right-4 rounded-lg border border-emerald-400/20 bg-emerald-400/10 p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-emerald-200">Runtime</span>
            <Badge status={task.status} />
          </div>
          <div className="mt-3 h-1.5 rounded-full bg-white/10">
            <div className="h-1.5 rounded-full bg-emerald-400" style={{ width: `${task.progress}%` }} />
          </div>
        </div>
      </aside>

      <nav className="sticky top-0 z-30 border-b border-slate-200 bg-slate-950/95 px-3 py-2 backdrop-blur lg:hidden">
        <div className="no-scrollbar flex items-center gap-2 overflow-x-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <a key={item.href} href={item.href} className="inline-flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-slate-200">
                <Icon className="h-4 w-4 text-emerald-300" />
                {item.label}
              </a>
            );
          })}
        </div>
      </nav>
    </>
  );
}

function TaskStatusCard() {
  return (
    <section id="overview" className="scroll-mt-20 rounded-lg border border-slate-200 bg-white p-5 shadow-clinical lg:scroll-mt-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-indigo-700">
            <Activity className="h-4 w-4" />
            任务详情
          </div>
          <h1 className="mt-3 text-2xl font-semibold tracking-normal text-slate-950 sm:text-3xl">
            多组学智能分析平台
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            {task.workflow} 正在执行，后端流程已完成质控并进入序列比对阶段。
          </p>
        </div>
        <Badge status={task.status} />
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <InfoTile icon={FileText} label="Task ID" value={task.id} />
        <InfoTile icon={Clock3} label="创建时间" value={task.createdAt} />
        <InfoTile icon={Cpu} label="计算资源" value="24 threads / 96 GB" />
        <InfoTile icon={Play} label="预计剩余" value={task.eta} />
      </div>

      <div className="mt-5">
        <div className="mb-2 flex items-center justify-between text-xs font-medium text-slate-500">
          <span>Pipeline progress</span>
          <span>{task.progress}%</span>
        </div>
        <div className="h-2 rounded-full bg-slate-100">
          <div className="h-2 rounded-full bg-gradient-to-r from-indigo-600 via-cyan-400 to-emerald-400" style={{ width: `${task.progress}%` }} />
        </div>
      </div>
    </section>
  );
}

function InfoTile({ icon: Icon, label, value }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
        <Icon className="h-4 w-4 text-indigo-600" />
        {label}
      </div>
      <div className="mt-2 break-words text-sm font-semibold text-slate-950">{value}</div>
    </div>
  );
}

function ParameterTable() {
  return (
    <section id="parameters" className="scroll-mt-20 rounded-lg border border-slate-200 bg-white p-5 shadow-clinical lg:scroll-mt-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ServerCog className="h-5 w-5 text-indigo-600" />
          <h2 className="text-base font-semibold text-slate-950">参数概览</h2>
        </div>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">API Config</span>
      </div>
      <div className="mt-4 overflow-hidden rounded-lg border border-slate-200">
        <table className="w-full text-left text-sm">
          <tbody className="divide-y divide-slate-200">
            {parameters.map(([key, value]) => (
              <tr key={key} className="bg-white">
                <th className="w-1/2 bg-slate-50 px-4 py-3 font-medium text-slate-600">{key}</th>
                <td className="px-4 py-3 font-semibold text-slate-900">{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function PipelineStepper({ activeStep, setActiveStep }) {
  return (
    <section id="pipeline" className="scroll-mt-20 rounded-lg border border-slate-200 bg-white p-5 shadow-clinical lg:scroll-mt-6">
      <div className="mb-4 flex items-center gap-2">
        <Layers3 className="h-5 w-5 text-indigo-600" />
        <h2 className="text-base font-semibold text-slate-950">流程编排</h2>
      </div>

      <div className="space-y-3">
        {pipelineSteps.map((step, index) => {
          const Icon = step.icon;
          const isActive = activeStep.id === step.id;
          return (
            <button
              key={step.id}
              type="button"
              onClick={() => setActiveStep(step)}
              className={`w-full rounded-lg border p-4 text-left transition duration-200 ${
                isActive
                  ? "border-indigo-300 bg-indigo-50 shadow-sm"
                  : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
              }`}
            >
              <div className="flex items-start gap-3">
                <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${isActive ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"}`}>
                  <Icon className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-semibold text-slate-400">0{index + 1}</span>
                    <h3 className="text-sm font-semibold text-slate-950">{step.name}</h3>
                    <Badge status={step.status} />
                  </div>
                  <p className="mt-1 text-xs leading-5 text-slate-500">{step.subtitle}</p>
                  <div className="mt-3 h-1.5 rounded-full bg-slate-100">
                    <div className={`h-1.5 rounded-full ${step.status === "Success" ? "bg-emerald-500" : step.status === "Processing" ? "bg-indigo-600" : "bg-slate-300"}`} style={{ width: `${step.progress}%` }} />
                  </div>
                </div>
                <ChevronRight className={`mt-2 h-4 w-4 shrink-0 text-slate-400 transition ${isActive ? "translate-x-0.5 text-indigo-600" : ""}`} />
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function StepDetail({ step }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-clinical transition-all duration-300">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-indigo-700">
            <Sparkles className="h-4 w-4" />
            当前阶段
          </div>
          <h2 className="mt-2 text-xl font-semibold text-slate-950">{step.name}</h2>
          <p className="mt-1 text-sm text-slate-600">{step.subtitle}</p>
        </div>
        <Badge status={step.status} />
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        {step.metrics.map(([label, value]) => (
          <div key={label} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <div className="text-xs font-medium text-slate-500">{label}</div>
            <div className="mt-1 text-lg font-semibold text-slate-950">{value}</div>
          </div>
        ))}
      </div>

      <div className="mt-5 rounded-lg border border-slate-200 bg-slate-950 p-4">
        <div className="mb-3 flex items-center gap-2 text-xs font-semibold text-emerald-300">
          <TerminalSquare className="h-4 w-4" />
          step.log
        </div>
        <div className="space-y-2 font-mono text-xs leading-5 text-emerald-300">
          {step.logs.map((line) => (
            <div key={line}>{line}</div>
          ))}
        </div>
      </div>
    </section>
  );
}

function LiveLogWindow() {
  return (
    <section id="logs" className="scroll-mt-20 rounded-lg border border-slate-800 bg-slate-950 p-5 shadow-clinical lg:scroll-mt-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold text-emerald-300">
          <TerminalSquare className="h-5 w-5" />
          实时日志流
        </div>
        <span className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2.5 py-1 text-xs font-medium text-emerald-300">tail -f</span>
      </div>
      <div className="min-h-40 space-y-2 font-mono text-xs leading-6 text-emerald-300">
        {runtimeLogs.map((line, index) => (
          <div key={line} className="flex gap-3">
            <span className="select-none text-slate-500">{String(index + 1).padStart(2, "0")}</span>
            <span>{line}</span>
          </div>
        ))}
        <div className="flex gap-3 text-emerald-200">
          <span className="select-none text-slate-500">05</span>
          <span className="inline-flex items-center gap-2">
            <span>[INFO] Waiting for backend event stream</span>
            <span className="h-3 w-1.5 animate-pulse bg-emerald-300" />
          </span>
        </div>
      </div>
    </section>
  );
}

function ResultPreview() {
  return (
    <section id="results" className="scroll-mt-20 rounded-lg border border-slate-200 bg-white p-5 shadow-clinical lg:scroll-mt-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-indigo-600" />
          <h2 className="text-base font-semibold text-slate-950">结果预览</h2>
        </div>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">Awaiting outputs</span>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(280px,0.85fr)]">
        <div className="overflow-hidden rounded-lg border border-slate-200">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-left text-sm">
              <thead className="bg-slate-950 text-xs uppercase tracking-normal text-slate-200">
                <tr>
                  <th className="px-4 py-3 font-semibold">Gene ID</th>
                  <th className="px-4 py-3 font-semibold">Symbol</th>
                  <th className="px-4 py-3 font-semibold">Log2FC</th>
                  <th className="px-4 py-3 font-semibold">P-value</th>
                </tr>
              </thead>
              <tbody className="bg-white">
                <tr>
                  <td colSpan="4" className="px-4 py-12 text-center">
                    <div className="mx-auto flex max-w-sm flex-col items-center">
                      <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-slate-100 text-slate-500">
                        <ClipboardList className="h-5 w-5" />
                      </div>
                      <div className="mt-3 text-sm font-semibold text-slate-950">暂无后端结果数据</div>
                      <div className="mt-1 text-xs leading-5 text-slate-500">
                        差异表达表将在 workflow 输出完成后自动呈现。
                      </div>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <div className="mb-4 flex items-center justify-between">
            <div className="text-sm font-semibold text-slate-950">表达变化图</div>
            <div className="text-xs font-medium text-slate-500">No result file</div>
          </div>
          <EmptyChart />
        </div>
      </div>
    </section>
  );
}

function EmptyChart() {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <svg viewBox="0 0 100 82" role="img" aria-label="Empty result chart preview" className="h-56 w-full">
        <defs>
          <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
            <path d="M 10 0 L 0 0 0 10" fill="none" className="stroke-slate-100" strokeWidth="0.8" />
          </pattern>
        </defs>
        <rect x="8" y="8" width="86" height="64" fill="url(#grid)" />
        <line x1="50" y1="8" x2="50" y2="72" className="stroke-slate-200" strokeWidth="0.8" />
        <line x1="8" y1="72" x2="94" y2="72" className="stroke-slate-300" strokeWidth="1" />
        <line x1="8" y1="8" x2="8" y2="72" className="stroke-slate-300" strokeWidth="1" />
        <path d="M24 60 C34 45, 42 39, 50 39 C58 39, 66 45, 76 60" fill="none" className="stroke-indigo-200" strokeWidth="1.4" strokeDasharray="3 3" />
        <circle cx="50" cy="39" r="4" className="fill-slate-200" />
      </svg>
      <div className="mt-2 text-center text-xs font-medium text-slate-500">等待结果文件生成</div>
    </div>
  );
}

export default function TaskDetailPage() {
  const [activeStep, setActiveStep] = useState(pipelineSteps[1]);

  return (
    <main className="min-h-screen bg-slate-100">
      <SideNavigation />
      <div className="w-full lg:pl-64">
        <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <TaskStatusCard />

          <div className="mt-6 grid gap-6 xl:grid-cols-[380px_minmax(0,1fr)]">
            <div className="space-y-6">
              <PipelineStepper activeStep={activeStep} setActiveStep={setActiveStep} />
              <ParameterTable />
            </div>

            <div className="space-y-6">
              <StepDetail step={activeStep} />
              <LiveLogWindow />
              <ResultPreview />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
