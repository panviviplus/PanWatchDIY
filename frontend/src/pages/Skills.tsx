import { useEffect, useState } from 'react'
import { Zap, Play, RefreshCw, Wrench, Tag, FileText } from 'lucide-react'
import { fetchAPI } from '@panwatch/api'

interface SkillManifest {
  name: string
  display_name: string
  description: string
  version: string
  author: string
  tags: string[]
  enabled: boolean
  dir_path: string
  has_runner: boolean
  has_prompt: boolean
}

interface SkillRunResult {
  skill_name: string
  success: boolean
  output: string
  error: string
  duration_ms: number
  metadata?: Record<string, any>
}

export default function SkillsPage() {
  const [skills, setSkills] = useState<SkillManifest[]>([])
  const [loading, setLoading] = useState(true)
  const [runningSkill, setRunningSkill] = useState<string | null>(null)
  const [result, setResult] = useState<SkillRunResult | null>(null)

  const loadSkills = async () => {
    setLoading(true)
    try {
      const data = await fetchAPI<SkillManifest[]>('/local-skills')
      setSkills(data)
    } catch {
      // Skills dir might not exist yet
      setSkills([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadSkills() }, [])

  // Init skills directory on first load
  const initSkills = async () => {
    try {
      await fetchAPI('/local-skills/init', { method: 'POST' })
      await loadSkills()
    } catch { /* ignore */ }
  }

  const runSkill = async (name: string) => {
    setRunningSkill(name)
    setResult(null)
    try {
      const res = await fetchAPI<SkillRunResult>(`/local-skills/${name}/run`, {
        method: 'POST',
        body: JSON.stringify({ params: {} }),
        timeoutMs: 30000,
      })
      setResult(res)
    } catch (e: any) {
      setResult({
        skill_name: name,
        success: false,
        output: '',
        error: e?.message || '未知错误',
        duration_ms: 0,
      })
    } finally {
      setRunningSkill(null)
    }
  }

  return (
    <div className="flex flex-col h-full p-4 sm:p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <Wrench className="w-5 h-5" />
            本地 Skill 广场
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Hermes 本地技能扫描与执行
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadSkills}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg bg-accent/50 hover:bg-accent transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" /> 刷新
          </button>
          <button
            onClick={initSkills}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg bg-primary/10 hover:bg-primary/20 text-primary transition-colors"
          >
            <Zap className="w-3.5 h-3.5" /> 初始化
          </button>
        </div>
      </div>

      {/* Skills Grid */}
      {loading ? (
        <div className="text-sm text-muted-foreground">加载中...</div>
      ) : skills.length === 0 ? (
        <div className="flex flex-col items-center justify-center flex-1 text-muted-foreground gap-3">
          <Wrench className="w-12 h-12 opacity-20" />
          <p className="text-sm">暂无 Skill</p>
          <p className="text-xs">
            在 skills/ 目录下创建 Skill 文件夹与 manifest.yaml 即可自动发现
          </p>
          <button
            onClick={initSkills}
            className="inline-flex items-center gap-1 px-4 py-2 text-sm rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
          >
            <Zap className="w-4 h-4" /> 初始化 Skills 目录
          </button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {skills.map((skill) => (
            <div
              key={skill.name}
              className="rounded-xl border border-border/60 bg-card p-4 space-y-3 hover:shadow-sm transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-sm">{skill.display_name}</h3>
                  <p className="text-xs text-muted-foreground font-mono">{skill.name}</p>
                </div>
                {skill.has_runner && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300">
                    可执行
                  </span>
                )}
              </div>

              <p className="text-xs text-muted-foreground line-clamp-2">
                {skill.description || '无描述'}
              </p>

              <div className="flex items-center gap-1 flex-wrap">
                {skill.tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-[10px] px-1.5 py-0.5 rounded-full bg-accent/50 text-muted-foreground inline-flex items-center gap-0.5"
                  >
                    <Tag className="w-2.5 h-2.5" /> {tag}
                  </span>
                ))}
              </div>

              <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                <span>v{skill.version}</span>
                <span className="flex items-center gap-1">
                  {skill.has_runner && <Play className="w-3 h-3" />}
                  {skill.has_prompt && <FileText className="w-3 h-3" />}
                </span>
              </div>

              <button
                onClick={() => runSkill(skill.name)}
                disabled={runningSkill === skill.name || !skill.has_runner}
                className="w-full inline-flex items-center justify-center gap-1 px-3 py-1.5 text-xs rounded-lg bg-primary/10 hover:bg-primary/20 text-primary transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {runningSkill === skill.name ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Play className="w-3.5 h-3.5" />
                )}
                {runningSkill === skill.name ? '执行中...' : '运行'}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Result Panel */}
      {result && (
        <div className={`rounded-lg border p-4 ${result.success ? 'border-emerald-500/30 bg-emerald-50 dark:bg-emerald-950' : 'border-rose-500/30 bg-rose-50 dark:bg-rose-950'}`}>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold">
              {result.success ? '✅ 执行成功' : '❌ 执行失败'} — {result.skill_name}
            </h3>
            <span className="text-xs text-muted-foreground">
              {result.duration_ms.toFixed(0)}ms
            </span>
          </div>
          {result.success && result.output && (
            <pre className="text-xs whitespace-pre-wrap break-words max-h-48 overflow-y-auto bg-black/5 dark:bg-white/5 rounded p-3">
              {result.output}
            </pre>
          )}
          {!result.success && result.error && (
            <p className="text-xs text-rose-600 dark:text-rose-400">{result.error}</p>
          )}
        </div>
      )}
    </div>
  )
}
