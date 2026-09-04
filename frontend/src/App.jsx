import { useState, useEffect } from 'react'
import Viewer from './components/Viewer.jsx'
import IssuesPanel from './components/IssuesPanel.jsx'
import ChatPanel from './components/ChatPanel.jsx'

export default function App() {
  const [summary, setSummary] = useState(null)
  const [elements, setElements] = useState([])
  const [selectedGuid, setSelectedGuid] = useState(null)
  const [fileName, setFileName] = useState(null)
  const [minWidth, setMinWidth] = useState(750)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchSummary = async (mw = minWidth) => {
    try {
      const r = await fetch(`/api/summary?min_width=${mw}`)
      if (!r.ok) throw new Error(await r.text())
      const j = await r.json()
      setSummary(j)
      const er = await fetch('/api/elements?limit=100')
      if (er.ok) {
        const ej = await er.json()
        setElements(ej.elements || [])
      }
    } catch (e) {
      setError(e.message)
    }
  }

  const handleUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setLoading(true); setError(null)
    const fd = new FormData()
    fd.append('file', file)
    try {
      const r = await fetch('/api/upload', { method: 'POST', body: fd })
      if (!r.ok) throw new Error(await r.text())
      const j = await r.json()
      setFileName(j.filename)
      await fetchSummary()
    } catch (err) {
      setError(err.message)
    } finally { setLoading(false) }
  }

  const handleExplain = async (issue) => {
    return `Explain ${issue.name || issue.guid} : ${JSON.stringify(issue).slice(0,300)}`
  }

  useEffect(() => {
    fetchSummary().catch(()=>{})
  }, [])

  const failedDoorGuids = new Set(
    (summary?.doors?.results || []).filter(d => d.status === 'fail').map(d => d.guid)
  )
  const firstClashMethod = summary?.clashes?.results?.[0]?.method
  const clashMethodLabel = firstClashMethod === 'synthetic_aabb_fallback'
    ? 'Labelled synthetic demo fallback'
    : 'IfcOpenShell BVH for real geometry'

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-10 bg-white border-b px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-black text-white flex items-center justify-center font-bold rounded">BG</div>
          <div>
            <div className="font-bold leading-none">BIMGuard</div>
            <div className="text-xs text-gray-500">AI-Native IFC Compliance Agent · HKU AI+BIM</div>
          </div>
          <span className="ml-4 text-xs bg-gray-100 px-2 py-1 rounded">IFC4 · HK FS 2011 Table B2 · IfcOpenShell</span>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-600">Min width</label>
          <select value={minWidth} onChange={e=>{setMinWidth(Number(e.target.value)); fetchSummary(Number(e.target.value))}} className="border rounded px-2 py-1 text-sm">
            <option value={750}>750 mm (4–30 p)</option>
            <option value={850}>850 mm (31–200 p)</option>
          </select>
          <label className="bg-black text-white px-4 py-1.5 rounded text-sm cursor-pointer hover:bg-gray-800">
            {loading ? 'Uploading...' : 'Upload .ifc'}
            <input type="file" accept=".ifc" className="hidden" onChange={handleUpload} />
          </label>
        </div>
      </header>

      {error && <div className="mx-6 mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded text-sm">{error}</div>}
      {fileName && <div className="mx-6 mt-3 text-xs text-gray-500">Loaded: {fileName} · {elements.length} elements</div>}

      <div className="flex-1 grid grid-cols-12 gap-4 p-4">
        <div className="col-span-7 bg-white rounded-xl border overflow-hidden flex flex-col">
          <div className="px-4 py-2 border-b flex items-center justify-between">
            <span className="font-medium text-sm">3D Element Locator</span>
            <span className="text-xs text-gray-500">{selectedGuid ? `Selected: ${selectedGuid.slice(0,8)}` : 'Schematic placement view · click issue → Locate'}</span>
          </div>
          <div className="flex-1 min-h-[520px]">
            <Viewer elements={elements} selectedGuid={selectedGuid} failedDoorGuids={failedDoorGuids} />
          </div>
        </div>

        <div className="col-span-5 flex flex-col gap-4">
          {summary ? (
            <>
              <div className="bg-white rounded-xl border p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-gray-500">Compliance Score</div>
                    <div className="text-3xl font-bold">{summary.score===null||summary.score===undefined?'N/A':summary.score} <span className="text-sm font-normal text-gray-500">{summary.score===null?'': '/100'}</span></div>
                    {summary.score===null && <div className="text-xs text-gray-400">No applicable elements</div>}
                  </div>
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center text-white font-bold ${summary.score===null?'bg-gray-400':summary.score>=80?'bg-green-600':summary.score>=50?'bg-amber-500':'bg-red-600'}`}>{summary.score===null?'—':summary.score}</div>
                </div>
                <div className="grid grid-cols-2 gap-3 mt-4">
                  <div className="border rounded-lg p-3">
                    <div className="text-xs text-gray-500">Exit Door Width</div>
                    <div className="text-sm font-medium">{summary.doors.passed} passed · {summary.doors.failed} failed</div>
                    <div className="text-xs text-gray-400">{summary.doors.total} checked · ≥{summary.min_width}mm</div>
                  </div>
                  <div className="border rounded-lg p-3">
                    <div className="text-xs text-gray-500">Geometry Clash</div>
                    <div className="text-sm font-medium">{summary.clashes.count} clashes</div>
                    <div className="text-xs text-gray-400">{clashMethodLabel}</div>
                  </div>
                </div>
              </div>

              <IssuesPanel summary={summary} onLocate={setSelectedGuid} onExplain={handleExplain} />
            </>
          ) : (
            <div className="bg-white rounded-xl border p-8 text-center text-sm text-gray-500">
              Upload an .ifc to see compliance results.<br/>
              <span className="text-xs">Try sample-ifc/BIMGuard_Demo.ifc (D-102 fail + 1 labelled synthetic clash)</span>
            </div>
          )}

          <ChatPanel minWidth={minWidth} />
        </div>
      </div>

      <footer className="text-center text-xs text-gray-400 py-3 border-t bg-white">
        Deterministic engine: IfcOpenShell · LLM: grounded explanation · HKU DUPAD Ref.536608
      </footer>
    </div>
  )
}
