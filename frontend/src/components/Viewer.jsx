import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'

function Box({ pos, color, selected }) {
  return (
    <mesh position={pos}>
      <boxGeometry args={[1, 0.6, 1]} />
      <meshStandardMaterial color={selected ? '#ef4444' : color} emissive={selected ? '#ffaaaa' : '#000000'} />
    </mesh>
  )
}

// Schematic element locator: placement-aware boxes, not rendered IFC shape geometry.
export default function Viewer({ elements, selectedGuid, failedDoorGuids = new Set() }) {
  const items = elements.slice(0, 40).map((el, i) => {
    const p = el.placement || { x: (i % 6) * 2, y: Math.floor(i / 6) * 2, z: 0 }
    let color = '#d1d5db'
    if (el.type === 'IfcWall') color = '#94a3b8'
    if (el.type === 'IfcDoor') color = failedDoorGuids.has(el.guid) ? '#f97316' : '#22c55e'
    if (el.type === 'IfcBeam') color = '#a78bfa'
    if (el.type === 'IfcPipeSegment' || el.type === 'IfcFlowSegment') color = '#38bdf8'
    const isSelected = selectedGuid && el.guid === selectedGuid
    const pos = [p.x, p.z + 0.5, -p.y]
    return { el, pos, color, isSelected }
  })

  if (!elements.length) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-50 text-sm text-gray-500">
        No model loaded — upload .ifc to visualize element placements
      </div>
    )
  }

  return (
    <Canvas camera={{ position: [8, 10, 8], fov: 45 }}>
      <ambientLight intensity={0.7} />
      <directionalLight position={[10, 10, 5]} intensity={0.8} />
      <gridHelper args={[20, 20, '#e5e7eb', '#f3f4f6']} />
      {items.map(({ el, pos, color, isSelected }) => (
        <Box key={el.guid || el.name} pos={pos} color={color} selected={isSelected} />
      ))}
      <OrbitControls />
    </Canvas>
  )
}
