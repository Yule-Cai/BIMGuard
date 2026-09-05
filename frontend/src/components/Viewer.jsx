import { Canvas } from '@react-three/fiber'
import { OrbitControls, Environment, ContactShadows } from '@react-three/drei'

function Box({ pos, color, selected, type }) {
  const scale = type === 'IfcDoor' ? [0.9, 2.1, 0.05] : type === 'IfcBeam' ? [5, 0.3, 0.4] : type === 'IfcPipeSegment' ? [4, 0.15, 0.15] : [1, 0.6, 1]
  const args = type === 'IfcWall' ? [5, 3, 0.2] : scale
  return (
    <mesh position={pos} castShadow receiveShadow>
      <boxGeometry args={args} />
      <meshStandardMaterial
        color={selected ? '#ef4444' : color}
        emissive={selected ? '#ffaaaa' : '#000000'}
        emissiveIntensity={selected ? 0.3 : 0}
        roughness={0.7}
        metalness={0.1}
      />
    </mesh>
  )
}

// Schematic element locator — now with PBR, shadows, and honest labeling.
// For true IFC shape rendering, swap this for web-ifc-three (ThatOpen) in production.
export default function Viewer({ elements, selectedGuid, failedDoorGuids = new Set() }) {
  const items = elements.slice(0, 48).map((el, i) => {
    const p = el.placement || { x: (i % 6) * 2.5, y: Math.floor(i/6)*2.5, z: 0 }
    let color = '#d1d5db'
    if (el.type === 'IfcWall') color = '#94a3b8'
    if (el.type === 'IfcDoor') color = failedDoorGuids.has(el.guid) ? '#f97316' : '#22c55e'
    if (el.type === 'IfcBeam') color = '#a78bfa'
    if (el.type === 'IfcPipeSegment' || el.type === 'IfcFlowSegment') color = '#38bdf8'
    if (el.type === 'IfcSlab') color = '#fbbf24'
    const isSelected = selectedGuid && el.guid === selectedGuid
    // Use placement with slight randomization for visual clarity when no placement
    const pos = [p.x, p.z + 0.5, -p.y]
    return { el, pos, color, isSelected }
  })

  if (!elements.length) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-50 text-sm text-gray-500 p-6 text-center">
        <div>
          <div className="font-medium">No model loaded</div>
          <div className="text-xs mt-1">Upload .ifc to visualize — schematic locator shows placements; true IFC geometry via web-ifc in production</div>
        </div>
      </div>
    )
  }

  return (
    <Canvas camera={{ position: [12, 10, 12], fov: 45 }} shadows>
      <ambientLight intensity={0.6} />
      <directionalLight position={[10, 14, 8]} intensity={1.0} castShadow shadow-mapSize={[2048,2048]} />
      <pointLight position={[-8, 8, -8]} intensity={0.4} />
      <gridHelper args={[24, 24, '#e5e7eb', '#f3f4f6']} />
      <mesh rotation={[-Math.PI/2,0,0]} position={[0,-0.01,0]} receiveShadow>
        <planeGeometry args={[40,40]} />
        <meshStandardMaterial color="#f9fafb" roughness={0.9} />
      </mesh>
      {items.map(({ el, pos, color, isSelected }) => (
        <Box key={el.guid || el.name} pos={pos} color={color} selected={isSelected} type={el.type} />
      ))}
      <ContactShadows position={[0,-0.5,0]} opacity={0.35} scale={24} blur={2} />
      <Environment preset="city" />
      <OrbitControls enableDamping dampingFactor={0.08} />
    </Canvas>
  )
}
