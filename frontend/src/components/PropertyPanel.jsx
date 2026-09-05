import { useEffect, useState } from 'react'

export default function PropertyPanel({ guid, onClose }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!guid) { setData(null); return }
    setLoading(true)
    fetch(`/api/element/${guid}`)
      .then(r => r.ok ? r.json() : Promise.reject(r.statusText))
      .then(j => setData(j))
      .catch(() => setData({ error: 'Failed to load' }))
      .finally(() => setLoading(false))
  }, [guid])

  if (!guid) {
    return (
      <div className="bg-white rounded-xl border p-4 text-sm text-gray-500">
        <div className="font-medium">Properties</div>
        <div className="text-xs mt-1">Select an element via <span className="bg-gray-100 px-1 rounded">[Locate]</span> to see Pset / Qto</div>
      </div>
    )
  }

  if (loading) return <div className="bg-white rounded-xl border p-4 text-xs text-gray-500">Loading {guid.slice(0,8)}…</div>
  if (!data) return null

  const psets = data.psets || {}
  const info = data.info || {}
  // Flatten psets for table
  const rows = []
  Object.entries(psets).forEach(([psetName, props]) => {
    if (typeof props === 'object' && props !== null) {
      Object.entries(props).forEach(([k, v]) => {
        rows.push({ pset: psetName, key: k, value: String(v) })
      })
    }
  })

  return (
    <div className="bg-white rounded-xl border flex flex-col max-h-[320px]">
      <div className="px-4 py-2 border-b flex items-center justify-between">
        <span className="font-medium text-sm">Properties — {info.name || guid.slice(0,8)}</span>
        <button onClick={onClose} className="text-xs text-gray-500 hover:text-black">✕</button>
      </div>
      <div className="px-4 py-2 border-b bg-gray-50 text-xs">
        <div><span className="text-gray-500">GUID:</span> {guid}</div>
        <div><span className="text-gray-500">Type:</span> {info.type || '—'} {info.width ? `· Width ${info.width} m` : ''}</div>
        {info.placement && <div className="text-gray-500">Placement: ({info.placement.x.toFixed(2)}, {info.placement.y.toFixed(2)}, {info.placement.z.toFixed(2)})</div>}
      </div>
      <div className="flex-1 overflow-auto">
        {rows.length ? (
          <table className="w-full text-xs">
            <thead className="bg-gray-50 sticky top-0"><tr><th className="text-left p-2 font-medium">Pset</th><th className="text-left p-2 font-medium">Property</th><th className="text-left p-2 font-medium">Value</th></tr></thead>
            <tbody className="divide-y">
              {rows.map((r, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="p-2 text-gray-600">{r.pset}</td>
                  <td className="p-2 font-medium">{r.key}</td>
                  <td className="p-2">{r.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="p-4 text-xs text-gray-500">No Pset/Qto found for this element (common for synthetic demo walls). Real IFCs show Pset_DoorCommon, Qto_DoorBaseQuantities etc.</div>
        )}
      </div>
    </div>
  )
}
