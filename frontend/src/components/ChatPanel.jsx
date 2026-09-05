import { useState } from 'react'

export default function ChatPanel({ minWidth }) {
  const [msgs, setMsgs] = useState([
    { role:'assistant', text:'Ask BIMGuard — e.g. "Why is D-102 a problem?" or "Show me all serious violations"' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [useLlm, setUseLlm] = useState(true)
  const [liveInfo, setLiveInfo] = useState('Grounded explainer')

  const send = async () => {
    if (!input.trim()) return
    const userMsg = input
    setMsgs(m=>[...m, {role:'user', text:userMsg}])
    setInput(''); setLoading(true)
    const controller = new AbortController()
    const t = setTimeout(()=>controller.abort(), 30000)
    try {
      const r = await fetch('/api/chat', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ message: userMsg, min_width: minWidth, use_llm: useLlm }),
        signal: controller.signal
      })
      clearTimeout(t)
      if (!r.ok) throw new Error(await r.text())
      const j = await r.json()
      // Live/Mock indicator
      if (j.mode && j.mode.startsWith('llm:')) {
        setLiveInfo(`Live · ${j.model || j.mode.replace('llm:','')}`)
      } else if (j.mode && j.mode.startsWith('mock_fallback')) {
        setLiveInfo('LLM unavailable — deterministic fallback')
      } else {
        setLiveInfo('Deterministic')
      }
      setMsgs(m=>[...m, {role:'assistant', text:j.reply, meta: `${j.mode}${j.provider?` · ${j.provider}`:''}`}])
    } catch(e){
      clearTimeout(t)
      const isAbort = e.name==='AbortError'
      setLiveInfo(isAbort ? 'Timeout' : 'Error')
      setMsgs(m=>[...m, {role:'assistant', text: isAbort ? 'LLM timeout (30s) — please retry or uncheck Live LLM' : 'Error: '+e.message}])
    } finally { setLoading(false) }
  }

  return (
    <div className="bg-white rounded-xl border flex flex-col h-[300px]">
      <div className="px-4 py-2 border-b font-medium text-sm flex items-center justify-between">
        <span>Ask BIMGuard</span>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1 text-xs"><input type="checkbox" checked={useLlm} onChange={e=>setUseLlm(e.target.checked)} className="rounded"/> Live LLM</label>
          <span className={`text-xs px-2 py-0.5 rounded ${liveInfo.startsWith('Live')?'bg-green-100 text-green-700':liveInfo.includes('fallback')||liveInfo.includes('unavailable')?'bg-amber-100 text-amber-700':'bg-gray-100'}`}>{liveInfo}</span>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-3 space-y-2">
        {msgs.map((m,i)=>(
          <div key={i} className={`text-xs p-2 rounded max-w-[90%] ${m.role==='user'?'bg-black text-white ml-auto':'bg-gray-100'}`}>
            <div className="whitespace-pre-wrap">{m.text}</div>
            {m.meta && <div className="text-[10px] opacity-50 mt-1">{m.meta}</div>}
          </div>
        ))}
        {loading && <div className="text-xs text-gray-400">Thinking (calling tools)…</div>}
      </div>
      <div className="p-2 border-t flex gap-2">
        <input value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>e.key==='Enter'&&send()} placeholder='Why is D-102 non-compliant?' className="flex-1 border rounded px-3 py-1.5 text-sm" />
        <button onClick={send} className="bg-black text-white px-4 py-1.5 rounded text-sm">Send</button>
      </div>
    </div>
  )
}
