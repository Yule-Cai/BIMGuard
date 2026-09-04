import { useState } from 'react'

export default function IssuesPanel({ summary, onLocate, onExplain }) {
  const [explaining, setExplaining] = useState(null)
  const [explainText, setExplainText] = useState(null)

  const doorsFail = summary.doors.results.filter(d=>d.status==='fail')
  const clashes = summary.clashes.results

  const handleExplain = async (item) => {
    setExplaining(item.guid || item.a_guid)
    // call chat API for explanation
    try {
      const msg = item.a_guid ? `Explain clash ${item.a_guid} x ${item.b_guid} penetration ${item.penetration_mm}mm` : `Why is door ${item.name} (${item.guid}) a problem? width ${item.measured_mm} required ${item.required_mm}`
      const r = await fetch('/api/chat', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ message: msg, min_width: summary.min_width }) })
      const j = await r.json()
      setExplainText(j.reply)
    } catch (e) {
      setExplainText(String(e))
    } finally {
      setExplaining(null)
    }
  }

  return (
    <div className="bg-white rounded-xl border flex flex-col">
      <div className="px-4 py-2 border-b font-medium text-sm">Critical Issues</div>
      <div className="divide-y max-h-[320px] overflow-auto">
        {doorsFail.length===0 && clashes.length===0 && (
          <div className="p-4 text-sm text-green-600">✓ No violations for current threshold.</div>
        )}
        {doorsFail.map(d=>(
          <div key={d.guid} className="p-3 flex items-start justify-between hover:bg-gray-50">
            <div>
              <div className="text-sm font-medium flex items-center gap-2">
                <span className="bg-red-100 text-red-700 text-xs px-1.5 py-0.5 rounded">FAIL</span>
                {d.name} <span className="text-xs text-gray-500">{d.guid.slice(0,8)}</span>
              </div>
              <div className="text-xs text-gray-600 mt-1">Exit door too narrow</div>
              <div className="text-xs text-red-600">{d.measured_mm} mm &lt; {d.required_mm} mm (Δ {d.delta_mm} mm)</div>
              <div className="text-[11px] text-gray-400">{d.rule}</div>
            </div>
            <div className="flex flex-col gap-1">
              <button onClick={()=>onLocate(d.guid)} className="text-xs border px-2 py-1 rounded hover:bg-black hover:text-white">Locate</button>
              <button onClick={()=>handleExplain(d)} className="text-xs border px-2 py-1 rounded hover:bg-black hover:text-white">{explaining===d.guid?'...':'Explain'}</button>
            </div>
          </div>
        ))}
        {clashes.map((c,i)=>(
          <div key={c.a_guid+c.b_guid} className="p-3 flex items-start justify-between hover:bg-gray-50">
            <div>
              <div className="text-sm font-medium flex items-center gap-2">
                <span className={`text-xs px-1.5 py-0.5 rounded ${c.severity==='high'?'bg-red-100 text-red-700':c.severity==='medium'?'bg-amber-100 text-amber-700':'bg-gray-100'}`}>{c.severity}</span>
                {c.a_name} × {c.b_name}
              </div>
              <div className="text-xs text-gray-600">{c.a_type} × {c.b_type}</div>
              <div className="text-xs text-red-600">{c.penetration_mm} mm penetration</div>
            </div>
            <div className="flex flex-col gap-1">
              <button onClick={()=>onLocate(c.a_guid)} className="text-xs border px-2 py-1 rounded hover:bg-black hover:text-white">Locate</button>
              <button onClick={()=>handleExplain(c)} className="text-xs border px-2 py-1 rounded hover:bg-black hover:text-white">{explaining===c.a_guid?'...':'Explain'}</button>
            </div>
          </div>
        ))}
      </div>
      {explainText && (
        <div className="m-3 p-3 bg-gray-50 border rounded text-xs whitespace-pre-wrap">{explainText}</div>
      )}
    </div>
  )
}
